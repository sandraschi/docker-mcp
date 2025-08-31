"""
System-level tools for Docker MCP.

This module provides FastMCP 2.10.1 compatible tools for Docker system operations.
"""
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
    
    # Tools
    'system_info',
    'system_disk_usage',
    'system_ping',
    'system_auth',
    'system_prune',
    'system_events',
    'system_data_usage'
]

# Register all tools with MCP
from ..tools import mcp
tools = [
    system_info,
    docker_version,
    system_prune
]

for tool in tools:
    mcp.tool(tool)
