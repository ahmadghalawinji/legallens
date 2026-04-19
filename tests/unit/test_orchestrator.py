from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.schemas.clauses import ClassifiedClause, ClauseType, RiskLevel
from backend.core.parsers.base import DocumentSection, ParsedDocument


def make_parsed_doc() -> ParsedDocument:
    return ParsedDocument(
        filename="test.pdf",
        file_type="pdf",
        full_text="Party shall indemnify Company for all losses.",
        sections=[DocumentSection(text="Indemnification clause text.", page_number=1)],
        page_count=1,
    )


def make_classified_clause() -> ClassifiedClause:
    return ClassifiedClause(
        id="clause_1",
        clause_type=ClauseType.INDEMNIFICATION,
        text="Party shall indemnify Company for all losses.",
        confidence=0.92,
        risk_level=RiskLevel.HIGH,
        risk_score=0.85,
        risk_explanation="Broad indemnification.",
        reasoning="One-sided.",
    )


@pytest.mark.asyncio
async def test_full_pipeline_runs():
    from backend.core.orchestrator import run_analysis_graph

    mock_doc = make_parsed_doc()
    mock_clause = make_classified_clause()

    with (
        patch("backend.core.orchestrator.get_parser") as mock_get_parser,
        patch("backend.core.orchestrator.get_llm") as mock_get_llm,
        patch("backend.core.orchestrator.PrecedentRetriever") as mock_retriever_cls,
    ):
        mock_parser = MagicMock()
        mock_parser.parse = AsyncMock(return_value=mock_doc)
        mock_get_parser.return_value = mock_parser

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="{}"))
        mock_get_llm.return_value = mock_llm

        mock_extractor = MagicMock()
        mock_extractor.run = AsyncMock(return_value=[mock_clause])

        mock_classifier = MagicMock()
        mock_classifier.run = AsyncMock(return_value=[mock_clause])

        mock_retriever = MagicMock()
        mock_retriever.run = AsyncMock(return_value={"clause_1": []})
        mock_retriever_cls.return_value = mock_retriever

        mock_rec_gen = MagicMock()
        from backend.core.agents.recommendation_generator import Recommendation

        mock_rec_gen.run = AsyncMock(
            return_value=[
                Recommendation(
                    clause_id="clause_1",
                    plain_explanation="Broad indemnification.",
                    key_concerns=["No cap"],
                    suggested_alternative="Limit to direct damages.",
                )
            ]
        )

        with (
            patch("backend.core.orchestrator.ClauseExtractor", return_value=mock_extractor),
            patch("backend.core.orchestrator.RiskClassifier", return_value=mock_classifier),
            patch("backend.core.orchestrator.RecommendationGenerator", return_value=mock_rec_gen),
        ):
            state = await run_analysis_graph(b"fake pdf bytes", "test.pdf")

    assert state["parsed_document"] is not None
    assert len(state["extracted_clauses"]) == 1
    assert len(state["classified_clauses"]) == 1
    assert state["overall_risk_score"] > 0
    assert state["executive_summary"] != ""
    assert state["errors"] == []


@pytest.mark.asyncio
async def test_pipeline_continues_on_parse_error():
    from backend.core.orchestrator import run_analysis_graph

    with patch("backend.core.orchestrator.get_parser") as mock_get_parser:
        mock_parser = MagicMock()
        mock_parser.parse = AsyncMock(side_effect=ValueError("Bad PDF"))
        mock_get_parser.return_value = mock_parser

        with patch("backend.core.orchestrator.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm

            with (
                patch("backend.core.orchestrator.ClauseExtractor") as mock_ext_cls,
                patch("backend.core.orchestrator.RiskClassifier") as mock_cls_cls,
                patch("backend.core.orchestrator.PrecedentRetriever") as mock_ret_cls,
                patch("backend.core.orchestrator.RecommendationGenerator") as mock_rec_cls,
            ):
                mock_ext_cls.return_value.run = AsyncMock(return_value=[])
                mock_cls_cls.return_value.run = AsyncMock(return_value=[])
                mock_ret_cls.return_value.run = AsyncMock(return_value={})
                mock_rec_cls.return_value.run = AsyncMock(return_value=[])

                state = await run_analysis_graph(b"bad bytes", "broken.pdf")

    assert len(state["errors"]) > 0
    assert "Parsing failed" in state["errors"][0]
    assert state["classified_clauses"] == []


@pytest.mark.asyncio
async def test_progress_callback_called():
    from backend.core.orchestrator import run_analysis_graph

    progress_values: list[int] = []

    def track_progress(pct: int) -> None:
        progress_values.append(pct)

    mock_doc = make_parsed_doc()

    with (
        patch("backend.core.orchestrator.get_parser") as mock_get_parser,
        patch("backend.core.orchestrator.get_llm") as mock_get_llm,
        patch("backend.core.orchestrator.ClauseExtractor") as mock_ext_cls,
        patch("backend.core.orchestrator.RiskClassifier") as mock_cls_cls,
        patch("backend.core.orchestrator.PrecedentRetriever") as mock_ret_cls,
        patch("backend.core.orchestrator.RecommendationGenerator") as mock_rec_cls,
    ):
        mock_get_parser.return_value.parse = AsyncMock(return_value=mock_doc)
        mock_get_llm.return_value = MagicMock()
        mock_ext_cls.return_value.run = AsyncMock(return_value=[])
        mock_cls_cls.return_value.run = AsyncMock(return_value=[])
        mock_ret_cls.return_value.run = AsyncMock(return_value={})
        mock_rec_cls.return_value.run = AsyncMock(return_value=[])

        await run_analysis_graph(b"pdf", "test.pdf", progress_callback=track_progress)

    assert 100 in progress_values
    assert progress_values == sorted(progress_values)  # monotonically increasing
