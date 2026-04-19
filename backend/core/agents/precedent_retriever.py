import logging

from pydantic import BaseModel

from backend.api.schemas.clauses import ClassifiedClause, RiskLevel
from backend.knowledge.retriever import hybrid_search

logger = logging.getLogger(__name__)

# Only retrieve precedents for MEDIUM and HIGH risk clauses
_RETRIEVAL_THRESHOLD = {RiskLevel.MEDIUM, RiskLevel.HIGH}
_TOP_K = 3


class Precedent(BaseModel):
    """A retrieved legal precedent relevant to a clause."""

    id: str
    text: str
    clause_type: str
    source: str
    relevance_score: float


class PrecedentRetriever:
    """Retrieve legal precedents for medium/high-risk clauses via hybrid search."""

    async def run(self, clauses: list[ClassifiedClause]) -> dict[str, list[Precedent]]:
        """Retrieve precedents for all MEDIUM/HIGH risk clauses.

        Args:
            clauses: Classified clauses from RiskClassifier.

        Returns:
            Mapping of clause_id → list of Precedent objects.
        """
        results: dict[str, list[Precedent]] = {}

        for clause in clauses:
            if clause.risk_level not in _RETRIEVAL_THRESHOLD:
                results[clause.id] = []
                continue

            try:
                precedents = await self._retrieve_for_clause(clause)
                results[clause.id] = precedents
                logger.debug(
                    "Retrieved %d precedents for clause %s", len(precedents), clause.id
                )
            except Exception as exc:
                logger.error("Precedent retrieval failed for clause %s: %s", clause.id, exc)
                results[clause.id] = []

        return results

    async def _retrieve_for_clause(self, clause: ClassifiedClause) -> list[Precedent]:
        """Run hybrid search for a single clause."""
        hits = hybrid_search(
            query=clause.text,
            top_k=_TOP_K,
            clause_type=clause.clause_type.value,
        )

        return [
            Precedent(
                id=hit["id"],
                text=hit["text"],
                clause_type=hit.get("metadata", {}).get("clause_type", "other"),
                source=hit.get("metadata", {}).get("source", "unknown"),
                relevance_score=hit.get("rrf_score", 0.0),
            )
            for hit in hits
        ]
