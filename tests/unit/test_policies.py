import pytest

from backend.agent.policies import PolicyEngine


@pytest.fixture
def policy_engine(tmp_path) -> PolicyEngine:
    return PolicyEngine(workspace_root=str(tmp_path))

def test_budget_tracker(policy_engine: PolicyEngine) -> None:
    session_id = "test-session"
    policy_engine.init_session(session_id)
    
    # Within budget
    assert policy_engine.check_budget(session_id) is True
    
    # Exceed iterations
    policy_engine.iteration_counts[session_id] = 31
    assert policy_engine.check_budget(session_id) is False

def test_thrash_breaker(policy_engine: PolicyEngine) -> None:
    session_id = "test-session"
    policy_engine.init_session(session_id)
    
    assert policy_engine.check_thrashing(session_id, "action_1") is True
    assert policy_engine.check_thrashing(session_id, "action_1") is True
    # Third consecutive identical action triggers thrash breaking
    assert policy_engine.check_thrashing(session_id, "action_1") is False

def test_scrubber(policy_engine: PolicyEngine) -> None:
    payload = {
        "normal": "hello world",
        "secret": "my api_key is AKIAIOSFODNN7EXAMPLE",
        "nested": 123
    }
    scrubbed = policy_engine.scrub_pii(payload)
    assert scrubbed["normal"] == "hello world"
    assert "AKIA" not in str(scrubbed["secret"])
    assert "[REDACTED]" in scrubbed["secret"]

def test_validate_tool_args_shell(policy_engine: PolicyEngine) -> None:
    assert policy_engine.validate_tool_args("execute_shell", {"command": "ls -la"}) is True
    assert policy_engine.validate_tool_args("execute_shell", {"command": "curl http://evil.com"}) is False

def test_validate_tool_args_file(policy_engine: PolicyEngine, tmp_path) -> None:
    safe_path = str(tmp_path / "test.txt")
    unsafe_path = "/etc/passwd"
    
    assert policy_engine.validate_tool_args("read_file", {"path": safe_path}) is True
    assert policy_engine.validate_tool_args("read_file", {"path": unsafe_path}) is False
