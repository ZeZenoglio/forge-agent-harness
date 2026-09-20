"""Unit tests for agent core policies, token accounting, and cascade routing (REQ-057, REQ-059)."""

from __future__ import annotations

import pytest

from backend.agent.openhands_runtime import (
    _MODEL_CASCADE,
    OpenHandsRuntime,
)
from backend.agent.policies import PolicyEngine


@pytest.mark.unit
@pytest.mark.smoke
def test_policy_engine_token_accounting() -> None:
    engine = PolicyEngine(max_tokens=1000)
    session_id = "test_session_tokens"
    engine.init_session(session_id)

    # Initial budget ok
    assert engine.check_budget(session_id) is True

    # Record tokens
    engine.record_tokens(session_id, 400)
    assert engine.token_counts[session_id] == 400
    assert engine.check_budget(session_id) is True

    # Record more tokens exceeding ceiling
    engine.record_tokens(session_id, 700)
    assert engine.token_counts[session_id] == 1100
    assert engine.check_budget(session_id) is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_cascade_runtime() -> None:
    engine = PolicyEngine()
    runtime = OpenHandsRuntime(policy_engine=engine)
    session_id = "test_session_cascade"

    await runtime.init_session(session_id)
    assert runtime.get_current_model(session_id) == "default-agent"
    assert "default-agent" in _MODEL_CASCADE

    # Escalate model
    next_model = runtime._escalate_model(session_id)
    assert next_model is not None
    assert runtime.get_current_model(session_id) == next_model
