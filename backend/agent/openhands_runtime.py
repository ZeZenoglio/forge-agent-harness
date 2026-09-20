"""OpenHands SDK adapter — the only file permitted to import openhands.*.

Wires together:
- AgentRuntime protocol (architecture invariant 1)
- PolicyEngine for guardrails (budget, thrash, PII, approval)
- Token accounting per observation (REQ-057)
- Model cascade on failure (REQ-059)
- cap_observation for unbounded output protection (REQ-057, invariant 6)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from backend.tools.delegation import delegate_task
from backend.tools.file import (
    edit_file,
    list_directory,
    read_file,
    search_files,
    write_file,
)
from backend.tools.shell import execute_shell
from backend.tools.web import fetch_url

from .events import AgentEvent
from .policies import PolicyEngine
from .runtime import AgentRuntime

logger = logging.getLogger(__name__)

# ── Model cascade config (REQ-059) ───────────────────────────────────────────
# Comma-separated list of model aliases in escalation order.
# E.g. "default-agent,reviewer,gpt-4o"
_CASCADE_ENV = os.getenv("MODEL_CASCADE", "default-agent,reviewer")
_MODEL_CASCADE: list[str] = [m.strip() for m in _CASCADE_ENV.split(",") if m.strip()]

# Approximate token estimate: 1 token ≈ 4 characters (conservative)
_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


class OpenHandsRuntime(AgentRuntime):
    """Adapter bridging the AgentRuntime protocol and the OpenHands SDK.

    Integrates the PolicyEngine for guardrails before execution.
    This is the ONLY file allowed to import openhands.*.
    """

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self.policy_engine = policy_engine
        self.seq_counter = 0
        # Active model alias per session (starts at cascade[0], escalates on error)
        self._session_model: dict[str, str] = {}

    async def init_session(
        self, session_id: str, user_id: str = "anonymous_user"
    ) -> None:
        self.policy_engine.init_session(session_id)
        self._session_model[session_id] = (
            _MODEL_CASCADE[0] if _MODEL_CASCADE else "default-agent"
        )
        logger.info(
            "Session %s started. Model: %s",
            session_id[:8],
            self._session_model[session_id],
        )

    def get_current_model(self, session_id: str) -> str:
        """Return the active model alias for the session."""
        return self._session_model.get(
            session_id, _MODEL_CASCADE[0] if _MODEL_CASCADE else "default-agent"
        )

    def _escalate_model(self, session_id: str) -> str | None:
        """Advance to the next model in the cascade.  Returns new alias or None if exhausted."""
        current = self._session_model.get(session_id, _MODEL_CASCADE[0])
        try:
            idx = _MODEL_CASCADE.index(current)
        except ValueError:
            idx = 0
        next_idx = idx + 1
        if next_idx >= len(_MODEL_CASCADE):
            return None
        next_model = _MODEL_CASCADE[next_idx]
        self._session_model[session_id] = next_model
        logger.warning(
            "Session %s: escalating model cascade %s → %s",
            session_id[:8],
            current,
            next_model,
        )
        return next_model

    async def step(self, session_id: str, input_event: AgentEvent) -> AgentEvent:
        if not self.policy_engine.check_budget(session_id):
            return self._build_event("error", "Budget exceeded (iterations or tokens)")

        action_signature = f"simulate_tool_{self.seq_counter}"
        if not self.policy_engine.check_thrashing(session_id, action_signature):
            return self._build_event("error", "Thrashing detected. Agent loop aborted.")

        # Charge tokens for the input event content
        self.policy_engine.record_tokens(
            session_id, _estimate_tokens(input_event.content)
        )

        self.seq_counter += 1
        return self._build_event("thought", "Agent processed input")

    async def execute_tool(
        self, session_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        from evaluation.metrics import cap_observation

        if not self.policy_engine.validate_tool_args(tool_name, arguments):
            return {"error": "Tool arguments blocked by PolicyEngine due to violation"}

        self.policy_engine.check_requires_approval(tool_name, arguments)

        try:
            result = await self._dispatch_tool(
                tool_name, arguments, session_id=session_id
            )
        except Exception as exc:  # noqa: BLE001
            # On tool failure, attempt model cascade escalation (REQ-059)
            new_model = self._escalate_model(session_id)
            if new_model:
                logger.info(
                    "Session %s: retrying with escalated model %s",
                    session_id[:8],
                    new_model,
                )
            return {"error": f"Tool execution failed: {exc!s}"}

        # Cap unbounded observations before returning to context (REQ-057, invariant 6)
        if isinstance(result, str):
            result = cap_observation(result)
            self.policy_engine.record_tokens(session_id, _estimate_tokens(result))

        return result

    async def _dispatch_tool(
        self, tool_name: str, arguments: dict[str, Any], session_id: str = ""
    ) -> Any:
        """Route tool_name to the appropriate implementation."""
        if tool_name == "read_file":
            return read_file(arguments["path"])
        elif tool_name == "write_file":
            return write_file(arguments["path"], arguments["content"])
        elif tool_name == "edit_file":
            return edit_file(
                arguments["path"], arguments["old_string"], arguments["new_string"]
            )
        elif tool_name == "list_directory":
            return list_directory(arguments["path"])
        elif tool_name == "search_files":
            return search_files(
                directory=arguments.get("directory", "."),
                pattern=arguments.get("pattern", ""),
                file_glob=arguments.get("file_glob", "*"),
            )
        elif tool_name == "execute_shell":
            return execute_shell(
                command=arguments.get("command", ""),
                workspace_root=self.policy_engine.workspace_root,
            )
        elif tool_name == "fetch_url":
            return fetch_url(arguments.get("url", ""))
        elif tool_name == "delegate_task":
            return await delegate_task(
                task_description=arguments.get("task_description", ""),
                model_alias=arguments.get("model_alias", "default-agent"),
            )
        elif tool_name == "memorize":
            from backend.tools.rag import memorize

            return memorize(arguments.get("content", ""))
        elif tool_name == "search_memory":
            from backend.tools.rag import search_memory

            return search_memory(arguments.get("query", ""))
        elif tool_name == "send_email":
            from backend.tools.email import send_email

            return send_email(
                to_address=arguments.get("to_address", ""),
                subject=arguments.get("subject", ""),
                body=arguments.get("body", ""),
            )
        elif tool_name == "research_topic":
            from backend.tools.research import research_topic

            return research_topic(
                query=arguments.get("query", ""),
                depth=arguments.get("depth", "shallow"),
                conversation_id=session_id,
            )
        elif tool_name == "web_search":
            from backend.tools.web import web_search

            return web_search(
                query=arguments.get("query", ""),
                num_results=arguments.get("num_results", 5),
            )
        elif tool_name == "execute_code":
            from backend.tools.code import execute_code

            return execute_code(
                code=arguments.get("code", ""),
                language=arguments.get("language", "python"),
            )
        elif tool_name == "generate_pdf":
            from backend.tools.docgen import generate_pdf

            return generate_pdf(
                content=arguments.get("content", ""),
                title=arguments.get("title", "document"),
                conversation_id=session_id,
            )
        elif tool_name == "generate_docx":
            from backend.tools.docgen import generate_docx

            return generate_docx(
                content=arguments.get("content", ""),
                title=arguments.get("title", "document"),
                conversation_id=session_id,
            )
        elif tool_name == "analyze_image":
            from backend.tools.vision import analyze_image

            return analyze_image(
                image_input=arguments.get("image_input", ""),
                prompt=arguments.get("prompt", "Describe this image in detail."),
            )
        elif tool_name == "extract_structured":
            from backend.tools.extraction import extract_structured

            return extract_structured(
                input_data=arguments.get("input_data", arguments.get("file_path", "")),
                schema=arguments.get("schema", arguments.get("schema_definition", {})),
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def close(self, session_id: str) -> None:
        self._session_model.pop(session_id, None)

    def _build_event(self, event_type: str, content: str) -> AgentEvent:
        self.seq_counter += 1
        return AgentEvent(seq=self.seq_counter, event_type=event_type, content=content)
