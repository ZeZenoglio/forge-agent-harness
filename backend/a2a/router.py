import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.routes.agent import agent_task
from backend.services.streaming import StreamService

a2a_router = APIRouter()
well_known_router = APIRouter()
stream_service = StreamService()

class A2ATaskRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: dict[str, Any]

class A2ATaskResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: dict[str, Any]

@well_known_router.get("/.well-known/agent.json")
async def get_agent_card() -> JSONResponse:
    """Returns the A2A Agent Card."""
    card = {
        "name": "Forge Agent",
        "description": "Forge autonomous agent capable of file manipulation, shell execution, and sub-agent delegation.",
        "capabilities": [
            "read_file",
            "write_file",
            "execute_shell",
            "web_search",
            "delegate_task"
        ],
        "supported_content_types": ["text/plain", "application/json"],
        "endpoints": {
            "tasks_send": "/a2a/tasks/send",
            "tasks_get": "/a2a/tasks/get"
        }
    }
    return JSONResponse(card)

@a2a_router.post("/tasks/send")
async def tasks_send(req: A2ATaskRequest, background_tasks: BackgroundTasks) -> A2ATaskResponse:
    if req.method != "submit_task":
        return A2ATaskResponse(id=req.id, result={"error": "Method not supported"})
    
    task_description = req.params.get("task", "")
    session_id = str(uuid.uuid4())
    
    # Run the same background agent logic
    background_tasks.add_task(agent_task, session_id, task_description)
    
    return A2ATaskResponse(
        id=req.id,
        result={"task_id": session_id, "status": "working"}
    )

@a2a_router.post("/tasks/get")
async def tasks_get(req: A2ATaskRequest) -> A2ATaskResponse:
    if req.method != "get_status":
        return A2ATaskResponse(id=req.id, result={"error": "Method not supported"})
    
    task_id = req.params.get("task_id")
    # For now, return a generic status since we don't have persistent state in this mock
    return A2ATaskResponse(
        id=req.id,
        result={"task_id": task_id, "status": "completed"}
    )

@a2a_router.get("/tasks/stream/{task_id}")
async def tasks_stream(task_id: str) -> StreamingResponse:
    return StreamingResponse(
        stream_service.subscribe(task_id),
        media_type="text/event-stream"
    )
