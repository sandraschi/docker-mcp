"""
System tools package for Docker MCP.

This package provides comprehensive system management tools following
FastMCP 2.12+ standards.
"""

# Import system tools to register them with FastMCP
from .system_management import *

__all__ = [
    # System management operations
    "get_system_info",
    "get_disk_usage",
    "prune_system",
    "parse_duration",

    # Request/Response models
    "SystemInfoRequest",
    "SystemInfoResponse",
    "DiskUsageRequest",
    "DiskUsageResponse",
    "PruneSystemRequest",
    "PruneSystemResponse",
    "ParseDurationRequest",
    "ParseDurationResponse"
]
