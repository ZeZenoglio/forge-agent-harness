"""Tools discovery and inspection endpoints (REQ-033)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])

AVAILABLE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "description": "Searches the web using self-hosted SearXNG meta-search engine.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetches and cleans web page content with SSRF protection.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Web URL to fetch"},
                "max_chars": {"type": "integer", "default": 10000},
            },
            "required": ["url"],
        },
    },
    {
        "name": "execute_code",
        "description": "Executes Python or Bash code in an isolated subprocess with CPU and memory limits.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code snippet to run"},
                "language": {
                    "type": "string",
                    "enum": ["python", "bash"],
                    "default": "python",
                },
                "timeout_seconds": {"type": "integer", "default": 30},
            },
            "required": ["code"],
        },
    },
    {
        "name": "generate_pdf",
        "description": "Compiles LaTeX or generates PDF reports as downloadable artifacts.",
        "parameters": {
            "type": "object",
            "properties": {
                "latex_source": {"type": "string"},
                "title": {"type": "string", "default": "document.pdf"},
            },
            "required": ["latex_source"],
        },
    },
    {
        "name": "analyze_image",
        "description": "Interprets images, diagrams, charts, and extracts visual information or text.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string"},
                "prompt": {"type": "string", "default": "Describe this image."},
            },
            "required": ["image_path"],
        },
    },
    {
        "name": "extract_structured",
        "description": "Extracts structured data conforming to a JSON schema from unstructured text, PDFs, or images.",
        "parameters": {
            "type": "object",
            "properties": {
                "input_data": {
                    "type": "string",
                    "description": "Raw text or path to file/image",
                },
                "schema": {"type": "object", "description": "Target JSON schema"},
            },
            "required": ["input_data", "schema"],
        },
    },
    {
        "name": "research_topic",
        "description": "Performs iterative multi-step research on a topic, synthesizing findings into a markdown report artifact with citations.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or research query"},
                "depth": {
                    "type": "string",
                    "enum": ["shallow", "deep"],
                    "default": "shallow",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "delegate_task",
        "description": "Spawns a sub-agent to work on a specialized sub-task and reports back.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string"},
                "model_alias": {"type": "string", "default": "default-agent"},
            },
            "required": ["task_description"],
        },
    },
]


@router.get("")
def list_tools() -> dict[str, Any]:
    """List available agent tools and their parameter schemas."""
    return {"data": AVAILABLE_TOOLS}


@router.get("/{tool_name}")
def get_tool_schema(tool_name: str) -> dict[str, Any]:
    """Inspect schema for a specific tool."""
    for tool in AVAILABLE_TOOLS:
        if tool["name"] == tool_name:
            return {"data": tool}
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
