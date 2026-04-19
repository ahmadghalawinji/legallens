from fastapi import APIRouter, HTTPException

from backend.api.schemas.tasks import AnalysisResult, TaskResponse, TaskStatus
from backend.tasks.analysis_tasks import get_task_state

router = APIRouter()


@router.get("/{task_id}", response_model=dict)
async def get_task(task_id: str) -> dict:
    """Poll the status of an analysis task.

    Args:
        task_id: The task identifier returned by POST /contracts/analyze.

    Returns:
        Standard envelope with TaskResponse.
    """
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    result = None
    if state.get("result"):
        result = AnalysisResult(**state["result"])

    task_response = TaskResponse(
        task_id=task_id,
        status=TaskStatus(state["status"]),
        progress=state.get("progress", 0),
        result=result,
        error=state.get("error"),
    )

    return {
        "status": "ok",
        "data": task_response.model_dump(),
        "errors": None,
        "metadata": None,
    }
