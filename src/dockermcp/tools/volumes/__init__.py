"""
Volume tools package for Docker MCP.

This package provides comprehensive volume management tools following
FastMCP 2.12+ standards.
"""

# Import volume tools to register them with FastMCP
from .volume_management import (
    VolumeCreateResponse,
    VolumeListResponse,
    VolumePruneResponse,
    VolumeRemoveResponse,
    create_volume,
    list_volumes,
    prune_volumes,
    remove_volume,
)

__all__ = [
    "VolumeCreateResponse",
    "VolumeListResponse",
    "VolumePruneResponse",
    "VolumeRemoveResponse",
    "create_volume",
    "list_volumes",
    "prune_volumes",
    "remove_volume",
]
