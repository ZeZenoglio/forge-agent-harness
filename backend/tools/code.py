import os
import resource
import subprocess
import sys
import tempfile
from typing import Any


def _set_resource_limits(max_memory_mb: int = 256, max_cpu_seconds: int = 10) -> None:
    """Apply memory and CPU resource limits on POSIX subprocesses."""
    try:
        # Address space (virtual memory) limit in bytes
        bytes_limit = max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
        # CPU time limit in seconds
        resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds))
    except (ValueError, OSError, AttributeError):
        # Ignore on platforms where resource limits cannot be set
        pass


def execute_code(
    language: str,
    code: str,
    timeout: int = 10,
    memory_limit_mb: int = 256,
    packages: list[str] | None = None,
    working_directory: str | None = None,
) -> dict[str, Any]:
    """Execute code in an isolated subprocess with resource limits and timeout.

    Supported languages: 'python', 'bash', 'sh', 'javascript', 'node'.
    """
    lang = language.lower().strip()
    with tempfile.TemporaryDirectory(dir=working_directory) as temp_dir:
        # If packages requested for python workspace execution, virtual environment or PYTHONPATH can be configured
        env = os.environ.copy()
        if packages:
            env["INSTALLED_PACKAGES"] = ",".join(packages)

        if lang in ("python", "python3", "py"):
            script_path = os.path.join(temp_dir, "script.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = [sys.executable, script_path]

        elif lang in ("bash", "sh"):
            script_path = os.path.join(temp_dir, "script.sh")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = ["/bin/bash", script_path]

        elif lang in ("javascript", "js", "node"):
            script_path = os.path.join(temp_dir, "script.js")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = ["node", script_path]

        else:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Unsupported language: {language}",
                "language": language,
            }

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                cwd=temp_dir,
                env=env,
                preexec_fn=lambda: _set_resource_limits(
                    max_memory_mb=memory_limit_mb, max_cpu_seconds=timeout
                ),
            )
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "language": lang,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "language": lang,
            }
        except Exception as e:  # noqa: BLE001
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution error: {e!s}",
                "language": lang,
            }
