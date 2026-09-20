from typing import Any

from backend.tools.delegation import delegate_task
from backend.tools.file import edit_file, list_directory, read_file, write_file
from backend.tools.shell import execute_shell
from backend.tools.web import fetch_url

from .events import AgentEvent
from .policies import PolicyEngine
from .runtime import AgentRuntime

# This is the ONLY file allowed to import openhands.*
# In full implementation, we will use importlib to dynamically load it

class OpenHandsRuntime(AgentRuntime):
    """
    Adapter bridging the AgentRuntime protocol and the OpenHands SDK.
    Integrates the PolicyEngine for guardrails before execution.
    """

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self.policy_engine = policy_engine
        self.seq_counter = 0

    async def init_session(self, session_id: str, user_id: str = "anonymous_user") -> None:
        # Pass user_id to policy engine or Langfuse setup here if needed
        self.policy_engine.init_session(session_id)

    async def step(self, session_id: str, input_event: AgentEvent) -> AgentEvent:
        if not self.policy_engine.check_budget(session_id):
            return self._build_event("error", "Budget exceeded (iterations or tokens)")

        # Dummy integration with openhands for Phase 2 implementation
        # In a real implementation, we pass the event to openhands agent step
        
        # We simulate that the agent decided to execute a tool:
        action_signature = f"simulate_tool_{self.seq_counter}"
        
        if not self.policy_engine.check_thrashing(session_id, action_signature):
            return self._build_event("error", "Thrashing detected. Agent loop aborted.")
            
        self.seq_counter += 1
        return self._build_event("thought", "Agent processed input")

    async def execute_tool(
        self, session_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        
        if not self.policy_engine.validate_tool_args(tool_name, arguments):
            return {"error": "Tool arguments blocked by PolicyEngine due to violation"}
            
        self.policy_engine.check_requires_approval(tool_name, arguments)
            
        try:
            if tool_name == "read_file":
                return read_file(arguments["path"])
            elif tool_name == "write_file":
                return write_file(arguments["path"], arguments["content"])
            elif tool_name == "edit_file":
                return edit_file(arguments["path"], arguments["old_string"], arguments["new_string"])
            elif tool_name == "list_directory":
                return list_directory(arguments["path"])
            elif tool_name == "execute_shell":
                return execute_shell(arguments.get("command", ""))
            elif tool_name == "fetch_url":
                return fetch_url(arguments.get("url", ""))
            elif tool_name == "delegate_task":
                return await delegate_task(
                    task_description=arguments.get("task_description", ""),
                    model_alias=arguments.get("model_alias", "default-agent")
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
                    body=arguments.get("body", "")
                )
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Tool execution failed: {e!s}"}
            
    async def close(self, session_id: str) -> None:
        """Close the session."""
            
    def _build_event(self, event_type: str, content: str) -> AgentEvent:
        self.seq_counter += 1
        return AgentEvent(
            seq=self.seq_counter,
            event_type=event_type,
            content=content
        )
