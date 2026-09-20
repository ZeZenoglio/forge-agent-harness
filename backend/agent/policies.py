import re
from pathlib import Path
from typing import Any


class ApprovalRequiredException(Exception):
    """Raised when an action requires human approval."""

class PolicyEngine:
    """
    Synchronous policy engine evaluating constraints before any tool is run.
    Implements budget tracking, thrash breaking, PII scrubbing, and validation.
    """
    def __init__(self, workspace_root: str, max_iterations: int = 30, max_tokens: int = 100000):
        self.workspace_root = Path(workspace_root).resolve()
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        
        self.iteration_counts: dict[str, int] = {}
        self.token_counts: dict[str, int] = {}
        self.action_history: dict[str, list[str]] = {}
        
        # Common secret regex patterns (AWS keys, JWTs, generic secrets)
        self.secret_patterns = [
            re.compile(r'(?i)(?:api_key|secret|token|password|auth|bearer)[^a-z0-9]*[a-z0-9_]{16,}'),
            re.compile(r'AKIA[0-9A-Z]{16}'), # AWS Access Key
            re.compile(r'eyJ[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,}'), # JWT
            re.compile(r'gh[pousr]_[A-Za-z0-9_]{36}'), # GitHub tokens
        ]
        
    def init_session(self, session_id: str) -> None:
        self.iteration_counts[session_id] = 0
        self.token_counts[session_id] = 0
        self.action_history[session_id] = []

    def check_budget(self, session_id: str) -> bool:
        """Abort if max iterations or token limits are exceeded."""
        iters = self.iteration_counts.get(session_id, 0)
        tokens = self.token_counts.get(session_id, 0)
        
        if iters >= self.max_iterations:
            return False
        return not tokens >= self.max_tokens
        
    def check_thrashing(self, session_id: str, action_signature: str) -> bool:
        """Abort if the agent loops exactly the same action >3 times consecutively."""
        history = self.action_history.get(session_id, [])
        history.append(action_signature)
        
        return not (len(history) >= 3 and history[-1] == history[-2] == history[-3])
        
    def scrub_pii(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Strip PII and Secrets from payload (shallow check for phase 2)."""
        scrubbed = {}
        for k, v in payload.items():
            if isinstance(v, str):
                for pattern in self.secret_patterns:
                    v = pattern.sub('[REDACTED]', v)
            scrubbed[k] = v
        return scrubbed
        
    def validate_tool_args(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Block illegal arguments and enforce workspace containment."""
        if tool_name in ["execute_shell"]:
            command = arguments.get("command", "")
            # Basic deny-list for phase 2
            deny_list = ["nc ", "curl ", "wget ", "rm -rf /"]
            if any(deny in command for deny in deny_list):
                return False
                
        if tool_name in ["read_file", "write_file", "edit_file"]:
            file_path = arguments.get("path") or arguments.get("file_path")
            if file_path:
                try:
                    target_path = Path(file_path).resolve()
                    # Check if target_path is within workspace_root
                    if not str(target_path).startswith(str(self.workspace_root)):
                        return False
                except Exception:  # noqa: BLE001
                    return False
                    
        return True

    def check_requires_approval(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Raise ApprovalRequiredException if the tool call requires human intervention."""
        # For Phase 2, any shell command with sudo requires approval
        if tool_name == "execute_shell":
            command = arguments.get("command", "")
            if "sudo" in command:
                raise ApprovalRequiredException(f"Command requires human approval: {command}")
        
        # We can expand this list (e.g., deleting files, sending emails)
        if tool_name == "delete_file":
            raise ApprovalRequiredException(f"Deleting file requires human approval: {arguments.get('path')}")
