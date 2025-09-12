"""
Docker Status Tool - Provides Docker daemon status information.

This module provides functionality to check the status of the Docker daemon
and related services.
"""
from typing import Dict, Any

from fastmcp.tools.tool import Tool
from dockermcp import get_docker_status

@Tool(
    name="get_docker_status",
    description="Get the current status of the Docker daemon and related services",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    output_schema={
        "type": "object",
        "properties": {
            "docker_running": {"type": "boolean", "description": "Whether Docker is running"},
            "docker_version": {"type": ["string", "null"], "description": "Docker version string if available"},
            "containers_running": {"type": "integer", "description": "Number of running containers"},
            "containers_total": {"type": "integer", "description": "Total number of containers"},
            "images_count": {"type": "integer", "description": "Number of Docker images"},
            "os_type": {"type": ["string", "null"], "description": "Host OS type"},
            "error": {"type": ["string", "null"], "description": "Error message if any"}
        },
        "required": ["docker_running", "containers_running", "containers_total", "images_count"]
    }
)
async def get_docker_status_tool() -> Dict[str, Any]:
    """
    Get the current status of the Docker daemon and related services.
    
    Returns:
        Dict containing Docker status information
    """
    return get_docker_status()

def register_tool():
    """Register the Docker status tool with the MCP server.
    
    Returns:
        List of tool functions to register
    """
    return [get_docker_status_tool]
