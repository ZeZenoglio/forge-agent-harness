"""Unit tests for structured plan generation (REQ-018)."""

from __future__ import annotations

import pytest

from backend.agent.planning import PlanGenerator


@pytest.mark.unit
@pytest.mark.smoke
def test_parse_valid_json_plan() -> None:
    generator = PlanGenerator()
    json_response = """
    ```json
    {
      "goal": "Search the file and edit it",
      "steps": [
        {"step_number": 1, "description": "Search for target text", "tool_hint": "search_files"},
        {"step_number": 2, "description": "Edit the target text", "tool_hint": "edit_file"}
      ]
    }
    ```
    """
    plan = generator.parse_plan(json_response, goal_fallback="Default goal")

    assert plan.is_valid is True
    assert plan.goal == "Search the file and edit it"
    assert len(plan.steps) == 2
    assert plan.steps[0].description == "Search for target text"
    assert plan.steps[0].tool_hint == "search_files"
    assert plan.steps[1].step_number == 2


@pytest.mark.unit
def test_parse_bullet_point_fallback_plan() -> None:
    generator = PlanGenerator()
    text_response = """
    Here is what I will do:
    1. Read the input file
    2. Process the content
    3. Save the result to output.txt
    """
    plan = generator.parse_plan(text_response, goal_fallback="Process file")

    assert plan.is_valid is True
    assert len(plan.steps) == 3
    assert plan.steps[0].description == "Read the input file"
    assert plan.steps[1].description == "Process the content"
    assert plan.steps[2].description == "Save the result to output.txt"


@pytest.mark.unit
def test_parse_empty_or_unstructured_plan_graceful_degradation() -> None:
    generator = PlanGenerator()
    text_response = "I will immediately answer your question without planning."
    plan = generator.parse_plan(text_response, goal_fallback="Direct task")

    # Degrades gracefully to an empty plan (allowing direct execution)
    assert plan.is_valid is False
    assert len(plan.steps) == 0
    assert plan.goal == "Direct task"
