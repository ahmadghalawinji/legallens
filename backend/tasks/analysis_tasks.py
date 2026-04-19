from backend.celery_app import celery_app


@celery_app.task(bind=True, name="analysis_tasks.analyze_contract")
def analyze_contract_task(self, task_id: str, file_bytes: bytes, filename: str) -> dict:
    """Celery task for async contract analysis. Full implementation in Phase 3+."""
    return {"task_id": task_id, "status": "pending"}
