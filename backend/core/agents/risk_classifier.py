import asyncio
import logging
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from backend.api.schemas.clauses import ClassifiedClause, ExtractedClause, RiskLevel
from backend.core.prompts.risk_classification import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2


class _RiskVerdict(BaseModel):
    risk_level: RiskLevel
    risk_score: float
    risk_explanation: str
    reasoning: str


def _extract_json(raw: str) -> str:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


class RiskClassifier:
    """Classify the risk level of extracted contract clauses using chain-of-thought."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm
        self._parser = PydanticOutputParser(pydantic_object=_RiskVerdict)

    async def run(self, clauses: list[ExtractedClause]) -> list[ClassifiedClause]:
        """Classify all clauses in parallel.

        Args:
            clauses: Extracted clauses from ClauseExtractor.

        Returns:
            List of ClassifiedClause with risk assessments.
        """
        if not clauses:
            return []

        tasks = [self._classify_clause(clause) for clause in clauses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        classified: list[ClassifiedClause] = []
        for clause, result in zip(clauses, results, strict=True):
            if isinstance(result, Exception):
                logger.error("Failed to classify clause %s: %s", clause.id, result)
                # Fallback: keep clause with MEDIUM risk rather than dropping it
                classified.append(
                    ClassifiedClause(
                        **clause.model_dump(),
                        risk_level=RiskLevel.MEDIUM,
                        risk_score=0.5,
                        risk_explanation="Classification failed — flagged for manual review.",
                        reasoning="Error during automated classification.",
                    )
                )
            else:
                classified.append(result)

        logger.debug("RiskClassifier: classified %d clauses", len(classified))
        return classified

    async def _classify_clause(self, clause: ExtractedClause) -> ClassifiedClause:
        """Classify a single clause with retry logic."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=USER_TEMPLATE.format(
                    clause_type=clause.clause_type.value,
                    clause_text=clause.text,
                )
            ),
        ]

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._llm.ainvoke(messages)
                raw = response.content if hasattr(response, "content") else str(response)
                raw = _extract_json(raw)
                verdict = self._parser.parse(raw)
                return ClassifiedClause(
                    **clause.model_dump(),
                    risk_level=verdict.risk_level,
                    risk_score=max(0.0, min(1.0, verdict.risk_score)),
                    risk_explanation=verdict.risk_explanation,
                    reasoning=verdict.reasoning,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "RiskClassifier clause %s attempt %d failed: %s",
                    clause.id,
                    attempt + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    messages.append(
                        HumanMessage(
                            content=f"Your previous response was invalid JSON. Error: {exc}. "
                            "Please output ONLY the JSON object with risk_level, risk_score, "
                            "risk_explanation, and reasoning fields."
                        )
                    )

        raise RuntimeError(
            f"RiskClassifier failed after {_MAX_RETRIES + 1} attempts: {last_error}"
        )
