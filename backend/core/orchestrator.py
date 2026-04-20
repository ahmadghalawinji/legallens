import logging
from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from backend.api.schemas.clauses import ClassifiedClause, ExtractedClause, RiskLevel
from backend.core.agents.clause_extractor import ClauseExtractor
from backend.core.agents.precedent_retriever import PrecedentRetriever
from backend.core.agents.recommendation_generator import Recommendation, RecommendationGenerator
from backend.core.agents.risk_classifier import RiskClassifier
from backend.core.llm import get_llm
from backend.core.parsers import get_parser
from backend.core.parsers.base import ParsedDocument

logger = logging.getLogger(__name__)


class AnalysisState(TypedDict):
    file_bytes: bytes
    filename: str
    parsed_document: ParsedDocument | None
    extracted_clauses: list[ExtractedClause]
    classified_clauses: list[ClassifiedClause]
    recommendations: list[Recommendation]
    executive_summary: str
    overall_risk_score: float
    errors: list[str]
    progress: int
    _progress_callback: Callable[[int], None] | None


# ── graph nodes ───────────────────────────────────────────────────────────────


async def _parse_document(state: AnalysisState) -> dict:
    """Node: parse uploaded file into a ParsedDocument."""
    try:
        parser = get_parser(state["filename"])
        doc = await parser.parse(state["file_bytes"], state["filename"])
        _cb(state, 20)
        return {"parsed_document": doc, "progress": 20}
    except Exception as exc:
        logger.error("parse_document failed: %s", exc)
        return {"errors": state["errors"] + [f"Parsing failed: {exc}"], "progress": 20}


async def _extract_clauses(state: AnalysisState) -> dict:
    """Node: extract clauses from the parsed document."""
    doc = state.get("parsed_document")
    if not doc:
        return {"extracted_clauses": [], "progress": 40}
    try:
        llm = get_llm(temperature=0.0)
        extractor = ClauseExtractor(llm)
        clauses = await extractor.run(doc)
        _cb(state, 40)
        return {"extracted_clauses": clauses, "progress": 40}
    except Exception as exc:
        logger.error("extract_clauses failed: %s", exc)
        return {
            "extracted_clauses": [],
            "errors": state["errors"] + [f"Extraction failed: {exc}"],
            "progress": 40,
        }


async def _classify_and_retrieve(state: AnalysisState) -> dict:
    """Node: classify risk and retrieve precedents for each clause in parallel."""
    clauses = state.get("extracted_clauses", [])
    if not clauses:
        return {"classified_clauses": [], "progress": 75}

    llm = get_llm(temperature=0.0)
    classifier = RiskClassifier(llm)
    retriever = PrecedentRetriever()

    errors = list(state["errors"])
    try:
        classified = await classifier.run(clauses)
        precedents = await retriever.run(classified)
    except Exception as exc:
        logger.error("classify_and_retrieve failed: %s", exc)
        errors.append(f"Classification failed: {exc}")
        classified = []
        precedents = {}

    # Generate recommendations
    try:
        rec_gen = RecommendationGenerator(llm)
        recommendations = await rec_gen.run(classified, precedents)
    except Exception as exc:
        logger.error("recommendation_generator failed: %s", exc)
        errors.append(f"Recommendations failed: {exc}")
        recommendations = []

    _cb(state, 75)
    return {
        "classified_clauses": classified,
        "recommendations": recommendations,
        "errors": errors,
        "progress": 75,
    }


async def _generate_summary(state: AnalysisState) -> dict:
    """Node: build a short executive summary from classification results."""
    classified = state.get("classified_clauses", [])
    high = sum(1 for c in classified if c.risk_level == RiskLevel.HIGH)
    medium = sum(1 for c in classified if c.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for c in classified if c.risk_level == RiskLevel.LOW)

    if not classified:
        summary = "No legally significant clauses were identified in this document."
    elif high > 0:
        summary = (
            f"This contract contains {high} HIGH-risk clause(s) that require immediate attention, "
            f"{medium} MEDIUM-risk clause(s), and {low} LOW-risk clause(s). "
            "Review highlighted clauses carefully before signing."
        )
    elif medium > 0:
        summary = (
            f"This contract contains {medium} MEDIUM-risk clause(s) worth negotiating "
            f"and {low} LOW-risk clause(s). No critical issues found."
        )
    else:
        summary = (
            f"This contract appears relatively standard with {low} LOW-risk clause(s). "
            "Standard review recommended before signing."
        )

    _cb(state, 90)
    return {"executive_summary": summary, "progress": 90}


async def _compute_score(state: AnalysisState) -> dict:
    """Node: compute the overall risk score."""
    classified = state.get("classified_clauses", [])
    score = (
        sum(c.risk_score for c in classified) / len(classified) if classified else 0.0
    )
    _cb(state, 100)
    return {"overall_risk_score": round(score, 3), "progress": 100}


def _cb(state: AnalysisState, pct: int) -> None:
    cb = state.get("_progress_callback")
    if cb:
        cb(pct)


# ── graph construction ────────────────────────────────────────────────────────


def _build_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)

    graph.add_node("parse_document", _parse_document)
    graph.add_node("extract_clauses", _extract_clauses)
    graph.add_node("classify_and_retrieve", _classify_and_retrieve)
    graph.add_node("generate_summary", _generate_summary)
    graph.add_node("compute_score", _compute_score)

    graph.set_entry_point("parse_document")
    graph.add_edge("parse_document", "extract_clauses")
    graph.add_edge("extract_clauses", "classify_and_retrieve")
    graph.add_edge("classify_and_retrieve", "generate_summary")
    graph.add_edge("generate_summary", "compute_score")
    graph.add_edge("compute_score", END)

    return graph.compile()  # type: ignore[return-value]


_compiled_graph: Any = _build_graph()


async def run_analysis_graph(
    file_bytes: bytes,
    filename: str,
    progress_callback: Callable[[int], None] | None = None,
) -> AnalysisState:
    """Run the full analysis pipeline via the LangGraph DAG.

    Args:
        file_bytes: Raw contract file bytes.
        filename: Original filename.
        progress_callback: Optional callback for progress 0–100.

    Returns:
        Final AnalysisState with all results populated.
    """
    initial: AnalysisState = {
        "file_bytes": file_bytes,
        "filename": filename,
        "parsed_document": None,
        "extracted_clauses": [],
        "classified_clauses": [],
        "recommendations": [],
        "executive_summary": "",
        "overall_risk_score": 0.0,
        "errors": [],
        "progress": 0,
        "_progress_callback": progress_callback,
    }

    final_state = await _compiled_graph.ainvoke(initial)
    return final_state
