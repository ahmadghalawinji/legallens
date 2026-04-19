import logging
import time
from collections.abc import Callable

from backend.api.schemas.clauses import ClassifiedClause, RiskLevel
from backend.api.schemas.tasks import AnalysisResult
from backend.core.agents.clause_extractor import ClauseExtractor
from backend.core.agents.risk_classifier import RiskClassifier
from backend.core.llm import get_llm
from backend.core.parsers import get_parser

logger = logging.getLogger(__name__)


async def run_analysis(
    file_bytes: bytes,
    filename: str,
    progress_callback: Callable[[int], None] | None = None,
) -> AnalysisResult:
    """Run the full analysis pipeline: parse → extract → classify.

    Args:
        file_bytes: Raw bytes of the uploaded contract.
        filename: Original filename (.pdf or .docx).
        progress_callback: Optional callback receiving progress 0–100.

    Returns:
        AnalysisResult with classified clauses and risk summary.
    """

    def _progress(pct: int) -> None:
        if progress_callback:
            progress_callback(pct)

    start = time.monotonic()
    _progress(0)

    # Stage 1: Parse
    logger.info("Parsing '%s'", filename)
    parser = get_parser(filename)
    document = await parser.parse(file_bytes, filename)
    _progress(20)

    # Stage 2: Extract clauses
    logger.info("Extracting clauses from '%s'", filename)
    llm = get_llm(temperature=0.0)
    extractor = ClauseExtractor(llm)
    clauses = await extractor.run(document)
    _progress(60)

    # Stage 3: Classify risk
    logger.info("Classifying %d clauses", len(clauses))
    classifier = RiskClassifier(llm)
    classified: list[ClassifiedClause] = await classifier.run(clauses)
    _progress(90)

    # Compute summary
    high = sum(1 for c in classified if c.risk_level == RiskLevel.HIGH)
    medium = sum(1 for c in classified if c.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for c in classified if c.risk_level == RiskLevel.LOW)
    overall = (sum(c.risk_score for c in classified) / len(classified)) if classified else 0.0

    elapsed = time.monotonic() - start
    _progress(100)

    logger.info(
        "Analysis complete: %d clauses (%d high, %d medium, %d low) in %.2fs",
        len(classified),
        high,
        medium,
        low,
        elapsed,
    )

    return AnalysisResult(
        filename=filename,
        clauses=classified,
        overall_risk_score=round(overall, 3),
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
        processing_time_seconds=round(elapsed, 2),
    )
