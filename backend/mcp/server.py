import os
from typing import Any

from fastmcp import FastMCP

from backend.agent.policies import PolicyEngine
from backend.tools.file import edit_file, list_directory, read_file, write_file
from backend.tools.shell import execute_shell
from backend.tools.web import fetch_url

# Initialize FastMCP Server
mcp = FastMCP("Forge MCP Server")

# Instantiate Policy Engine for the MCP session
WORKSPACE_ROOT = os.getenv("FORGE_WORKSPACE", "/tmp/forge_workspace")
policy = PolicyEngine(workspace_root=WORKSPACE_ROOT)

def _check_policy(tool_name: str, **kwargs: Any) -> None:
    """Helper to validate arguments before tool execution."""
    if not policy.validate_tool_args(tool_name, kwargs):
        raise ValueError(f"PolicyEngine blocked execution of {tool_name} with provided arguments.")


@mcp.tool()
def mcp_read_file(path: str) -> str:
    """Read contents of a file in the workspace."""
    _check_policy("read_file", path=path)
    return read_file(path)


@mcp.tool()
def mcp_write_file(path: str, content: str) -> str:
    """Write content to a file in the workspace."""
    _check_policy("write_file", path=path)
    return write_file(path, content)


@mcp.tool()
def mcp_edit_file(path: str, old_string: str, new_string: str) -> str:
    """Replace exactly old_string with new_string in a file."""
    _check_policy("edit_file", path=path)
    return edit_file(path, old_string, new_string)


@mcp.tool()
def mcp_list_directory(path: str) -> str:
    """List contents of a directory."""
    _check_policy("list_directory", path=path)
    return list_directory(path)


@mcp.tool()
def mcp_execute_shell(command: str) -> str:
    """Execute a shell command with a timeout."""
    _check_policy("execute_shell", command=command)
    return execute_shell(command)


@mcp.tool()
def mcp_fetch_url(url: str) -> str:
    """Fetch URL contents with SSRF protection."""
    _check_policy("fetch_url", url=url)
    return fetch_url(url)


if __name__ == "__main__":
    # FastMCP uses .run() internally which handles stdio and sse transparently.
    mcp.run(transport="stdio")
