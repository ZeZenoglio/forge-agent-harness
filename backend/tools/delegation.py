import asyncio
import uuid

from backend.agent.events import AgentEvent
from backend.services.streaming import StreamService

# Since tools can't easily circularly import OpenHandsRuntime, we use a simple functional approach
# or rely on DI in the tool registration.

stream_service = StreamService()

async def delegate_task(task_description: str, model_alias: str = "default-agent") -> str:
    """Spawns a sub-agent to work on a specific task and returns its final answer."""
    # To prevent circular imports and simplify mock execution in Phase 5:
    from backend.agent.openhands_runtime import OpenHandsRuntime
    from backend.agent.policies import PolicyEngine
    
    sub_session_id = f"sub-{uuid.uuid4()}"
    policy_engine = PolicyEngine(workspace_root="/tmp/forge_workspace")
    runtime = OpenHandsRuntime(policy_engine=policy_engine)
    
    await runtime.init_session(sub_session_id)
    
    # Emit start event to sub-agent's own stream (can be monitored in Langfuse)
    start_event = AgentEvent(seq=0, event_type="start", content=f"Sub-agent started for task: {task_description}")
    await stream_service.emit_event(sub_session_id, start_event.model_dump())
    
    # Run steps (mocking the sub-agent loop)
    event_1 = await runtime.step(sub_session_id, start_event)
    await stream_service.emit_event(sub_session_id, event_1.model_dump())
    
    # A real sub-agent would loop here. We just mock a result.
    await asyncio.sleep(1) # simulate work
    
    result_content = f"Sub-agent completed task '{task_description}' successfully."
    finish_event = AgentEvent(seq=event_1.seq + 1, event_type="finish", content=result_content)
    await stream_service.emit_event(sub_session_id, finish_event.model_dump())
    
    return result_content
