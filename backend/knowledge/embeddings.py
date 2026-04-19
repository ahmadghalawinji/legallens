import logging

from sentence_transformers import SentenceTransformer

from backend.config import settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s'", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single text string locally using sentence-transformers.

    Args:
        text: Input text to embed.

    Returns:
        Embedding vector as a list of floats.
    """
    model = _get_model()
    return model.encode(text, convert_to_numpy=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts locally using sentence-transformers.

    Args:
        texts: List of input texts.

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32, show_progress_bar=False)
    return [e.tolist() for e in embeddings]
