from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

def test_a2a_agent_card():
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 200
    card = response.json()
    assert card["name"] == "Forge Agent"
    assert "delegate_task" in card["capabilities"]
    assert "tasks_send" in card["endpoints"]

@patch("backend.a2a.router.agent_task", new_callable=AsyncMock)
@patch("backend.routes.agent.stream_service.emit_event", new_callable=AsyncMock)
def test_a2a_task_send(mock_emit, mock_agent_task):
    payload = {
        "jsonrpc": "2.0",
        "id": "123",
        "method": "submit_task",
        "params": {"task": "test task"}
    }
    response = client.post("/a2a/tasks/send", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "123"
    assert data["result"]["status"] == "working"
    assert "task_id" in data["result"]

def test_a2a_task_get():
    payload = {
        "jsonrpc": "2.0",
        "id": "456",
        "method": "get_status",
        "params": {"task_id": "fake_task"}
    }
    response = client.post("/a2a/tasks/get", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "456"
    assert data["result"]["status"] == "completed"
