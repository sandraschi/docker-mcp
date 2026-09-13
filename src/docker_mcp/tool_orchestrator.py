"""Tool orchestrator for agentic chat - matches NL queries to Docker tools and executes them."""

import time
from typing import Any

from dockermcp.mcp_instance import get_mcp

TOOL_PATTERNS: dict[str, list[str]] = {
    "list_containers": ["list container", "running container", "show container", "all container", "what.*container"],
    "list_images": ["list image", "show image", "available image", "what image"],
    "get_system_info": ["docker info", "system info", "daemon info", "engine info", "docker version"],
    "get_disk_usage": ["disk usage", "disk space", "storage", "how much space", "docker disk"],
}

COMPOSE_PATTERNS: list[str] = ["compose", "docker-compose", "docker compose"]


def _match_query(query: str) -> str | None:
    q = query.lower()
    for tool, patterns in TOOL_PATTERNS.items():
        for pat in patterns:
            import re

            if re.search(pat, q):
                return tool
    return None


async def execute_tool(tool_name: str, query: str) -> dict[str, Any]:
    """Execute an MCP tool by name, passing heuristically derived params."""
    mcp = get_mcp()
    params: dict[str, Any] = {}
    start = time.monotonic()

    if tool_name == "list_containers":
        q = query.lower()
        params = {"all_states": True}
        if "running" in q:
            params = {"all_states": False}
    elif tool_name == "list_images":
        params = {"all": True}
    elif tool_name == "get_disk_usage":
        params = {"include_disk_usage": True, "include_swarm_info": False}
    elif tool_name == "get_disk_usage":
        params = {"detailed": True}

    tool = next((t for t in (await mcp.list_tools()) if t.name == tool_name), None)
    if not tool:
        return {"success": False, "error": f"Tool '{tool_name}' not found"}

    try:
        result = await mcp.call_tool(tool_name, params)
        elapsed = time.monotonic() - start
        return {
            "success": True,
            "tool": tool_name,
            "params": params,
            "result": str(result),
            "timing_ms": round(elapsed * 1000),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "success": False,
            "tool": tool_name,
            "params": params,
            "error": str(e),
            "timing_ms": round(elapsed * 1000),
        }


def tool_to_nl_name(tool: str) -> str:
    """Pretty name for a tool."""
    names = {
        "list_containers": "List Containers",
        "list_images": "List Images",
        "get_system_info": "Docker System Info",
        "get_disk_usage": "Disk Usage",
        "prune_images": "Prune Images",
        "container_logs": "Container Logs",
    }
    return names.get(tool, tool.replace("_", " ").title())
