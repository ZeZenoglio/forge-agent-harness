"""Shell command execution tool with deny-list and workspace containment (REQ-025).

The execution is intentionally restricted:
- Commands are run in the workspace directory (not CWD of the server process).
- A deny-list blocks known-dangerous patterns before the process is spawned.
- A hard timeout prevents runaway commands.
- The environment is stripped to a minimal safe set so the subprocess cannot
  inherit credentials or tokens from the parent process's environment.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Commands that should never be executed by the agent (REQ-025 deny-list).
# These are checked against the raw command string before execution.
_DENY_PATTERNS: list[str] = [
    "rm -rf /",
    "rm -rf ~",
    ":(){ :|:& };:",  # fork bomb
    "dd if=/dev/",
    "mkfs.",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "nc -",  # netcat reverse shells
    "ncat ",
    "sudo ",
    "sudo\t",
    "sudo\n",
    "sudo",
    "curl http",  # outbound HTTP (allow curl for file, deny for network)
    "wget http",
    "> /dev/sda",
    "chmod 777 /",
    "chown root",
]

# Maximum bytes of combined stdout+stderr returned to context.
_OUTPUT_CAP = 8_000

# Minimal safe environment for subprocess execution (REQ-056: no credential leakage).
_SAFE_ENV_KEYS = {"PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR"}


def _build_safe_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}


def _check_deny_list(command: str) -> None:
    """Raise :class:`PermissionError` if *command* matches a deny pattern."""
    lower = command.lower().strip()
    for pattern in _DENY_PATTERNS:
        if pattern.lower() in lower:
            raise PermissionError(
                f"Command blocked by deny-list (matched: '{pattern}')"
            )


def execute_shell(
    command: str,
    workspace_root: str | Path | None = None,
    timeout: int = 30,
) -> str:
    """Execute *command* in a restricted shell, return combined output.

    Args:
        command: The shell command string to run.
        workspace_root: Working directory for the subprocess.  Defaults to
            ``FORGE_WORKSPACE`` env var or ``/tmp/forge_workspace``.
        timeout: Hard timeout in seconds.  Defaults to 30.

    Returns:
        Combined stdout + stderr, capped at ``_OUTPUT_CAP`` bytes.

    Raises:
        :class:`PermissionError`: If the command matches the deny-list.
    """
    _check_deny_list(command)

    cwd = (
        Path(workspace_root).resolve()
        if workspace_root
        else Path(os.getenv("FORGE_WORKSPACE", "/tmp/forge_workspace")).resolve()
    )
    cwd.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(cwd),
            env=_build_safe_env(),
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"

        if len(output) > _OUTPUT_CAP:
            output = output[:_OUTPUT_CAP] + "\n[... output truncated ...]"

        if result.returncode != 0:
            output += f"\n[exit code {result.returncode}]"

        return output or "(no output)"

    except subprocess.TimeoutExpired:
        return f"[ERROR] Command timed out after {timeout}s: {command}"
    except PermissionError:
        raise
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] Failed to execute command: {exc!s}"
