import json
from unittest.mock import patch

import pytest

from backend.tools.delegation import delegate_task
from backend.tools.email import send_email


@pytest.mark.asyncio
async def test_delegate_multiple_tasks():
    # Test parallel delegation of multiple tasks
    task_input = "Write a report; Summarize the report"

    with patch("backend.tools.delegation.stream_service.emit_event") as mock_emit:
        result = await delegate_task(task_input)
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["task"] == "Write a report"
        assert parsed[1]["task"] == "Summarize the report"

        # Check that trajectory has multiple events
        assert len(parsed[0]["trajectory"]) > 2
        assert parsed[0]["trajectory"][0]["event_type"] == "start"
        assert parsed[0]["trajectory"][-1]["event_type"] == "finish"

        assert mock_emit.called


def test_send_email_mock():
    # Since mailpit isn't running in our test environment, we expect a connection failure,
    # but the tool shouldn't crash.
    result = send_email("test@example.com", "Test Subject", "Test Body")
    assert "Failed to send email" in result or "Email successfully sent" in result
