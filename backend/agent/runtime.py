from typing import Any, Protocol

from .events import AgentEvent


class AgentRuntime(Protocol):
    """
    Protocol defining the core interface for any agent harness.
    The rest of the system depends ONLY on this protocol, never directly on OpenHands.
    """

    async def init_session(self, session_id: str) -> None:
        """Initialize a new agent session."""
        ...

    async def step(self, session_id: str, input_event: AgentEvent) -> AgentEvent:
        """Execute a single step/turn of the agent loop."""
        ...

    async def execute_tool(
        self, session_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Execute a specific tool within the agent's sandbox."""
        ...

    async def close(self, session_id: str) -> None:
        """Clean up the agent session."""
        ...
