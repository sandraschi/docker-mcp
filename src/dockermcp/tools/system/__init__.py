"""
System-level tools for Docker MCP.

This module provides FastMCP 2.12.0 compatible tools for Docker system operations.
"""
from typing import List
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolException

# Import models
from .system_models import (
    SystemInfo,
    SystemResponse,
    SystemPruneResponse,
    SystemDiskUsageResponse,
    SystemInfoResponse,
    SystemPingResponse,
    SystemAuthRequest,
    SystemAuthResponse,
    SystemPruneRequest,
    SystemEventsRequest,
    SystemEventsResponse,
    SystemDataUsageResponse
)

# Import tools
from .system_tools import (
    system_info,
    system_disk_usage,
    system_ping,
    system_auth,
    system_prune,
    system_events,
    system_data_usage
)

# Import new status tools with graceful failure handling
from .status_tools import (
    docker_status,
    docker_reconnect
)

# Tool registration
def get_tools() -> List[callable]:
    """
    Get all system management tools for registration with FastMCP 2.12+.
    
    Returns:
        List of @tool-decorated functions for all system management operations
    """
    return [
        # New graceful status tools (work without Docker)
        docker_status,
        docker_reconnect,
        
        # Traditional system tools (require Docker)
        system_info,
        system_disk_usage,
        system_ping,
        system_auth,
        system_prune,
        system_events,
        system_data_usage
    ]

# Export public API
__all__ = [
    # Models
    'SystemInfo',
    'SystemResponse',
    'SystemPruneResponse',
    'SystemDiskUsageResponse',
    'SystemInfoResponse',
    'SystemPingResponse',
    'SystemAuthRequest',
    'SystemAuthResponse',
    'SystemPruneRequest',
    'SystemEventsRequest',
    'SystemEventsResponse',
    'SystemDataUsageResponse',
    
    # New status tools
    'docker_status',
    'docker_reconnect',
    
    # Traditional tools
    'system_info',
    'system_disk_usage',
    'system_ping',
    'system_auth',
    'system_prune',
    'system_events',
    'system_data_usage',
    
    # Tool registration
    'get_tools'
]
