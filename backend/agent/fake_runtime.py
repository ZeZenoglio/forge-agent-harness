from typing import Any

from .events import AgentEvent
from .runtime import AgentRuntime


class FakeRuntime(AgentRuntime):
    """
    Mock runtime used strictly for fast unit testing and evaluation (Track A).
    Never makes network calls or invokes the actual LLM.
    """

    def __init__(self) -> None:
        self.seq_counter = 0

    async def init_session(
        self, session_id: str, user_id: str = "anonymous_user"
    ) -> None:
        self.seq_counter = 0

    async def step(self, session_id: str, input_event: AgentEvent) -> AgentEvent:
        self.seq_counter += 1
        return AgentEvent(
            seq=self.seq_counter,
            event_type="thought",
            content="Fake thought for testing.",
        )

    async def execute_tool(
        self, session_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        return {"status": "success", "tool": tool_name, "args": arguments}

    async def close(self, session_id: str) -> None:
        pass
