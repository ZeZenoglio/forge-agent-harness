from unittest.mock import AsyncMock, patch

import pytest

from backend.tools.delegation import delegate_task


@pytest.mark.asyncio
@patch("backend.tools.delegation.stream_service.emit_event", new_callable=AsyncMock)
async def test_delegate_task(mock_emit):
    # Calling the delegation tool should return a simulated successful response
    result = await delegate_task("test delegation", "default-agent")
    assert "successfully" in result
    assert "test delegation" in result
