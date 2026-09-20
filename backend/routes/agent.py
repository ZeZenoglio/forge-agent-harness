import asyncio
import uuid

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

# Global dict for phase 2 local dev to hold pending approval events
pending_approvals: dict[str, asyncio.Event] = {}

class RunRequest(BaseModel):
    task: str

async def agent_task(session_id: str, task: str, user_id: str = "anonymous_user") -> None:
    """Background task simulating the agent run loop emitting to Redis."""
    policy_engine = PolicyEngine(workspace_root="/tmp/forge_workspace")
    runtime = OpenHandsRuntime(policy_engine=policy_engine)
    
    await runtime.init_session(session_id, user_id=user_id)
    
    # Emit start event
    start_event = AgentEvent(seq=0, event_type="start", content=f"Starting task: {task}")
    await stream_service.emit_event(session_id, start_event.model_dump())
    
    # Step 1
    event_1 = await runtime.step(session_id, start_event)
    await stream_service.emit_event(session_id, event_1.model_dump())
    
    # Step 2: Simulate Tool Execution
    tool_name = "execute_shell"
    tool_args = {"command": "sudo echo 'Hello Forge'"} # Changed to trigger approval
    
    try:
        tool_res = await runtime.execute_tool(session_id, tool_name, tool_args)
    except ApprovalRequiredException as e:
        # Emit approval requested event
        approval_event = AgentEvent(seq=event_1.seq + 1, event_type="approval_requested", content=str(e))
        await stream_service.emit_event(session_id, approval_event.model_dump())
        
        # Pause and wait for approval
        approval_wait_event = asyncio.Event()
        pending_approvals[session_id] = approval_wait_event
        try:
            # Wait up to 5 minutes (REQ-050)
            await asyncio.wait_for(approval_wait_event.wait(), timeout=300)
            tool_res = "Approval granted. Command executed."
        except TimeoutError:
            tool_res = "Approval denied due to timeout."
        finally:
            pending_approvals.pop(session_id, None)

    tool_event = AgentEvent(seq=event_1.seq + 2, event_type="tool_result", content=str(tool_res))
    await stream_service.emit_event(session_id, tool_event.model_dump())
    
    # Step 3: Finish
    finish_event = AgentEvent(seq=tool_event.seq + 1, event_type="finish", content="Task completed")
    await stream_service.emit_event(session_id, finish_event.model_dump())


@router.post("/run")
async def run_agent(req: RunRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)) -> dict[str, str]:
    session_id = str(uuid.uuid4())
    # In full production, this dispatches to Celery. For Phase 2, BackgroundTasks suffices
    # to demonstrate the streaming decoupled from the request.
    background_tasks.add_task(agent_task, session_id, req.task, user_id)
    return {"session_id": session_id}

@router.get("/stream/{session_id}")
async def stream_agent(session_id: str) -> StreamingResponse:
    return StreamingResponse(
        stream_service.subscribe(session_id),
        media_type="text/event-stream"
    )

@router.post("/tasks/{session_id}/approve")
async def approve_task(session_id: str, user_id: str = Depends(get_current_user)) -> dict[str, str]:
    if session_id in pending_approvals:
        pending_approvals[session_id].set()
        return {"status": "approved"}
    raise HTTPException(status_code=404, detail="No pending approval for this session")
