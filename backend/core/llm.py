"""
LLM provider abstraction. All agents import from here, never from provider-specific packages.
Supports: Ollama (local), Groq (free tier), HuggingFace (free tier).
"""
from langchain_core.language_models import BaseChatModel

from backend.config import settings


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """Get the configured LLM instance.

    Args:
        temperature: Sampling temperature (0.0 = deterministic).

    Returns:
        A LangChain BaseChatModel for the configured provider.
    """
    match settings.llm_provider:
        case "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=temperature,
            )
        case "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                temperature=temperature,
            )
        case "huggingface":
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

            llm = HuggingFaceEndpoint(
                repo_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
                huggingfacehub_api_token=settings.hf_api_token,
                temperature=temperature,
            )
            return ChatHuggingFace(llm=llm)
        case _:
            raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_embeddings():
    """Get local sentence-transformers embeddings. No API needed.

    Returns:
        LangChain Embeddings backed by sentence-transformers (CPU).
    """
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
    )
