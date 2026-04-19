from unittest.mock import patch

import pytest

from backend.config import settings


def test_get_llm_unknown_provider():
    from backend.core.llm import get_llm

    with patch.object(settings, "llm_provider", "unknown"), pytest.raises(
        ValueError, match="Unknown LLM provider"
    ):
        get_llm()


def test_get_embeddings_import():
    """Verify get_embeddings is importable."""
    from backend.core.llm import get_embeddings

    assert callable(get_embeddings)
