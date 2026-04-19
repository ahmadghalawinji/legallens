from celery import Celery

from backend.config import settings

celery_app = Celery(
    "legallens",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.tasks.analysis_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
