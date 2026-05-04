"""
System tools package for Docker MCP.

This package provides comprehensive system management tools following
FastMCP 2.12+ standards.
"""

# Import system tools to register them with FastMCP
from .system_management import (
    DiskUsageRequest,
    DiskUsageResponse,
    ParseDurationRequest,
    ParseDurationResponse,
    PruneSystemRequest,
    PruneSystemResponse,
    SystemInfoRequest,
    SystemInfoResponse,
    get_disk_usage,
    get_system_info,
    parse_duration,
    prune_system,
)

__all__ = [
    "DiskUsageRequest",
    "DiskUsageResponse",
    "ParseDurationRequest",
    "ParseDurationResponse",
    "PruneSystemRequest",
    "PruneSystemResponse",
    "SystemInfoRequest",
    "SystemInfoResponse",
    "get_disk_usage",
    "get_system_info",
    "parse_duration",
    "prune_system",
]
