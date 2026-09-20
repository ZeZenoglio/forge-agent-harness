"""Structured planning module for agent execution (REQ-018).

The agent generates an explicit plan (list of steps) before executing any tools.
The plan is emitted as a structured event and stored in the execution trace.
If plan generation cannot produce a valid structure, it degrades gracefully
to direct execution.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """A single atomic step in an execution plan."""

    step_number: int
    description: str
    tool_hint: str | None = None
    completed: bool = False


@dataclass
class ExecutionPlan:
    """A structured plan of action created before tool execution."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    raw_response: str = ""

    @property
    def is_valid(self) -> bool:
        return len(self.steps) > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "tool_hint": s.tool_hint,
                    "completed": s.completed,
                }
                for s in self.steps
            ],
            "total_steps": len(self.steps),
        }


class PlanGenerator:
    """Generates structured execution plans from user queries."""

    PLAN_PROMPT_TEMPLATE = (
        "You are an expert planning assistant. Given the following user goal, "
        "break it down into a concise, ordered list of 2 to 6 actionable steps.\n\n"
        "Return ONLY a JSON object with this format:\n"
        "{\n"
        '  "goal": "summary of user goal",\n'
        '  "steps": [\n'
        '    {"step_number": 1, "description": "step description", "tool_hint": "optional_tool_name"}\n'
        "  ]\n"
        "}\n\n"
        "USER GOAL:\n{query}"
    )

    def parse_plan(self, text: str, goal_fallback: str = "") -> ExecutionPlan:
        """Parse structured plan from LLM output with fallback heuristics."""
        text_clean = text.strip()
        # Try finding JSON block in markdown fences or raw text
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text_clean, re.DOTALL)
        candidate = json_match.group(1) if json_match else text_clean

        try:
            data = json.loads(candidate)
            if (
                isinstance(data, dict)
                and "steps" in data
                and isinstance(data["steps"], list)
            ):
                steps = []
                for i, s in enumerate(data["steps"], 1):
                    desc = (
                        s.get("description", str(s)) if isinstance(s, dict) else str(s)
                    )
                    tool_hint = s.get("tool_hint") if isinstance(s, dict) else None
                    steps.append(
                        PlanStep(
                            step_number=s.get("step_number", i)
                            if isinstance(s, dict)
                            else i,
                            description=desc,
                            tool_hint=tool_hint,
                        )
                    )
                return ExecutionPlan(
                    goal=data.get("goal", goal_fallback),
                    steps=steps,
                    raw_response=text,
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Structured plan JSON parsing failed (%s), attempting line heuristic",
                exc,
            )

        # Fallback: line-by-line numbered bullet parser
        steps = []
        for line in text_clean.splitlines():
            line_s = line.strip()
            num_match = re.match(r"^(?:(\d+)[\.\)]\s*|[-*]\s+)(.+)$", line_s)
            if num_match:
                desc = num_match.group(2).strip()
                if desc:
                    steps.append(
                        PlanStep(
                            step_number=len(steps) + 1,
                            description=desc,
                        )
                    )

        if steps:
            return ExecutionPlan(goal=goal_fallback, steps=steps, raw_response=text)

        # Graceful degradation to empty plan (triggering direct execution)
        return ExecutionPlan(goal=goal_fallback, steps=[], raw_response=text)
