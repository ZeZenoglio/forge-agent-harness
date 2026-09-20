"""Trajectory evaluator for agentic runs (REQ-063).

Parses a sequence of ``AgentEvent`` dicts produced by the agent runtime and
computes structural quality metrics that do not require an LLM call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Known tool names the agent is permitted to call.  A call to anything outside
# this set is flagged as a schema violation.
_KNOWN_TOOLS = frozenset(
    {
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "search_files",
        "execute_shell",
        "fetch_url",
        "delegate_task",
        "memorize",
        "search_memory",
        "send_email",
    }
)


@dataclass
class TrajectoryReport:
    """Aggregated quality report for a single agent trajectory."""

    # Total number of events in the trace
    total_events: int = 0
    # Did the trajectory end with a 'finish' event?
    completed: bool = False
    # Did the trajectory encounter an 'error' event?
    errored: bool = False
    # Number of tool calls made
    tool_calls: int = 0
    # Number of tool calls blocked (policy violation)
    blocked_calls: int = 0
    # Number of tool calls to unknown / hallucinated tool names
    schema_violations: int = 0
    # Number of HITL approval events triggered
    approval_gates: int = 0
    # Was human approval eventually granted?
    approval_granted: bool = False
    # Event types observed (in order)
    event_sequence: list[str] = field(default_factory=list)

    # ── Derived metrics ────────────────────────────────────────────────
    @property
    def plan_adherence(self) -> float:
        """Fraction of tool calls that passed policy checks.

        1.0 = all calls were valid.  0.0 = all calls were blocked.
        Returns 1.0 if no tool calls were made (vacuously true).
        """
        total = self.tool_calls + self.blocked_calls
        if total == 0:
            return 1.0
        return self.tool_calls / total

    @property
    def schema_validity(self) -> float:
        """Fraction of tool calls targeting known tool names.

        1.0 = no hallucinated tool names.
        """
        total = self.tool_calls + self.schema_violations
        if total == 0:
            return 1.0
        return self.tool_calls / total

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_events": self.total_events,
            "completed": self.completed,
            "errored": self.errored,
            "tool_calls": self.tool_calls,
            "blocked_calls": self.blocked_calls,
            "schema_violations": self.schema_violations,
            "approval_gates": self.approval_gates,
            "approval_granted": self.approval_granted,
            "plan_adherence": self.plan_adherence,
            "schema_validity": self.schema_validity,
            "event_sequence": self.event_sequence,
        }


class TrajectoryEvaluator:
    """Parse an agent event trace and produce a :class:`TrajectoryReport`.

    Usage::

        evaluator = TrajectoryEvaluator()
        events = [event.model_dump() for event in session_events]
        report = evaluator.evaluate(events)
        print(report.as_dict())
    """

    def evaluate(self, events: list[dict[str, Any]]) -> TrajectoryReport:
        """Evaluate a list of raw event dicts and return a :class:`TrajectoryReport`."""
        report = TrajectoryReport()
        report.total_events = len(events)

        for event in events:
            event_type: str = event.get("event_type", event.get("type", "unknown"))
            report.event_sequence.append(event_type)

            if event_type == "finish":
                report.completed = True

            elif event_type == "error":
                content = event.get("content", "")
                if "blocked by PolicyEngine" in content:
                    report.blocked_calls += 1
                else:
                    report.errored = True

            elif event_type == "tool_call":
                tool_name = (event.get("metadata") or {}).get("tool_name", "")
                if tool_name and tool_name not in _KNOWN_TOOLS:
                    report.schema_violations += 1
                else:
                    report.tool_calls += 1

            elif event_type == "tool_result":
                # Successful tool execution (already counted at tool_call time)
                pass

            elif event_type == "approval_requested":
                report.approval_gates += 1

            elif event_type in ("start", "thought"):
                pass  # Informational — no metrics

        # Check if approval was eventually followed by a result
        if report.approval_gates > 0:
            seq = report.event_sequence
            for i, t in enumerate(seq):
                if t == "approval_requested" and any(
                    s == "tool_result" for s in seq[i + 1 :]
                ):
                    report.approval_granted = True
                    break

        return report
