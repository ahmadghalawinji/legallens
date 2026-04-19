import uuid

from fastapi import APIRouter, Depends, UploadFile

from backend.api.dependencies import validate_upload
from backend.api.schemas.contracts import AnalyzeResponse
from backend.tasks.analysis_tasks import _set_progress, analyze_contract_task

router = APIRouter()


@router.post("/analyze", response_model=dict, status_code=202)
async def analyze_contract(
    file: UploadFile = Depends(validate_upload),  # noqa: B008
) -> dict:
    """Accept a contract upload and start async analysis.

    Args:
        file: Validated PDF or DOCX upload (≤20MB).

    Returns:
        Standard envelope with task_id.
    """
    task_id = str(uuid.uuid4())
    file_bytes = await file.read()

    # Initialise task state before dispatching so polls don't get 404
    _set_progress(task_id, 0, "pending")

    analyze_contract_task.delay(task_id, file_bytes.hex(), file.filename or "contract")

    response = AnalyzeResponse(task_id=task_id)
    return {
        "status": "accepted",
        "data": response.model_dump(),
        "errors": None,
        "metadata": {"filename": file.filename},
    }
