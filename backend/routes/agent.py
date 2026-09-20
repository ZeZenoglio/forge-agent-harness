import uuid

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agent.events import AgentEvent
from backend.agent.openhands_runtime import OpenHandsRuntime
from backend.agent.policies import PolicyEngine
from backend.services.streaming import StreamService

router = APIRouter()
stream_service = StreamService()

class RunRequest(BaseModel):
    task: str

async def agent_task(session_id: str, task: str) -> None:
    """Background task simulating the agent run loop emitting to Redis."""
    policy_engine = PolicyEngine(workspace_root="/tmp/forge_workspace")
    runtime = OpenHandsRuntime(policy_engine=policy_engine)
    
    await runtime.init_session(session_id)
    
    # Emit start event
    start_event = AgentEvent(seq=0, event_type="start", content=f"Starting task: {task}")
    await stream_service.emit_event(session_id, start_event.model_dump())
    
    # Step 1
    event_1 = await runtime.step(session_id, start_event)
    await stream_service.emit_event(session_id, event_1.model_dump())
    
    # Step 2: Simulate Tool Execution
    tool_res = await runtime.execute_tool(session_id, "execute_shell", {"command": "echo 'Hello Forge'"})
    tool_event = AgentEvent(seq=event_1.seq + 1, event_type="tool_result", content=str(tool_res))
    await stream_service.emit_event(session_id, tool_event.model_dump())
    
    # Step 3: Finish
    finish_event = AgentEvent(seq=tool_event.seq + 1, event_type="finish", content="Task completed")
    await stream_service.emit_event(session_id, finish_event.model_dump())


@router.post("/run")
async def run_agent(req: RunRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    session_id = str(uuid.uuid4())
    # In full production, this dispatches to Celery. For Phase 2, BackgroundTasks suffices
    # to demonstrate the streaming decoupled from the request.
    background_tasks.add_task(agent_task, session_id, req.task)
    return {"session_id": session_id}

@router.get("/stream/{session_id}")
async def stream_agent(session_id: str) -> StreamingResponse:
    return StreamingResponse(
        stream_service.subscribe(session_id),
        media_type="text/event-stream"
    )
