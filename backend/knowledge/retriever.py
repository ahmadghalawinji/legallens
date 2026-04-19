import logging

from rank_bm25 import BM25Okapi

from backend.knowledge.vector_store import dense_search

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _reciprocal_rank_fusion(
    dense_hits: list[dict],
    sparse_hits: list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge dense and sparse results via Reciprocal Rank Fusion.

    Args:
        dense_hits: Results from dense (embedding) search, ranked by relevance.
        sparse_hits: Results from BM25 search, ranked by score.
        k: RRF constant (default 60 per the original paper).

    Returns:
        Merged and re-ranked list of hits with rrf_score.
    """
    scores: dict[str, float] = {}
    by_id: dict[str, dict] = {}

    for rank, hit in enumerate(dense_hits):
        doc_id = hit["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        by_id[doc_id] = hit

    for rank, hit in enumerate(sparse_hits):
        doc_id = hit["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        if doc_id not in by_id:
            by_id[doc_id] = hit

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for doc_id, score in ranked:
        result = dict(by_id[doc_id])
        result["rrf_score"] = round(score, 6)
        results.append(result)
    return results


def hybrid_search(
    query: str,
    top_k: int = 5,
    clause_type: str | None = None,
) -> list[dict]:
    """Hybrid search combining dense embeddings and BM25.

    Runs dense search via ChromaDB and sparse BM25 over the dense candidates,
    then merges with Reciprocal Rank Fusion.

    Args:
        query: The clause text or search query.
        top_k: Number of final results to return.
        clause_type: Optional filter to restrict results to a clause type.

    Returns:
        Top-k results ranked by RRF score, each with id, text, metadata, rrf_score.
    """
    where = {"clause_type": clause_type} if clause_type else None
    dense_hits = dense_search(query, n_results=min(top_k * 3, 30), where=where)

    if not dense_hits:
        return []

    # BM25 over the dense candidate pool
    corpus = [hit["text"] for hit in dense_hits]
    tokenized_corpus = [_tokenize(doc) for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))

    sparse_hits = sorted(
        [{"id": dense_hits[i]["id"], "text": dense_hits[i]["text"],
          "metadata": dense_hits[i]["metadata"], "bm25_score": float(scores[i])}
         for i in range(len(dense_hits))],
        key=lambda x: x["bm25_score"],
        reverse=True,
    )

    merged = _reciprocal_rank_fusion(dense_hits, sparse_hits)
    return merged[:top_k]
