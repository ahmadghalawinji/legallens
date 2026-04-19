"""Integration tests for the REST API.

These tests mock Celery task dispatch and Redis state so they run without
live infrastructure. They verify HTTP behaviour, not end-to-end pipeline logic.
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from reportlab.pdfgen import canvas

from backend.main import app

# ── helpers ───────────────────────────────────────────────────────────────────


def make_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 700, "This is a test contract.")
    c.showPage()
    c.save()
    return buf.getvalue()


def make_docx_bytes() -> bytes:
    from docx import Document

    doc = Document()
    doc.add_paragraph("This is a test contract clause.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── health ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    with patch("backend.api.routes.health._check_redis", return_value=True), patch(
        "backend.api.routes.health._check_chromadb", return_value=True
    ):
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["redis"] == "ok"
    assert body["data"]["chromadb"] == "ok"


@pytest.mark.asyncio
async def test_health_degraded_without_redis(client):
    with patch("backend.api.routes.health._check_redis", return_value=False), patch(
        "backend.api.routes.health._check_chromadb", return_value=True
    ):
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


# ── contracts/analyze ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_pdf_returns_202(client):
    with patch("backend.api.routes.contracts.analyze_contract_task") as mock_celery, patch(
        "backend.api.routes.contracts._set_progress"
    ):
        mock_celery.delay = MagicMock()
        resp = await client.post(
            "/api/v1/contracts/analyze",
            files={"file": ("contract.pdf", make_pdf_bytes(), "application/pdf")},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert "task_id" in body["data"]
    assert len(body["data"]["task_id"]) == 36  # UUID4


@pytest.mark.asyncio
async def test_analyze_docx_returns_202(client):
    with patch("backend.api.routes.contracts.analyze_contract_task") as mock_celery, patch(
        "backend.api.routes.contracts._set_progress"
    ):
        mock_celery.delay = MagicMock()
        resp = await client.post(
            "/api/v1/contracts/analyze",
            files={"file": ("contract.docx", make_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},  # noqa: E501
        )

    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_analyze_rejects_unsupported_type(client):
    resp = await client.post(
        "/api/v1/contracts/analyze",
        files={"file": ("contract.txt", b"plain text", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_rejects_oversized_file(client):
    # Create a file larger than MAX_FILE_SIZE_MB
    big_bytes = b"x" * (21 * 1024 * 1024)  # 21 MB
    resp = await client.post(
        "/api/v1/contracts/analyze",
        files={"file": ("big.pdf", big_bytes, "application/pdf")},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_analyze_rejects_missing_file(client):
    resp = await client.post("/api/v1/contracts/analyze")
    assert resp.status_code == 422


# ── tasks/{task_id} ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    with patch("backend.api.routes.tasks.get_task_state", return_value=None):
        resp = await client.get("/api/v1/tasks/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_task_pending(client):
    with patch(
        "backend.api.routes.tasks.get_task_state",
        return_value={"status": "pending", "progress": 0},
    ):
        resp = await client.get("/api/v1/tasks/some-task-id")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "pending"
    assert body["data"]["progress"] == 0
    assert body["data"]["result"] is None


@pytest.mark.asyncio
async def test_get_task_processing(client):
    with patch(
        "backend.api.routes.tasks.get_task_state",
        return_value={"status": "processing", "progress": 60},
    ):
        resp = await client.get("/api/v1/tasks/some-task-id")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "processing"
    assert body["data"]["progress"] == 60


@pytest.mark.asyncio
async def test_get_task_completed(client):
    completed_state = {
        "status": "completed",
        "progress": 100,
        "result": {
            "filename": "contract.pdf",
            "clauses": [],
            "overall_risk_score": 0.3,
            "high_risk_count": 0,
            "medium_risk_count": 1,
            "low_risk_count": 2,
            "processing_time_seconds": 1.5,
        },
    }
    with patch("backend.api.routes.tasks.get_task_state", return_value=completed_state):
        resp = await client.get("/api/v1/tasks/some-task-id")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "completed"
    assert body["data"]["result"]["filename"] == "contract.pdf"
    assert body["data"]["result"]["overall_risk_score"] == 0.3


@pytest.mark.asyncio
async def test_get_task_failed(client):
    with patch(
        "backend.api.routes.tasks.get_task_state",
        return_value={"status": "failed", "progress": 0, "error": "Parse error"},
    ):
        resp = await client.get("/api/v1/tasks/some-task-id")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "failed"
    assert body["data"]["error"] == "Parse error"
