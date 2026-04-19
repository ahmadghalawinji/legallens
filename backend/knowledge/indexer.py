import logging
from collections.abc import Iterator

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


def _ledgar_provisions(limit: int) -> Iterator[tuple[str, str, dict]]:
    """Stream provisions from the LEDGAR dataset (HuggingFace, free).

    Yields:
        Tuples of (id, text, metadata).
    """
    from datasets import load_dataset

    dataset = load_dataset("lex_glue", "ledgar", split="train", streaming=True)
    for i, row in enumerate(dataset):
        if i >= limit:
            break
        clause_type = row.get("label_text", "other") or "other"
        yield (
            f"ledgar_{i}",
            row["text"],
            {"source": "ledgar", "clause_type": clause_type.lower().replace(" ", "_")},
        )


def index_corpus(source: str = "ledgar", limit: int = 5000) -> int:
    """Index legal provisions into ChromaDB.

    Args:
        source: Corpus source identifier ("ledgar").
        limit: Maximum number of provisions to index.

    Returns:
        Total number of provisions indexed.
    """
    from backend.knowledge.vector_store import upsert_provisions

    if source != "ledgar":
        raise ValueError(f"Unknown source: {source}. Supported: 'ledgar'")

    logger.info("Indexing up to %d provisions from '%s'", limit, source)

    ids: list[str] = []
    texts: list[str] = []
    metas: list[dict] = []
    total = 0

    for doc_id, text, meta in _ledgar_provisions(limit):
        ids.append(doc_id)
        texts.append(text[:2000])  # cap length
        metas.append(meta)

        if len(ids) >= _BATCH_SIZE:
            upsert_provisions(ids, texts, metas)
            total += len(ids)
            logger.info("Indexed %d / %d", total, limit)
            ids, texts, metas = [], [], []

    if ids:
        upsert_provisions(ids, texts, metas)
        total += len(ids)

    logger.info("Indexing complete: %d provisions", total)
    return total
