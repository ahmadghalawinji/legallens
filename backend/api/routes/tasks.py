from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from backend.api.schemas.tasks import AnalysisResult, TaskResponse, TaskStatus
from backend.tasks.analysis_tasks import get_task_state

router = APIRouter()


@router.get("/{task_id}/report", response_class=HTMLResponse)
async def get_task_report_html(task_id: str) -> HTMLResponse:
    """Download the HTML analysis report for a completed task.

    Args:
        task_id: The task identifier returned by POST /contracts/analyze.

    Returns:
        HTML report document.
    """
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    if state.get("status") != "success" or not state.get("result"):
        raise HTTPException(status_code=409, detail="Analysis not yet complete.")

    from backend.services.report_service import generate_report_html

    result = AnalysisResult(**state["result"])
    html = generate_report_html(result)
    return HTMLResponse(content=html)


@router.get("/{task_id}/report.pdf")
async def get_task_report_pdf(task_id: str) -> Response:
    """Download the PDF analysis report for a completed task.

    Args:
        task_id: The task identifier returned by POST /contracts/analyze.

    Returns:
        PDF binary.
    """
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    if state.get("status") != "success" or not state.get("result"):
        raise HTTPException(status_code=409, detail="Analysis not yet complete.")

    from backend.services.report_service import generate_report_pdf

    result = AnalysisResult(**state["result"])
    pdf_bytes = generate_report_pdf(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="legallens_{task_id}.pdf"'},
    )


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
