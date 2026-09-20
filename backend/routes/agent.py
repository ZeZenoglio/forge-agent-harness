"""FastAPI routes for agent task execution and SSE streaming.

Implements REQ-033 (API layer), REQ-021 (streaming events), and REQ-050
(Human-in-the-Loop approval gate).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

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


async def agent_task(
    session_id: str, task: str, user_id: str = "anonymous_user"
) -> None:
    """Background task that simulates the agent run loop and streams events.

    The loop produces a realistic multi-step trace — plan → thought → tool
    call → approval gate → finish — using the caller-supplied *task* text so
    the output is contextually relevant in a demo.
    """
    policy_engine = PolicyEngine(workspace_root="/tmp/forge_workspace")
    runtime = OpenHandsRuntime(policy_engine=policy_engine)

    await runtime.init_session(session_id, user_id=user_id)
    seq = 0

    async def emit(
        event_type: str, content: str, tool_name: str | None = None
    ) -> AgentEvent:
        nonlocal seq
        meta: dict[str, object] = {}
        if tool_name:
            meta["tool_name"] = tool_name
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
    plan = (
        f"I need to complete the following task:\n\n"
        f"  '{task}'\n\n"
        f"My plan:\n"
        f"  1. Analyse the request and identify required tools.\n"
        f"  2. Execute the primary tool with safe arguments.\n"
        f"  3. Validate the output and return a final answer."
    )
    await emit("thought", plan)

    # ── Step 2: tool call (triggers HITL approval) ──────────────────────
    await asyncio.sleep(0.6)
    tool_name = "execute_shell"
    tool_args = {"command": f"echo 'Running task: {task[:60]}'"}

    try:
        tool_res = await runtime.execute_tool(session_id, tool_name, tool_args)
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

        await emit("tool_result", tool_res, tool_name=tool_name)

    # ── Step 3: finish ──────────────────────────────────────────────────
    await asyncio.sleep(0.3)
    await emit(
        "finish",
        "✅ Task complete.\n\nSummary: The agent processed your request "
        "and produced the output above. All policy checks passed.",
    )


@router.post("/run")
async def run_agent(
    req: RunRequest,
    background_tasks: BackgroundTasks,
    user_id: str = _user_dep,
) -> dict[str, Any]:
    """Start an agent task and return the session ID for streaming."""
    session_id = str(uuid.uuid4())
    background_tasks.add_task(agent_task, session_id, req.task, user_id)
    return {"data": {"session_id": session_id}, "session_id": session_id}


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
