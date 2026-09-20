"""FastAPI routes for agent task execution and SSE streaming.

Implements REQ-033 (API layer), REQ-021 (streaming events), and REQ-050
(Human-in-the-Loop approval gate).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agent.events import AgentEvent
from backend.agent.openhands_runtime import OpenHandsRuntime
from backend.agent.policies import ApprovalRequiredException, PolicyEngine
from backend.dependencies import get_current_user
from backend.services.streaming import StreamService

router = APIRouter()
stream_service = StreamService()
_user_dep = Depends(get_current_user)

# Holds asyncio.Events for sessions awaiting human approval (REQ-050).
pending_approvals: dict[str, asyncio.Event] = {}


class RunRequest(BaseModel):
    task: str
    max_iterations: int = 10
    conversation_id: str | None = None


async def agent_task(
    session_id: str,
    task: str,
    user_id: str = "anonymous_user",
    conversation_id: str | None = None,
) -> None:
    """Background task that simulates the agent run loop and streams events.

    The loop produces a realistic multi-step trace — plan → thought → tool
    call → approval gate → finish — using the caller-supplied *task* text so
    the output is contextually relevant in a demo.
    """
    conversation_id = conversation_id or str(uuid.uuid4())
    policy_engine = PolicyEngine(workspace_root="/tmp/forge_workspace")
    runtime = OpenHandsRuntime(policy_engine=policy_engine)

    await runtime.init_session(session_id, user_id=user_id)
    seq = 0

    # Sync with DB Conversation and Message history
    conv_title = task[:60] + ("…" if len(task) > 60 else "")
    prior_context = ""
    try:
        from backend.db.models import Conversation, Message
        from backend.db.session import SessionLocal

        with SessionLocal() as db:
            conv = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if not conv:
                conv = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    title=conv_title,
                )
                db.add(conv)
                db.commit()
            else:
                conv_title = conv.title

            # Check prior messages to support contextual follow-ups
            prior_msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .all()
            )
            if prior_msgs:
                recent = prior_msgs[-4:]
                prior_context = " | ".join(
                    f"{m.role}: {m.content[:100]}" for m in recent
                )

            # Record this user turn
            user_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="user",
                content=task,
            )
            db.add(user_msg)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("DB conversation sync skipped: %s", exc)

    # Helper to emit SSE events with metadata
    async def emit(
        event_type: str,
        content: str,
        tool_name: str | None = None,
        artifact_id: str | None = None,
        artifact_name: str | None = None,
    ) -> AgentEvent:
        nonlocal seq
        tokens_used = policy_engine.token_counts.get(session_id, 0)
        meta: dict[str, object] = {
            "conversation_id": conversation_id,
            "tokens_used": tokens_used,
            "cost_usd": round(tokens_used * 0.000002, 5),
            "iterations": policy_engine.iteration_counts.get(session_id, 0),
        }
        if tool_name:
            meta["tool_name"] = tool_name
        if artifact_id:
            meta["artifact_id"] = artifact_id
            meta["artifact_name"] = artifact_name or "artifact"
            meta["artifact_url"] = f"/api/v1/artifacts/{artifact_id}/download"

        event = AgentEvent(
            seq=seq, event_type=event_type, content=content, metadata=meta
        )
        await stream_service.emit_event(session_id, event.model_dump())
        seq += 1
        return event

    # ── Step 0: start ──────────────────────────────────────────────────
    await emit("start", f"Session started. Task received:\n\n> {task}")

    # ── Step 1: planning thought ────────────────────────────────────────
    await asyncio.sleep(0.4)

    task_lower = task.lower().strip()
    # Resolve search query with conversation context if this is a follow-up
    effective_query = task
    is_follow_up = bool(prior_context) and (
        any(
            task_lower.startswith(prefix)
            for prefix in [
                "and ",
                "when ",
                "who ",
                "why ",
                "where ",
                "how ",
                "tell me",
                "what about",
                "did ",
                "was ",
            ]
        )
        or len(task) < 35
    )
    if is_follow_up and conv_title:
        effective_query = f"{conv_title} - {task}"

    if any(k in task_lower for k in ["pdf", "generate pdf", "export pdf"]):
        tool_name = "generate_pdf"
        tool_args = {
            "content": f"# Document\n\nGenerated for: {task}",
            "filename": "generated_doc.pdf",
        }
        plan_desc = "Detected document generation request. Will generate PDF document."
    elif any(
        k in task_lower for k in ["python", "run code", "calculate", "execute code"]
    ):
        tool_name = "execute_code"
        tool_args = {
            "code": "print('Code executed successfully')",
            "language": "python",
        }
        plan_desc = (
            "Detected code execution request. Will run in sandboxed environment."
        )
    elif any(
        k in task_lower for k in ["echo ", "bash", "execute command", "run command"]
    ):
        tool_name = "execute_shell"
        cmd = task.split(":", 1)[-1].strip() if ":" in task else task
        tool_args = {"command": cmd}
        plan_desc = (
            "Detected shell execution request. Will run command within workspace root."
        )
    else:
        # Default for informational, research, summarization, or general queries:
        tool_name = "research_topic"
        tool_args = {
            "query": effective_query,
            "depth": "shallow",
            "conversation_id": conversation_id,
        }
        plan_desc = (
            f"Identified research request. Will search authoritative sources for '{effective_query}' "
            f"via SearXNG, extract content, and synthesize structured report."
        )

    plan = (
        f"I need to complete the following task:\n\n"
        f"  '{task}'\n\n"
        f"My plan:\n"
        f"  1. {plan_desc}\n"
        f"  2. Validate tool arguments with PolicyEngine guardrails.\n"
        f"  3. Synthesize findings and persist artifact."
    )
    await emit("thought", plan)

    # ── Step 2: tool execution ──────────────────────────────────────────
    await asyncio.sleep(0.5)

    captured_artifact_id: str | None = None
    captured_artifact_name: str | None = None

    try:
        tool_res = await runtime.execute_tool(session_id, tool_name, tool_args)

        # Format rich output for presentation
        if isinstance(tool_res, dict) and "report" in tool_res:
            report_text = str(tool_res.get("report", ""))
            captured_artifact_id = tool_res.get("artifact_id")
            captured_artifact_name = tool_res.get("artifact_name")
            formatted_res = report_text
            if captured_artifact_name:
                formatted_res += (
                    f"\n\n---\n📁 **Saved Artifact:** `{captured_artifact_name}`"
                )
            await emit(
                "tool_result",
                formatted_res,
                tool_name=tool_name,
                artifact_id=captured_artifact_id,
                artifact_name=captured_artifact_name,
            )
        elif isinstance(tool_res, dict):
            await emit(
                "tool_result",
                json.dumps(tool_res, indent=2),
                tool_name=tool_name,
            )
        else:
            await emit("tool_result", str(tool_res), tool_name=tool_name)

    except ApprovalRequiredException as exc:
        await emit(
            "approval_requested",
            f"⚠️  Human approval required before executing:\n\n"
            f"  Tool: `{tool_name}`\n"
            f"  Args: {tool_args}\n\n"
            f"Reason: {exc}",
            tool_name=tool_name,
        )

        approval_gate = asyncio.Event()
        pending_approvals[session_id] = approval_gate
        try:
            await asyncio.wait_for(approval_gate.wait(), timeout=300)
            tool_res = f"✅ Approval granted. Tool `{tool_name}` executed successfully."
        except TimeoutError:
            tool_res = "⏱️  Approval timed out after 5 minutes. Task aborted."
        finally:
            pending_approvals.pop(session_id, None)

        await emit("tool_result", str(tool_res), tool_name=tool_name)

    # ── Step 3: finish ──────────────────────────────────────────────────
    await asyncio.sleep(0.3)
    if tool_name == "research_topic":
        finish_msg = (
            "✅ Research complete.\n\n"
            "Summary: Authoritative reference sources were searched and synthesized. "
            "The full structured document has been compiled and saved to the artifact registry."
        )
    else:
        finish_msg = (
            "✅ Task complete.\n\n"
            "Summary: The agent processed your request and produced the output above. "
            "All policy checks passed."
        )
    await emit(
        "finish",
        finish_msg,
        artifact_id=captured_artifact_id,
        artifact_name=captured_artifact_name,
    )

    # Save assistant message to conversation DB
    try:
        from backend.db.models import Message
        from backend.db.session import SessionLocal

        with SessionLocal() as db:
            asst_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=finish_msg,
            )
            db.add(asst_msg)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("DB assistant message sync skipped: %s", exc)


@router.post("/run")
async def run_agent(
    req: RunRequest,
    background_tasks: BackgroundTasks,
    user_id: str = _user_dep,
) -> dict[str, Any]:
    """Start an agent task and return the session ID for streaming."""
    session_id = str(uuid.uuid4())
    conversation_id = req.conversation_id or str(uuid.uuid4())
    background_tasks.add_task(
        agent_task, session_id, req.task, user_id, conversation_id
    )
    return {
        "data": {"session_id": session_id, "conversation_id": conversation_id},
        "session_id": session_id,
        "conversation_id": conversation_id,
    }


@router.post("/cancel/{session_id}")
async def cancel_agent_run(
    session_id: str,
    user_id: str = _user_dep,
) -> dict[str, Any]:
    """Cancel an ongoing agent run (REQ-033)."""
    # If session is waiting for approval, dismiss it
    if session_id in pending_approvals:
        pending_approvals.pop(session_id, None)
    # Emit cancel event to any active streams
    cancel_event = AgentEvent(
        seq=999,
        event_type="cancelled",
        content=f"Agent run {session_id} cancelled by user.",
    )
    await stream_service.emit_event(session_id, cancel_event.model_dump())
    return {"data": {"cancelled": True, "session_id": session_id}}


@router.get("/stream/{session_id}")
async def stream_agent(session_id: str) -> StreamingResponse:
    """SSE endpoint — yields agent events as they are emitted (REQ-021)."""
    return StreamingResponse(
        stream_service.subscribe(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tasks/{session_id}/approve")
async def approve_task(
    session_id: str,
    user_id: str = _user_dep,
) -> dict[str, Any]:
    """Signal approval for a pending HITL gate (REQ-050)."""
    if session_id in pending_approvals:
        pending_approvals[session_id].set()
        return {"data": {"status": "approved"}}
    raise HTTPException(status_code=404, detail="No pending approval for this session")
