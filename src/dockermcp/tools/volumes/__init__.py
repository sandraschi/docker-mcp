"""
Volume management tools for Docker MCP.

This module provides FastMCP 2.12.0 compatible tools for managing Docker volumes.
"""
from typing import List
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolException

# Import models
from .volume_models import (
    VolumeInfo,
    VolumeResponse,
    VolumeListResponse,
    VolumeInspectResponse,
    CreateVolumeRequest,
    VolumeOperationRequest,
    RemoveVolumeRequest,
    PruneVolumesRequest
)

# Import tools
from .volume_tools import (
    list_volumes,
    create_volume,
    inspect_volume,
    remove_volume,
    prune_volumes
)

# Tool registration
def get_tools() -> List[callable]:
    """
    Get all volume management tools for registration with FastMCP 2.12+.
    
    Returns:
        List of @tool-decorated functions for all volume management operations
    """
    return [
        list_volumes,
        create_volume,
        inspect_volume,
        remove_volume,
        prune_volumes
    ]

# Export public API
__all__ = [
    # Models
    'VolumeInfo',
    'VolumeResponse',
    'VolumeListResponse',
    'VolumeInspectResponse',
    'CreateVolumeRequest',
    'VolumeOperationRequest',
    'RemoveVolumeRequest',
    'PruneVolumesRequest',
    
    # Tools
    'list_volumes',
    'create_volume',
    'inspect_volume',
    'remove_volume',
    'prune_volumes',
    
    # Tool registration
    'get_tools'
]
