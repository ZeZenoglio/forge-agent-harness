"""Unit tests for Artifact storage service and API endpoints (REQ-022)."""

from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.artifact_service import ArtifactService


@pytest.fixture
def temp_storage_dir() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.unit
@pytest.mark.smoke
def test_artifact_service_lifecycle(
    temp_storage_dir: tempfile.TemporaryDirectory[str],
) -> None:
    service = ArtifactService(storage_dir=temp_storage_dir.name)

    artifact = service.create_artifact(
        name="report.md",
        content="# Test Report\nEverything passed.",
        mime_type="text/markdown",
        conversation_id="conv-123",
    )

    assert artifact.id is not None
    assert artifact.name == "report.md"
    assert artifact.mime_type == "text/markdown"
    assert artifact.conversation_id == "conv-123"
    assert artifact.size_bytes > 0

    retrieved = service.get_artifact(artifact.id)
    assert retrieved is not None
    assert retrieved.content == "# Test Report\nEverything passed."

    listed = service.list_artifacts(conversation_id="conv-123")
    assert len(listed) == 1
    assert listed[0].id == artifact.id


@pytest.mark.unit
def test_artifact_api_endpoints(client: TestClient) -> None:
    # 1. Create artifact via POST /api/v1/artifacts
    post_res = client.post(
        "/api/v1/artifacts",
        json={
            "name": "sample.py",
            "content": "print('hello artifact')",
            "mime_type": "text/x-python",
            "conversation_id": "conv-test",
        },
    )
    assert post_res.status_code == 201
    created_data = post_res.json()["data"]
    artifact_id = created_data["id"]

    # 2. List artifacts via GET /api/v1/artifacts
    list_res = client.get("/api/v1/artifacts?conversation_id=conv-test")
    assert list_res.status_code == 200
    assert any(a["id"] == artifact_id for a in list_res.json()["data"])

    # 3. Retrieve metadata via GET /api/v1/artifacts/{id}
    get_res = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "sample.py"

    # 4. Download artifact via GET /api/v1/artifacts/{id}/download
    dl_res = client.get(f"/api/v1/artifacts/{artifact_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"].startswith("text/x-python")
    assert "print('hello artifact')" in dl_res.text
