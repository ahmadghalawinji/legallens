from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    hf_api_token: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    redis_url: str = "redis://localhost:6379"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    log_level: str = "INFO"
    max_file_size_mb: int = 20
    allowed_extensions: list[str] = [".pdf", ".docx"]
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
