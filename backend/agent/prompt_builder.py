"""Prompt builder enforcing the canonical assembly order (REQ-058).

The order is fixed and must never be changed:

    system_prompt → tool_definitions → history → dynamic_state → current_turn

Anything that changes between turns (dynamic state, current input) sits at
the end so prefix stability is maximised and the KV cache is not invalidated
on every iteration.
"""

from __future__ import annotations

from typing import Any

# ── Types ─────────────────────────────────────────────────────────────────────

Message = dict[str, str]  # {"role": "...", "content": "..."}


# ── Prompt builder ────────────────────────────────────────────────────────────


class PromptBuilder:
    """Assemble an ordered message list for the model context.

    Usage::

        builder = PromptBuilder(system_prompt="You are a helpful agent.")
        builder.add_tool_definitions(tools_schema)
        builder.add_history(past_messages)
        builder.add_dynamic_state(current_workspace_summary)
        messages = builder.build(current_turn="Read /tmp/hello.txt")
    """

    def __init__(self, system_prompt: str) -> None:
        self._system_prompt = system_prompt
        self._tool_definitions: str = ""
        self._history: list[Message] = []
        self._dynamic_state: str = ""

    def add_tool_definitions(self, tools: list[dict[str, Any]]) -> PromptBuilder:
        """Serialise tool schemas into a deterministic string (sorted by name).

        Tools are sorted alphabetically so the prefix is stable across
        calls even when new tools are registered in a different order.
        """
        import json

        sorted_tools = sorted(tools, key=lambda t: t.get("name", ""))
        self._tool_definitions = json.dumps(sorted_tools, indent=2)
        return self

    def add_history(self, messages: list[Message]) -> PromptBuilder:
        """Add prior conversation turns.  Call once per build cycle."""
        self._history = list(messages)
        return self

    def add_dynamic_state(self, state: str) -> PromptBuilder:
        """Add mutable per-turn context (workspace summary, retrieved docs, etc.).

        This is deliberately placed near the end of the prompt so it does
        not pollute the stable prefix section.
        """
        self._dynamic_state = state
        return self

    def build(self, current_turn: str) -> list[Message]:
        """Return the ordered message list for the model API call.

        Order: system → tools (in system) → history → dynamic state → current turn.
        """
        # ── 1. System prompt (stable prefix) ─────────────────────────────
        system_content = self._system_prompt

        # ── 2. Tool definitions (deterministic, sorted — still stable prefix)
        if self._tool_definitions:
            system_content += (
                "\n\n## Available Tools\n\n"
                "Use only the tools listed below. Never invent tool names.\n\n"
                f"```json\n{self._tool_definitions}\n```"
            )

        messages: list[Message] = [{"role": "system", "content": system_content}]

        # ── 3. History (prior turns) ──────────────────────────────────────
        messages.extend(self._history)

        # ── 4. Dynamic state (per-turn, mutable — near end) ──────────────
        if self._dynamic_state:
            messages.append(
                {
                    "role": "system",
                    "content": f"## Current Workspace State\n\n{self._dynamic_state}",
                }
            )

        # ── 5. Current turn (most volatile — always last) ─────────────────
        messages.append({"role": "user", "content": current_turn})

        return messages
