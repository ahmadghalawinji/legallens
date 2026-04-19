from backend.config import settings


def test_defaults():
    assert settings.llm_provider == "ollama"
    assert settings.max_file_size_mb == 20
    assert ".pdf" in settings.allowed_extensions
    assert ".docx" in settings.allowed_extensions


def test_cors_origins():
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0
