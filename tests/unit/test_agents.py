# ruff: noqa: E501
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.api.schemas.clauses import ClauseType, ExtractedClause, RiskLevel
from backend.core.parsers.base import ParsedDocument

# ── fixtures ──────────────────────────────────────────────────────────────────


def make_llm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    return msg


def make_parsed_doc(text: str = "Sample contract text.") -> ParsedDocument:
    return ParsedDocument(
        filename="test.pdf",
        file_type="pdf",
        full_text=text,
        sections=[],
        page_count=1,
    )


def make_clause(clause_type: ClauseType = ClauseType.LIABILITY) -> ExtractedClause:
    return ExtractedClause(
        id="clause_1",
        clause_type=clause_type,
        text="In no event shall either party be liable for consequential damages.",
        confidence=0.95,
    )


EXTRACTION_JSON = """{
  "clauses": [
    {
      "id": "clause_1",
      "clause_type": "liability",
      "text": "In no event shall either party be liable for consequential damages.",
      "confidence": 0.95,
      "page_number": null
    }
  ]
}"""

CLASSIFICATION_JSON = """{
  "risk_level": "high",
  "risk_score": 0.85,
  "risk_explanation": "Unlimited liability waiver.",
  "reasoning": "ONE-SIDEDNESS: Favors the company. MARKET DEVIATION: Unusual. FINANCIAL EXPOSURE: High. ENFORCEABILITY: Enforceable."
}"""


# ── ClauseExtractor ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extractor_basic():
    from backend.core.agents.clause_extractor import ClauseExtractor

    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=make_llm_response(EXTRACTION_JSON))

    extractor = ClauseExtractor(llm)
    clauses = await extractor.run(make_parsed_doc())

    assert len(clauses) == 1
    assert clauses[0].clause_type == ClauseType.LIABILITY
    assert "consequential damages" in clauses[0].text
    assert 0 <= clauses[0].confidence <= 1


@pytest.mark.asyncio
async def test_extractor_empty_document():
    from backend.core.agents.clause_extractor import ClauseExtractor

    llm = MagicMock()
    extractor = ClauseExtractor(llm)
    clauses = await extractor.run(make_parsed_doc(""))

    assert clauses == []
    llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_extractor_assigns_stable_ids():
    from backend.core.agents.clause_extractor import ClauseExtractor

    multi_json = """{
      "clauses": [
        {"id": "x", "clause_type": "liability", "text": "Liability clause.", "confidence": 0.9, "page_number": null},
        {"id": "y", "clause_type": "termination", "text": "Termination clause.", "confidence": 0.8, "page_number": null}
      ]
    }"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=make_llm_response(multi_json))

    extractor = ClauseExtractor(llm)
    clauses = await extractor.run(make_parsed_doc("some text"))

    assert clauses[0].id == "clause_1"
    assert clauses[1].id == "clause_2"


@pytest.mark.asyncio
async def test_extractor_deduplication():
    from backend.core.agents.clause_extractor import ClauseExtractor

    dup_json = """{
      "clauses": [
        {"id": "a", "clause_type": "liability", "text": "Liability clause exact same text here.", "confidence": 0.9, "page_number": null},
        {"id": "b", "clause_type": "liability", "text": "Liability clause exact same text here.", "confidence": 0.8, "page_number": null}
      ]
    }"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=make_llm_response(dup_json))

    extractor = ClauseExtractor(llm)
    clauses = await extractor.run(make_parsed_doc("some text"))

    assert len(clauses) == 1


@pytest.mark.asyncio
async def test_extractor_retries_on_invalid_json():
    from backend.core.agents.clause_extractor import ClauseExtractor

    llm = MagicMock()
    llm.ainvoke = AsyncMock(
        side_effect=[
            make_llm_response("not json at all"),
            make_llm_response(EXTRACTION_JSON),
        ]
    )

    extractor = ClauseExtractor(llm)
    clauses = await extractor.run(make_parsed_doc("some text"))

    assert isinstance(clauses, list)


@pytest.mark.asyncio
async def test_extractor_returns_empty_on_total_failure():
    from backend.core.agents.clause_extractor import ClauseExtractor

    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))

    extractor = ClauseExtractor(llm)
    clauses = await extractor.run(make_parsed_doc("some text"))

    assert clauses == []


# ── RiskClassifier ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_classifier_basic():
    from backend.core.agents.risk_classifier import RiskClassifier

    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=make_llm_response(CLASSIFICATION_JSON))

    classifier = RiskClassifier(llm)
    results = await classifier.run([make_clause()])

    assert len(results) == 1
    assert results[0].risk_level == RiskLevel.HIGH
    assert 0 <= results[0].risk_score <= 1
    assert results[0].risk_explanation
    assert results[0].reasoning


@pytest.mark.asyncio
async def test_classifier_empty_input():
    from backend.core.agents.risk_classifier import RiskClassifier

    llm = MagicMock()
    classifier = RiskClassifier(llm)
    results = await classifier.run([])

    assert results == []


@pytest.mark.asyncio
async def test_classifier_fallback_on_failure():
    from backend.core.agents.risk_classifier import RiskClassifier

    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM error"))

    classifier = RiskClassifier(llm)
    results = await classifier.run([make_clause()])

    assert len(results) == 1
    assert results[0].risk_level == RiskLevel.MEDIUM
    assert "manual review" in results[0].risk_explanation


@pytest.mark.asyncio
async def test_classifier_parallel_execution():
    from backend.core.agents.risk_classifier import RiskClassifier

    clauses = [
        make_clause(ct)
        for ct in [ClauseType.LIABILITY, ClauseType.TERMINATION, ClauseType.NON_COMPETE]
    ]
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=make_llm_response(CLASSIFICATION_JSON))

    classifier = RiskClassifier(llm)
    results = await classifier.run(clauses)

    assert len(results) == 3
    assert llm.ainvoke.call_count == 3


@pytest.mark.asyncio
async def test_classifier_risk_score_clamped():
    from backend.core.agents.risk_classifier import RiskClassifier

    bad_json = """{
      "risk_level": "high",
      "risk_score": 1.5,
      "risk_explanation": "Very risky.",
      "reasoning": "Out of bounds score test."
    }"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=make_llm_response(bad_json))

    classifier = RiskClassifier(llm)
    results = await classifier.run([make_clause()])

    assert results[0].risk_score <= 1.0


# ── Schema validation ─────────────────────────────────────────────────────────


def test_extracted_clause_schema():
    clause = ExtractedClause(
        id="c1",
        clause_type=ClauseType.CONFIDENTIALITY,
        text="All information shared is confidential.",
        confidence=0.9,
    )
    assert clause.id == "c1"
    assert clause.page_number is None


def test_classified_clause_inherits_extracted():
    from backend.api.schemas.clauses import ClassifiedClause

    clause = ClassifiedClause(
        id="c1",
        clause_type=ClauseType.NON_COMPETE,
        text="No competing for 2 years.",
        confidence=0.9,
        risk_level=RiskLevel.HIGH,
        risk_score=0.8,
        risk_explanation="Broad restriction.",
        reasoning="Step-by-step reasoning.",
    )
    assert clause.clause_type == ClauseType.NON_COMPETE
    assert clause.risk_level == RiskLevel.HIGH
