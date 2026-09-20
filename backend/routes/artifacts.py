"""Artifact API routes (REQ-022).

Endpoints:
- POST /api/v1/artifacts : Create a new artifact
- GET  /api/v1/artifacts : List artifacts
- GET  /api/v1/artifacts/{id} : Retrieve artifact metadata and inline content
- GET  /api/v1/artifacts/{id}/download : Download raw artifact content with correct Content-Type
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from backend.services.artifact_service import ArtifactService, get_artifact_service

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


class CreateArtifactRequest(BaseModel):
    name: str
    content: str
    mime_type: str = "text/plain"
    conversation_id: str | None = None


@router.post("", status_code=201)
async def create_artifact_endpoint(payload: CreateArtifactRequest) -> dict[str, Any]:
    service: ArtifactService = get_artifact_service()
    artifact = service.create_artifact(
        name=payload.name,
        content=payload.content,
        mime_type=payload.mime_type,
        conversation_id=payload.conversation_id,
    )
    return {"data": artifact.to_dict()}


@router.get("")
async def list_artifacts_endpoint(conversation_id: str | None = None) -> dict[str, Any]:
    service: ArtifactService = get_artifact_service()
    artifacts = service.list_artifacts(conversation_id=conversation_id)
    return {"data": [a.to_dict() for a in artifacts]}


@router.get("/{artifact_id}")
async def get_artifact_endpoint(artifact_id: str) -> dict[str, Any]:
    service: ArtifactService = get_artifact_service()
    artifact = service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"data": artifact.to_dict()}


@router.get("/{artifact_id}/download")
async def download_artifact_endpoint(artifact_id: str) -> Response:
    service: ArtifactService = get_artifact_service()
    artifact = service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    headers = {
        "Content-Disposition": f'attachment; filename="{artifact.name}"',
    }
    return Response(
        content=artifact.content,
        media_type=artifact.mime_type,
        headers=headers,
    )
