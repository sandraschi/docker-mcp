"""
Volume management tools for Docker MCP.

This module provides FastMCP 2.10.1 compatible tools for managing Docker volumes.
"""
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
    'prune_volumes'
]
