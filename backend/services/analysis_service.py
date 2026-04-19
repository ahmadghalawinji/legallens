import logging
import time
from collections.abc import Callable

from backend.api.schemas.clauses import RiskLevel
from backend.api.schemas.tasks import AnalysisResult
from backend.core.orchestrator import run_analysis_graph

logger = logging.getLogger(__name__)


async def run_analysis(
    file_bytes: bytes,
    filename: str,
    progress_callback: Callable[[int], None] | None = None,
) -> AnalysisResult:
    """Run the full analysis pipeline via the LangGraph DAG.

    Args:
        file_bytes: Raw bytes of the uploaded contract.
        filename: Original filename (.pdf or .docx).
        progress_callback: Optional callback receiving progress 0–100.

    Returns:
        AnalysisResult with classified clauses and risk summary.
    """
    start = time.monotonic()

    state = await run_analysis_graph(file_bytes, filename, progress_callback)

    classified = state.get("classified_clauses", [])
    high = sum(1 for c in classified if c.risk_level == RiskLevel.HIGH)
    medium = sum(1 for c in classified if c.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for c in classified if c.risk_level == RiskLevel.LOW)

    elapsed = time.monotonic() - start

    logger.info(
        "Analysis complete: %d clauses (%d high, %d medium, %d low) in %.2fs",
        len(classified), high, medium, low, elapsed,
    )

    return AnalysisResult(
        filename=filename,
        clauses=classified,
        overall_risk_score=state.get("overall_risk_score", 0.0),
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
        processing_time_seconds=round(elapsed, 2),
    )
