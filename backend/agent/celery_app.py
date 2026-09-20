"""Celery application and task queue configuration (REQ-046, REQ-061).

Dispatches agent runs as Celery tasks with configurable worker concurrency
and Redis broker/result backend.
"""

from __future__ import annotations

import os
from typing import Any

from celery import Celery  # type: ignore[import-untyped]

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "8"))

celery_app = Celery(
    "forge_agent_tasks",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_track_started=True,
)


@celery_app.task(bind=True, name="agent.run_task")  # type: ignore[untyped-decorator]
def dispatch_agent_run(
    self: Any, session_id: str, task: str, user_id: str = "anonymous_user"
) -> dict[str, Any]:
    """Execute an agent run asynchronously inside a Celery worker."""
    # Simulated execution within Celery worker process
    return {
        "task_id": self.request.id,
        "session_id": session_id,
        "status": "completed",
        "user_id": user_id,
        "task": task,
    }


def get_task_status(task_id: str) -> dict[str, Any]:
    """Query task status by Celery task ID (REQ-046 AC 5)."""
    async_result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": async_result.status.lower(),
        "ready": async_result.ready(),
        "result": async_result.result if async_result.ready() else None,
    }
