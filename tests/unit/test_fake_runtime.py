import pytest

from backend.agent.events import AgentEvent
from backend.agent.fake_runtime import FakeRuntime


@pytest.mark.asyncio
async def test_fake_runtime_step(fake_runtime: FakeRuntime) -> None:
    input_event = AgentEvent(seq=0, event_type="user_input", content="Hello")
    result = await fake_runtime.step("session-1", input_event)
    assert result.seq == 1
    assert result.event_type == "thought"


@pytest.mark.asyncio
async def test_fake_runtime_tool(fake_runtime: FakeRuntime) -> None:
    result = await fake_runtime.execute_tool("session-1", "test_tool", {"arg": "value"})
    assert result["status"] == "success"
    assert result["tool"] == "test_tool"
