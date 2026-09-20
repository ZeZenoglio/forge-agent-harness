import subprocess


def execute_shell(command: str, timeout: int = 30) -> str:
    """Execute a shell command with a timeout."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds"
    except Exception as e:  # noqa: BLE001
        return f"Error executing command: {e!s}"
