"""Artifact management service (REQ-022).

Stores and serves structured artifacts (code, markdown, text, HTML, reports)
produced during agent runs.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class Artifact:
    """Represents a generated artifact with metadata and content."""

    id: str
    name: str
    mime_type: str
    content: str
    conversation_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    size_bytes: int = 0

    def __post_init__(self) -> None:
        if not self.size_bytes:
            self.size_bytes = len(self.content.encode("utf-8"))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class ArtifactService:
    """Service managing creation, retrieval, and disk storage of artifacts."""

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        raw_dir = (
            storage_dir
            if storage_dir is not None
            else os.getenv("ARTIFACT_STORAGE_DIR", "/tmp/forge_artifacts")
        )
        self.storage_dir = Path(raw_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._memory_store: dict[str, Artifact] = {}

    def create_artifact(
        self,
        name: str,
        content: str,
        mime_type: str = "text/plain",
        conversation_id: str | None = None,
    ) -> Artifact:
        """Create and persist a new artifact."""
        artifact_id = str(uuid.uuid4())
        artifact = Artifact(
            id=artifact_id,
            name=name,
            mime_type=mime_type,
            content=content,
            conversation_id=conversation_id,
        )

        # Store in memory cache
        self._memory_store[artifact_id] = artifact

        # Persist to disk
        file_path = self.storage_dir / f"{artifact_id}_{name}"
        try:
            file_path.write_text(content, encoding="utf-8")
        except OSError:
            pass

        return artifact

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        """Retrieve an artifact by its ID."""
        return self._memory_store.get(artifact_id)

    def list_artifacts(self, conversation_id: str | None = None) -> list[Artifact]:
        """List all artifacts, optionally filtered by conversation ID."""
        artifacts = list(self._memory_store.values())
        if conversation_id:
            return [a for a in artifacts if a.conversation_id == conversation_id]
        return artifacts


_default_artifact_service = ArtifactService()


def get_artifact_service() -> ArtifactService:
    return _default_artifact_service
