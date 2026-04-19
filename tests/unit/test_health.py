import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_contracts_stub(client):
    response = await client.post("/api/v1/contracts/analyze")
    assert response.status_code == 200
    assert response.json()["status"] == "not implemented"


@pytest.mark.asyncio
async def test_tasks_stub(client):
    response = await client.get("/api/v1/tasks/some-task-id")
    assert response.status_code == 200
    assert response.json()["status"] == "not implemented"
