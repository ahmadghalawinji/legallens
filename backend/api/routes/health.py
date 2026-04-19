import logging

import redis as redis_lib
from fastapi import APIRouter

from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def _check_redis() -> bool:
    try:
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        return True
    except Exception:
        return False


def _check_chromadb() -> bool:
    try:
        import httpx

        resp = httpx.get(
            f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1/heartbeat",
            timeout=2,
        )
        return resp.status_code == 200
    except Exception:
        return False


@router.get("/health")
async def health_check() -> dict:
    """Health check with dependency status."""
    redis_ok = _check_redis()
    chroma_ok = _check_chromadb()

    services = {
        "redis": "ok" if redis_ok else "unavailable",
        "chromadb": "ok" if chroma_ok else "unavailable",
        "llm_provider": settings.llm_provider,
    }

    overall = "ok" if redis_ok else "degraded"

    return {
        "status": overall,
        "data": services,
        "errors": None,
        "metadata": None,
    }
