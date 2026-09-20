"""Unit tests for PromptBuilder enforcing canonical assembly order (REQ-058)."""

from __future__ import annotations

import pytest

from backend.agent.prompt_builder import PromptBuilder


@pytest.mark.unit
@pytest.mark.smoke
def test_prompt_builder_assembly_order() -> None:
    system_prompt = "You are an autonomous AI coding assistant."
    tools = [
        {"name": "write_file", "description": "Write a file"},
        {"name": "execute_shell", "description": "Run shell cmd"},
        {"name": "read_file", "description": "Read a file"},
    ]
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    dynamic_state = "current_file: main.py"
    current_turn = "Please read main.py"

    builder = PromptBuilder(system_prompt=system_prompt)
    builder.add_tool_definitions(tools)
    builder.add_history(history)
    builder.add_dynamic_state(dynamic_state)
    messages = builder.build(current_turn=current_turn)

    # Order must be: system (with sorted tools) → history → dynamic_state → current_turn
    assert len(messages) == 5
    assert messages[0]["role"] == "system"
    assert system_prompt in messages[0]["content"]

    # Tool definitions must be deterministically sorted by name in system prompt
    system_content = messages[0]["content"]
    pos_exec = system_content.find("execute_shell")
    pos_read = system_content.find("read_file")
    pos_write = system_content.find("write_file")
    assert pos_exec < pos_read < pos_write

    # History
    assert messages[1] == history[0]
    assert messages[2] == history[1]

    # Dynamic state
    assert messages[3]["role"] == "system"
    assert "current_file: main.py" in messages[3]["content"]

    # Current turn
    assert messages[4]["role"] == "user"
    assert messages[4]["content"] == current_turn


@pytest.mark.unit
def test_prompt_builder_prefix_stability() -> None:
    tools = [{"name": "read_file", "description": "Read"}]
    history = [{"role": "user", "content": "Task 1"}]

    builder1 = PromptBuilder(system_prompt="Base System Prompt")
    builder1.add_tool_definitions(tools).add_history(history).add_dynamic_state(
        "state1"
    )
    msgs1 = builder1.build("Turn 1")

    builder2 = PromptBuilder(system_prompt="Base System Prompt")
    builder2.add_tool_definitions(tools).add_history(history).add_dynamic_state(
        "state2"
    )
    msgs2 = builder2.build("Turn 2")

    # The prefix (system message with tool schemas + history) must be byte-for-byte identical
    assert msgs1[0] == msgs2[0]
    assert msgs1[1] == msgs2[1]
