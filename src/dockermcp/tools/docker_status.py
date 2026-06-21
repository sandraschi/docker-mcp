"""
Docker Status Tool - Provides Docker daemon status information.

This module provides functionality to check the status of the Docker daemon
and related services.
"""

from typing import Any

from dockermcp.docker_context import get_docker_status
from dockermcp.mcp_instance import mcp


@mcp.tool()
async def get_docker_status_tool() -> dict[str, Any]:
    """
    Get the current status of the Docker daemon and related services.

    Returns:
        Dictionary containing Docker status information
    """
    return get_docker_status()


def register_tool():
    """Register the Docker status tool with the MCP server.

    Returns:
        List of tool functions to register
    """
    return [get_docker_status_tool]
