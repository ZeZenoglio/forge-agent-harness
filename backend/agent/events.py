from typing import Any

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    """
    Standard event envelope for the agent system.
    Every event carries a monotonic seq for deterministic replay and streaming.
    """

    seq: int
    event_type: str = Field(
        description="e.g. 'thought', 'tool_call', 'tool_result', 'final_answer'"
    )
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
