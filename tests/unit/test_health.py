from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    with patch("backend.api.routes.health._check_redis", return_value=True), patch(
        "backend.api.routes.health._check_chromadb", return_value=True
    ):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_degraded_no_redis(client):
    with patch("backend.api.routes.health._check_redis", return_value=False), patch(
        "backend.api.routes.health._check_chromadb", return_value=False
    ):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_contracts_requires_file(client):
    response = await client.post("/api/v1/contracts/analyze")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_task_not_found(client):
    with patch("backend.api.routes.tasks.get_task_state", return_value=None):
        response = await client.get("/api/v1/tasks/unknown-id")
    assert response.status_code == 404
