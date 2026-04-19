import logging
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from backend.api.schemas.clauses import ClassifiedClause
from backend.core.agents.precedent_retriever import Precedent
from backend.core.prompts.recommendation import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_DISCLAIMER = "This is not legal advice. Consult a qualified attorney before signing."


class Recommendation(BaseModel):
    """Plain-language recommendation for a contract clause."""

    clause_id: str
    plain_explanation: str
    key_concerns: list[str]
    suggested_alternative: str
    disclaimer: str = _DISCLAIMER


class _RecommendationOutput(BaseModel):
    plain_explanation: str
    key_concerns: list[str]
    suggested_alternative: str
    disclaimer: str


def _extract_json(raw: str) -> str:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


class RecommendationGenerator:
    """Generate plain-language recommendations for each classified clause."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm
        self._parser = PydanticOutputParser(pydantic_object=_RecommendationOutput)

    async def run(
        self,
        clauses: list[ClassifiedClause],
        precedents: dict[str, list[Precedent]],
    ) -> list[Recommendation]:
        """Generate recommendations for all clauses.

        Args:
            clauses: Classified clauses with risk assessments.
            precedents: Mapping clause_id → list of retrieved precedents.

        Returns:
            List of Recommendation objects, one per clause.
        """
        recommendations = []
        for clause in clauses:
            rec = await self._generate(clause, precedents.get(clause.id, []))
            recommendations.append(rec)
        return recommendations

    async def _generate(
        self, clause: ClassifiedClause, precedents: list[Precedent]
    ) -> Recommendation:
        """Generate a recommendation for a single clause."""
        precedents_text = (
            "\n".join(f"- {p.text[:300]}" for p in precedents)
            if precedents
            else "No specific precedents found."
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=USER_TEMPLATE.format(
                    clause_type=clause.clause_type.value,
                    risk_level=clause.risk_level.value,
                    risk_explanation=clause.risk_explanation,
                    clause_text=clause.text,
                    precedents_text=precedents_text,
                )
            ),
        ]

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._llm.ainvoke(messages)
                raw = response.content if hasattr(response, "content") else str(response)
                raw = _extract_json(raw)
                output = self._parser.parse(raw)
                return Recommendation(
                    clause_id=clause.id,
                    plain_explanation=output.plain_explanation,
                    key_concerns=output.key_concerns,
                    suggested_alternative=output.suggested_alternative,
                    disclaimer=_DISCLAIMER,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "RecommendationGenerator clause %s attempt %d failed: %s",
                    clause.id, attempt + 1, exc,
                )
                if attempt < _MAX_RETRIES:
                    messages.append(
                        HumanMessage(
                            content=f"Invalid JSON. Error: {exc}. Output ONLY the JSON object."
                        )
                    )

        logger.error(
            "RecommendationGenerator failed for clause %s: %s", clause.id, last_error
        )
        return Recommendation(
            clause_id=clause.id,
            plain_explanation=clause.risk_explanation,
            key_concerns=["Manual review recommended"],
            suggested_alternative="Seek legal counsel to negotiate this clause.",
            disclaimer=_DISCLAIMER,
        )
