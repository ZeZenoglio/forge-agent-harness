import asyncio
from unittest.mock import MagicMock, patch

from backend.agent.celery_app import celery_app, dispatch_agent_run, get_task_status
from scripts.load_test import run_load_test


def test_celery_concurrency_configuration() -> None:
    # Verify worker concurrency is configured
    assert celery_app.conf.worker_concurrency >= 1
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.timezone == "UTC"


def test_dispatch_agent_run_task() -> None:
    async_res = dispatch_agent_run.apply(
        args=["session-xyz", "Analyze dataset", "user-1"]
    )
    res = async_res.result
    assert res["session_id"] == "session-xyz"
    assert res["status"] == "completed"
    assert res["task"] == "Analyze dataset"
    assert res["user_id"] == "user-1"
    assert "task_id" in res


def test_get_task_status() -> None:
    with patch("backend.agent.celery_app.celery_app.AsyncResult") as mock_async:
        mock_instance = MagicMock()
        mock_instance.status = "SUCCESS"
        mock_instance.ready.return_value = True
        mock_instance.result = {"status": "completed"}
        mock_async.return_value = mock_instance

        status = get_task_status("mock-task-id")
        assert status["status"] == "success"
        assert status["ready"] is True
        assert status["result"] == {"status": "completed"}


def test_load_test_runner_mock() -> None:
    async def mock_session(client, base_url, idx, results):
        results.append({"user_index": idx, "duration_seconds": 0.05, "errors": 0})

    with patch("scripts.load_test.simulate_user_session", side_effect=mock_session):
        report = asyncio.run(
            run_load_test(
                base_url="http://testserver", concurrency=5, total_sessions=10
            )
        )

    assert report["concurrency_target"] == 5
    assert report["total_sessions"] == 10
    assert report["total_errors"] == 0
    assert report["success_rate_pct"] == 100.0
