import asyncio
import logging
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from backend.api.schemas.clauses import ExtractedClause, ExtractionResult
from backend.config import settings
from backend.core.parsers.base import ParsedDocument
from backend.core.prompts.clause_extraction import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)

# Token budget per chunk — 12k chars ≈ 3k tokens, comfortable for 1B–8B models
_CHUNK_CHAR_LIMIT = 12_000
_MAX_RETRIES = 2


def _chunk_text(text: str, limit: int = _CHUNK_CHAR_LIMIT) -> list[str]:
    """Split text into chunks that fit within the token budget."""
    if len(text) <= limit:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + limit
        # Prefer splitting at a paragraph boundary
        boundary = text.rfind("\n\n", start, end)
        if boundary == -1 or boundary <= start:
            boundary = text.rfind("\n", start, end)
        if boundary == -1 or boundary <= start:
            boundary = end
        chunks.append(text[start:boundary])
        start = boundary
    return chunks


def _extract_json(raw: str) -> str:
    """Pull the first {...} block from a raw LLM response."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


def _deduplicate(clauses: list[ExtractedClause]) -> list[ExtractedClause]:
    """Remove near-duplicate clauses by text similarity (exact prefix match)."""
    seen: list[str] = []
    unique: list[ExtractedClause] = []
    for clause in clauses:
        prefix = clause.text[:80].strip().lower()
        if not any(prefix == s for s in seen):
            seen.append(prefix)
            unique.append(clause)
    return unique


class ClauseExtractor:
    """Extract legally significant clauses from a parsed document."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm
        self._parser = PydanticOutputParser(pydantic_object=ExtractionResult)

    async def run(self, document: ParsedDocument) -> list[ExtractedClause]:
        """Extract clauses from a parsed document.

        Args:
            document: The parsed contract document.

        Returns:
            Deduplicated list of extracted clauses.
        """
        text = document.full_text
        if not text.strip():
            logger.warning("Empty document passed to ClauseExtractor")
            return []

        chunks = _chunk_text(text)
        logger.debug("ClauseExtractor: %d chunk(s) for '%s'", len(chunks), document.filename)

        all_clauses: list[ExtractedClause] = []
        for i, chunk in enumerate(chunks):
            if i > 0 and settings.llm_request_delay > 0:
                await asyncio.sleep(settings.llm_request_delay)
            clauses = await self._extract_chunk(chunk, chunk_index=i)
            all_clauses.extend(clauses)

        deduped = _deduplicate(all_clauses)

        # Assign stable UUIDs
        for j, clause in enumerate(deduped):
            clause.id = f"clause_{j + 1}"

        logger.debug("ClauseExtractor: extracted %d clauses", len(deduped))
        return deduped

    async def _extract_chunk(self, text: str, chunk_index: int) -> list[ExtractedClause]:
        """Run extraction on a single text chunk with retry logic."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=USER_TEMPLATE.format(contract_text=text)),
        ]

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._llm.ainvoke(messages)
                raw = response.content if hasattr(response, "content") else str(response)
                raw = _extract_json(raw)
                result = self._parser.parse(raw)
                return result.clauses
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "ClauseExtractor chunk %d attempt %d failed: %s",
                    chunk_index,
                    attempt + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    # Append error feedback and retry
                    messages.append(
                        HumanMessage(
                            content=f"Your previous response was invalid JSON. Error: {exc}. "
                            "Please output ONLY the JSON object with the 'clauses' array."
                        )
                    )

        logger.error(
            "ClauseExtractor chunk %d failed after %d attempts: %s",
            chunk_index,
            _MAX_RETRIES + 1,
            last_error,
        )
        return []
