import asyncio
import json
import uuid

from backend.agent.events import AgentEvent
from backend.services.streaming import StreamService

stream_service = StreamService()

from typing import Any


async def _run_sub_agent(task_description: str, model_alias: str) -> dict[str, Any]:
    from backend.agent.openhands_runtime import OpenHandsRuntime
    from backend.agent.policies import PolicyEngine

    sub_session_id = f"sub-{uuid.uuid4()}"
    policy_engine = PolicyEngine(workspace_root="/tmp/forge_workspace")
    runtime = OpenHandsRuntime(policy_engine=policy_engine)

    await runtime.init_session(sub_session_id)

    trajectory = []

    # Start Event
    start_event = AgentEvent(
        seq=0,
        event_type="start",
        content=f"Sub-agent started for task: {task_description}",
    )
    await stream_service.emit_event(sub_session_id, start_event.model_dump())
    trajectory.append(start_event.model_dump())

    # Mocking multiple steps for a complex sub-agent trajectory
    for i in range(1, 4):
        event = await runtime.step(sub_session_id, start_event)
        await stream_service.emit_event(sub_session_id, event.model_dump())
        trajectory.append(event.model_dump())
        await asyncio.sleep(0.5)

    finish_content = f"Sub-agent completed task '{task_description}' successfully."
    finish_event = AgentEvent(seq=4, event_type="finish", content=finish_content)
    await stream_service.emit_event(sub_session_id, finish_event.model_dump())
    trajectory.append(finish_event.model_dump())

    return {
        "task": task_description,
        "session_id": sub_session_id,
        "result": finish_content,
        "trajectory": trajectory,
    }


async def delegate_task(
    task_description: str, model_alias: str = "default-agent"
) -> str:
    """Spawns a sub-agent to work on a specific task and returns its final answer and trajectory."""
    # To support parallel complex sub-agent orchestration, we could use asyncio.gather here if we passed multiple tasks.
    # For now, we enhance the return payload with rich trajectory information.

    # We will simulate handling a comma-separated list of tasks for parallel execution
    tasks = [t.strip() for t in task_description.split(";") if t.strip()]
    if not tasks:
        tasks = [task_description]

    results = await asyncio.gather(*[_run_sub_agent(t, model_alias) for t in tasks])

    return json.dumps(results, indent=2)
