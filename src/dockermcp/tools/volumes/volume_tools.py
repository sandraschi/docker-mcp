"""
Volume management tools for Docker MCP.

This module provides FastMCP 2.11.3 compatible tools for managing Docker volumes.
"""
from dockermcp.logging_config import logger, configure_logging
configure_logging()

from typing import Dict, Any, List, Optional
from fastmcp.tools import tool as Tool
from fastmcp.exceptions import ToolError
from dockermcp.core.volumes import VolumeManager
from dockermcp.tools.volumes.volume_models import (
    VolumeInfo, VolumeResponse, VolumeListResponse, VolumeInspectResponse,
    CreateVolumeRequest, VolumeOperationRequest, RemoveVolumeRequest, PruneVolumesRequest
)

# Initialize volume manager
import docker
volume_mgr = VolumeManager(docker_client=docker.from_env())

@Tool(
    name="list_volumes",
    description="List all Docker volumes with their configurations and usage information"
)
async def list_volumes() -> Dict[str, Any]:
    """List all Docker volumes with their configurations and usage information."""
    try:
        volumes = await volume_mgr.list_volumes()
        total_size = sum(v.get('UsageData', {}).get('Size', 0) for v in volumes)
        return VolumeListResponse(
            success=True,
            message="Volumes listed successfully",
            volumes=volumes,
            total_size=total_size
        ).dict()
    except Exception as e:
        return VolumeResponse(
            success=False,
            message=f"Failed to list volumes: {str(e)}",
            error=str(e)
        ).dict()

@Tool(
    name="create_volume",
    description="Create a new Docker volume with the specified configuration"
)
async def create_volume(
    request: CreateVolumeRequest
) -> Dict[str, Any]:
    """Create a new Docker volume with the specified configuration."""
    try:
        volume = await volume_mgr.create_volume(
            name=request.name,
            driver=request.driver,
            driver_opts=request.driver_opts,
            labels=request.labels
        )
        return VolumeResponse(
            success=True,
            message="Volume created successfully",
            volume=volume
        ).dict()
    except Exception as e:
        return VolumeResponse(
            success=False,
            message=f"Failed to create volume: {str(e)}",
            error=str(e)
        ).dict()

@Tool(
    name="inspect_volume",
    description="Get detailed information about a specific volume"
)
async def inspect_volume(
    request: VolumeOperationRequest
) -> Dict[str, Any]:
    """Get detailed information about a specific volume."""
    try:
        volume = await volume_mgr.inspect_volume(volume_name=request.volume_name)
        return VolumeInspectResponse(
            success=True,
            message="Volume info retrieved",
            volume=volume,
            mountpoint=volume.get('Mountpoint'),
            usage_data=volume.get('UsageData')
        ).dict()
    except Exception as e:
        return VolumeResponse(
            success=False,
            message=f"Failed to inspect volume: {str(e)}",
            error=str(e)
        ).dict()

@Tool(
    name="remove_volume",
    description="Remove a Docker volume, with an option to force removal"
)
async def remove_volume(
    request: RemoveVolumeRequest
) -> Dict[str, Any]:
    """Remove a Docker volume, with an option to force removal."""
    try:
        await volume_mgr.remove_volume(
            volume_name=request.volume_name,
            force=request.force
        )
        return VolumeResponse(
            success=True,
            message=f"Volume '{request.volume_name}' removed successfully"
        ).dict()
    except Exception as e:
        return VolumeResponse(
            success=False,
            message=f"Failed to remove volume: {str(e)}",
            error=str(e)
        ).dict()

@Tool(
    name="prune_volumes",
    description="Remove all unused volumes, with optional filters"
)
async def prune_volumes(
    request: Optional[PruneVolumesRequest] = None
) -> Dict[str, Any]:
    """Remove all unused volumes, with optional filters."""
    try:
        filters = request.filters if request else None
        result = await volume_mgr.prune_volumes(filters=filters)
        return {
            "success": True,
            "message": "Volumes pruned successfully",
            "volumes_deleted": result.get('VolumesDeleted', []),
            "space_reclaimed": result.get('SpaceReclaimed', 0)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to prune volumes: {str(e)}",
            "error": str(e)
        }

