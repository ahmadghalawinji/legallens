import logging
from typing import Any

import chromadb

from backend.config import settings
from backend.knowledge.embeddings import embed_batch, embed_text

logger = logging.getLogger(__name__)

COLLECTION_NAME = "legal_provisions"


def _get_client() -> Any:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def _get_collection(client: Any) -> Any:
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_provisions(
    ids: list[str],
    texts: list[str],
    metadatas: list[dict[str, str | int | float | bool]],
) -> None:
    """Upsert legal provisions into ChromaDB.

    Args:
        ids: Unique identifiers for each provision.
        texts: Raw provision text.
        metadatas: Associated metadata (source, clause_type, etc.).
    """
    client = _get_client()
    collection = _get_collection(client)
    embeddings = embed_batch(texts)
    collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)  # type: ignore[arg-type]
    logger.debug("Upserted %d provisions", len(ids))


def dense_search(
    query: str,
    n_results: int = 10,
    where: dict | None = None,
) -> list[dict]:
    """Dense (embedding) search over ChromaDB.

    Args:
        query: Query text.
        n_results: Number of results to return.
        where: Optional ChromaDB metadata filter.

    Returns:
        List of result dicts with id, text, metadata, and distance.
    """
    client = _get_client()
    collection = _get_collection(client)
    query_embedding = embed_text(query)

    kwargs: dict = {"query_embeddings": [query_embedding], "n_results": n_results}
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    hits = []
    ids_list = results["ids"][0] if results["ids"] else []
    docs_list = results["documents"][0] if results["documents"] else []
    meta_list = results["metadatas"][0] if results["metadatas"] else []
    dist_list = results["distances"][0] if results["distances"] else []
    for i, doc_id in enumerate(ids_list):
        hits.append(
            {
                "id": doc_id,
                "text": docs_list[i] if i < len(docs_list) else "",
                "metadata": meta_list[i] if i < len(meta_list) else {},
                "distance": dist_list[i] if i < len(dist_list) else 0.0,
            }
        )
    return hits


def count_provisions() -> int:
    """Return total number of indexed provisions."""
    client = _get_client()
    collection = _get_collection(client)
    return collection.count()
