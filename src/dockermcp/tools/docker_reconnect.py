"""
Docker Reconnect Tool for FastMCP 2.12

Provides functionality to attempt reconnection to the Docker daemon.
"""

import sys
from typing import Dict, Any

from fastmcp.tools import Tool, tool, tool, tool
from dockermcp import retry_docker_connection, get_docker_status, docker_client

@Tool(
    name="docker_reconnect",
    description="Attempt to reconnect to the Docker daemon",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def docker_reconnect() -> str:
    """
    Attempt to reconnect to the Docker daemon and return the connection status.
    
    Returns:
        str: Status message indicating success or failure of reconnection
    """
    if not sys.platform.startswith('win'):
        return (
            "⚠️  Docker reconnection is only supported on Windows.\n"
            "On other platforms, please restart the Docker service manually."
        )
    
    result = retry_docker_connection()
    status = get_docker_status()
    
    if result and docker_client:
        try:
            version = docker_client.version()
            return (
                "✅ Successfully reconnected to Docker daemon!\n\n"
                f"Version: {version.get('Version', 'unknown')}\n"
                f"API Version: {version.get('ApiVersion', 'unknown')}\n\n"
                "Docker operations are now available."
            )
        except Exception as e:
            return f"⚠️  Reconnected but encountered an error: {str(e)}"
    
    # If we get here, reconnection failed
    error_msg = status.get('error', 'Unknown error')
    service_status = status.get('service_status', 'unknown')
    
    output = [
        "❌ Failed to reconnect to Docker daemon",
        "",
        "Error:",
        f"  {error_msg}",
        "",
        "Troubleshooting steps:",
        "1. Make sure Docker Desktop is running",
        "2. Check Docker Desktop logs for errors",
        "3. Try restarting Docker Desktop",
        "4. If the issue persists, restart your computer"
    ]
    
    if service_status == 'stopped':
        output.extend([
            "",
            "💡 The Docker service is currently stopped. Try starting it first."
        ])
    
    return "\n".join(output)

# Register the tool
def register_tool():
    """Register the docker_reconnect tool with FastMCP."""
    return [docker_reconnect]
