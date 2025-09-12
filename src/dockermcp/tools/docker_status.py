"""
Docker Status Tool for FastMCP 2.12

Provides detailed information about Docker daemon status and connectivity.
"""

import json
from typing import Dict, Any

from fastmcp.tools import Tool, tool, tool, tool
from dockermcp import get_docker_status

@Tool(
    name="docker_status",
    description="Get detailed status of the Docker daemon and its connection",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def docker_status() -> str:
    """
    Get comprehensive status information about the Docker daemon.
    
    Returns:
        str: Formatted JSON string with Docker status information
    """
    status = get_docker_status()
    
    # Format the output for better readability
    output = [
        "🚀 Docker Status",
        "=" * 50,
        f"Status: {'✅ Running' if status.get('docker_available') else '❌ Not Available'}",
        f"Platform: {status.get('platform', 'Unknown')}",
        f"Connection Type: {status.get('connection_type', 'Unknown')}"
    ]
    
    # Add version information if available
    if status.get('version'):
        output.extend([
            "",
            "📦 Version Information",
            "-" * 50,
            f"Docker Version: {status.get('version')}",
            f"API Version: {status.get('api_version')}"
        ])
    
    # Add service status for Windows
    if status.get('service_status'):
        service_status = status['service_status'].capitalize()
        output.extend([
            "",
            "🔧 Service Status",
            "-" * 50,
            f"Docker Service: {service_status}"
        ])
    
    # Add error information if Docker is not available
    if not status.get('docker_available'):
        output.extend([
            "",
            "❌ Troubleshooting",
            "-" * 50,
            "1. Make sure Docker Desktop is running",
            "2. Run 'docker version' in a terminal to test the connection",
            "3. Check Docker Desktop logs for errors"
        ])
    
    # Add container stats if available
    if status.get('containers_total') is not None:
        output.extend([
            "",
            "📊 Container Stats",
            "-" * 50,
            f"Running Containers: {status.get('containers_running', 0)}",
            f"Total Containers: {status.get('containers_total', 0)}",
            f"Total Images: {status.get('images_count', 0)}"
        ])
    
    return "\n".join(output)

# Register the tool
def register_tool():
    """Register the docker_status tool with FastMCP."""
    return [docker_status]
