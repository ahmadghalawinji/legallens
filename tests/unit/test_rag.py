from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.schemas.clauses import ClassifiedClause, ClauseType, RiskLevel
from backend.core.agents.precedent_retriever import Precedent

# ── helpers ───────────────────────────────────────────────────────────────────


def make_classified(
    clause_id: str = "clause_1",
    risk_level: RiskLevel = RiskLevel.HIGH,
) -> ClassifiedClause:
    return ClassifiedClause(
        id=clause_id,
        clause_type=ClauseType.LIABILITY,
        text="In no event shall either party be liable for consequential damages.",
        confidence=0.95,
        risk_level=risk_level,
        risk_score=0.8,
        risk_explanation="Broad liability waiver.",
        reasoning="Chain of thought reasoning.",
    )


def make_precedent(clause_id: str = "p1") -> Precedent:
    return Precedent(
        id=clause_id,
        text="Standard liability clause limiting exposure to direct damages only.",
        clause_type="liability",
        source="ledgar",
        relevance_score=0.72,
    )


# ── embeddings ────────────────────────────────────────────────────────────────


def test_embed_text_returns_list():
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])

    with patch("backend.knowledge.embeddings._get_model", return_value=mock_model):
        from backend.knowledge.embeddings import embed_text

        result = embed_text("test clause")

    assert isinstance(result, list)


def test_embed_batch_empty():
    from backend.knowledge.embeddings import embed_batch

    assert embed_batch([]) == []


# ── hybrid retriever / RRF ────────────────────────────────────────────────────


def test_rrf_merges_results():
    from backend.knowledge.retriever import _reciprocal_rank_fusion

    dense = [
        {"id": "a", "text": "doc a", "metadata": {}},
        {"id": "b", "text": "doc b", "metadata": {}},
    ]
    sparse = [
        {"id": "b", "text": "doc b", "metadata": {}, "bm25_score": 1.5},
        {"id": "c", "text": "doc c", "metadata": {}, "bm25_score": 0.8},
    ]
    merged = _reciprocal_rank_fusion(dense, sparse)

    ids = [h["id"] for h in merged]
    # "b" appears in both lists so should rank highest
    assert ids[0] == "b"
    assert set(ids) == {"a", "b", "c"}


def test_rrf_single_list():
    from backend.knowledge.retriever import _reciprocal_rank_fusion

    dense = [{"id": "x", "text": "only", "metadata": {}}]
    merged = _reciprocal_rank_fusion(dense, [])
    assert len(merged) == 1
    assert merged[0]["id"] == "x"


# ── PrecedentRetriever ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_precedent_retriever_skips_low_risk():
    from backend.core.agents.precedent_retriever import PrecedentRetriever

    low_clause = make_classified(risk_level=RiskLevel.LOW)
    retriever = PrecedentRetriever()

    with patch("backend.core.agents.precedent_retriever.hybrid_search", return_value=[]):
        results = await retriever.run([low_clause])

    assert results["clause_1"] == []


@pytest.mark.asyncio
async def test_precedent_retriever_fetches_for_high_risk():
    from backend.core.agents.precedent_retriever import PrecedentRetriever

    high_clause = make_classified(risk_level=RiskLevel.HIGH)
    mock_hit = {
        "id": "p1",
        "text": "Standard precedent text.",
        "metadata": {"clause_type": "liability", "source": "ledgar"},
        "rrf_score": 0.8,
    }

    with patch(
        "backend.core.agents.precedent_retriever.hybrid_search", return_value=[mock_hit]
    ):
        retriever = PrecedentRetriever()
        results = await retriever.run([high_clause])

    assert len(results["clause_1"]) == 1
    assert results["clause_1"][0].source == "ledgar"


@pytest.mark.asyncio
async def test_precedent_retriever_handles_error_gracefully():
    from backend.core.agents.precedent_retriever import PrecedentRetriever

    clause = make_classified(risk_level=RiskLevel.MEDIUM)

    with patch(
        "backend.core.agents.precedent_retriever.hybrid_search",
        side_effect=RuntimeError("ChromaDB down"),
    ) as _:
        retriever = PrecedentRetriever()
        results = await retriever.run([clause])

    assert results["clause_1"] == []


# ── RecommendationGenerator ───────────────────────────────────────────────────


RECOMMENDATION_JSON = """{
  "plain_explanation": "This clause waives your right to recover lost profits.",
  "key_concerns": ["No cap on waiver", "One-sided"],
  "suggested_alternative": "Liability limited to direct damages up to contract value.",
  "disclaimer": "This is not legal advice. Consult a qualified attorney before signing."
}"""


@pytest.mark.asyncio
async def test_recommendation_generator_basic():
    from backend.core.agents.recommendation_generator import RecommendationGenerator

    llm = MagicMock()
    msg = MagicMock()
    msg.content = RECOMMENDATION_JSON
    llm.ainvoke = AsyncMock(return_value=msg)

    gen = RecommendationGenerator(llm)
    results = await gen.run([make_classified()], {"clause_1": [make_precedent()]})

    assert len(results) == 1
    assert "waives" in results[0].plain_explanation
    assert len(results[0].key_concerns) >= 1
    assert results[0].suggested_alternative
    assert "not legal advice" in results[0].disclaimer


@pytest.mark.asyncio
async def test_recommendation_generator_fallback_on_failure():
    from backend.core.agents.recommendation_generator import RecommendationGenerator

    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))

    gen = RecommendationGenerator(llm)
    results = await gen.run([make_classified()], {"clause_1": []})

    assert len(results) == 1
    assert results[0].clause_id == "clause_1"
    assert "not legal advice" in results[0].disclaimer


@pytest.mark.asyncio
async def test_recommendation_generator_no_precedents():
    from backend.core.agents.recommendation_generator import RecommendationGenerator

    llm = MagicMock()
    msg = MagicMock()
    msg.content = RECOMMENDATION_JSON
    llm.ainvoke = AsyncMock(return_value=msg)

    gen = RecommendationGenerator(llm)
    # Empty precedents dict — should still work
    results = await gen.run([make_classified()], {})

    assert len(results) == 1
