"""
Docker Reconnect Tool - Handles reconnection to Docker daemon.

This module provides functionality to attempt reconnection to the Docker daemon
if the connection is lost.
"""
from typing import Dict, Any

from fastmcp.tools.tool import Tool
from dockermcp import retry_docker_connection, docker_available

@Tool(
    name="reconnect_docker",
    description="Attempt to reconnect to the Docker daemon",
    parameters={
        "type": "object",
        "properties": {
            "max_retries": {
                "type": "integer", 
                "default": 3,
                "description": "Maximum number of retry attempts"
            },
            "retry_delay": {
                "type": "number", 
                "default": 1.0,
                "description": "Delay between retry attempts in seconds"
            }
        },
        "required": []
    },
    output_schema={
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "description": "Whether reconnection was successful"},
            "message": {"type": "string", "description": "Status message"},
            "docker_available": {"type": "boolean", "description": "Whether Docker is now available"}
        },
        "required": ["success", "message", "docker_available"]
    }
)
async def reconnect_docker(max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
    """
    Attempt to reconnect to the Docker daemon.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retry attempts in seconds
        
    Returns:
        Dict containing reconnection status
    """
    if docker_available:
        return {
            "success": True,
            "message": "Docker is already available",
            "docker_available": True
        }
    
    success = False
    for attempt in range(1, max_retries + 1):
        success = retry_docker_connection()
        if success:
            return {
                "success": True,
                "message": f"Successfully reconnected to Docker daemon on attempt {attempt}",
                "docker_available": True
            }
        
        if attempt < max_retries:
            import time
            time.sleep(retry_delay)
    
    return {
        "success": False,
        "message": f"Failed to reconnect to Docker daemon after {max_retries} attempts",
        "docker_available": False
    }

def register_tool():
    """Register the Docker reconnect tool with the MCP server.
    
    Returns:
        List of tool functions to register
    """
    return [reconnect_docker]
