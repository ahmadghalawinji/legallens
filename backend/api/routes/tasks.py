from fastapi import APIRouter

router = APIRouter()


@router.get("/{task_id}")
async def get_task(task_id: str) -> dict:
    """Get task status by ID. Not yet implemented."""
    return {"status": "not implemented", "data": None, "errors": None, "metadata": None}
