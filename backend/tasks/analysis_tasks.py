import asyncio
import json
import logging

import redis as redis_lib

from backend.celery_app import celery_app
from backend.config import settings

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
_TASK_TTL = 3600  # 1 hour


def _set_progress(task_id: str, progress: int, status: str = "processing") -> None:
    _redis.setex(f"task:{task_id}", _TASK_TTL, json.dumps({"status": status, "progress": progress}))


def _set_result(task_id: str, result: dict) -> None:
    _redis.setex(
        f"task:{task_id}",
        _TASK_TTL,
        json.dumps({"status": "completed", "progress": 100, "result": result}),
    )


def _set_error(task_id: str, error: str) -> None:
    _redis.setex(
        f"task:{task_id}",
        _TASK_TTL,
        json.dumps({"status": "failed", "progress": 0, "error": error}),
    )


def get_task_state(task_id: str) -> dict | None:
    """Retrieve task state from Redis.

    Args:
        task_id: The task identifier.

    Returns:
        Task state dict or None if not found.
    """
    raw = _redis.get(f"task:{task_id}")
    if raw is None:
        return None
    return json.loads(raw)


@celery_app.task(bind=True, name="analysis_tasks.analyze_contract")
def analyze_contract_task(self, task_id: str, file_bytes_hex: str, filename: str) -> None:
    """Celery task: parse → extract → classify a contract.

    Args:
        task_id: Unique task identifier (also used as Redis key).
        file_bytes_hex: Hex-encoded file bytes (JSON-serializable).
        filename: Original filename.
    """
    from backend.services.analysis_service import run_analysis

    _set_progress(task_id, 0, "processing")

    def _progress(pct: int) -> None:
        _set_progress(task_id, pct)

    try:
        file_bytes = bytes.fromhex(file_bytes_hex)
        result = asyncio.get_event_loop().run_until_complete(
            run_analysis(file_bytes, filename, progress_callback=_progress)
        )
        _set_result(task_id, result.model_dump())
    except Exception as exc:
        logger.error("Task %s failed: %s", task_id, exc)
        _set_error(task_id, str(exc))
        raise
