"""
Container volume management for Docker MCP.

This module provides tools for managing Docker volumes including creation, inspection,
and removal. It follows FastMCP 2.12+ standards for tool registration and error handling.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Annotated

import docker
from docker.errors import DockerException, APIError, NotFound
from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

class VolumeDriver(str, Enum):
    """Supported Docker volume drivers."""
    LOCAL = "local"
    NONE = "none"
    # Add more drivers as needed

class VolumeCreateRequest(BaseModel):
    """Request model for creating a new volume."""
    name: Optional[str] = Field(
        None,
        description="Name of the volume. If not specified, Docker generates a name."
    )
    driver: str = Field(
        "local",
        description="Name of the volume driver to use. Defaults to 'local'."
    )
    driver_opts: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value mapping of driver options and values."
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to set on the volume, as a key-value mapping."
    )

class VolumeMount(BaseModel):
    """Model representing a volume mount in a container."""
    type: str = Field(..., description="The type of mount")
    source: str = Field(..., description="The source of the mount")
    target: str = Field(..., description="The target path in the container")
    read_only: bool = Field(False, description="Whether the mount is read-only")
    volume: Dict[str, Any] = Field(..., description="Volume details")

class ListVolumesParams(BaseModel):
    """Parameters for list_volumes tool."""
    names: List[str] = Field(
        default_factory=list,
        description="Filter volumes by names"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Filter by labels (key=value)"
    )
    dangling: Optional[bool] = Field(
        default=None,
        description="Filter for dangling volumes (true/false)"
    )
    driver: Optional[str] = Field(
        default=None,
        description="Filter by volume driver name"
    )

class CreateVolumeParams(BaseModel):
    """Parameters for create_volume tool."""
    name: Optional[str] = Field(
        None,
        description="Name of the volume. If not specified, Docker generates a name."
    )
    driver: str = Field(
        "local",
        description="Name of the volume driver to use. Defaults to 'local'."
    )
    driver_opts: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value mapping of driver options and values."
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to set on the volume, as a key-value mapping."
    )

class InspectVolumeParams(BaseModel):
    """Parameters for inspect_volume tool."""
    name: str = Field(
        ...,
        description="Name or ID of the volume to inspect"
    )

class RemoveVolumeParams(BaseModel):
    """Parameters for remove_volume tool."""
    name: str = Field(
        ...,
        description="Name or ID of the volume to remove"
    )
    force: bool = Field(
        False,
        description="Force removal even if in use"
    )

class PruneVolumesParams(BaseModel):
    """Parameters for prune_volumes tool."""
    filters: Dict[str, str] = Field(
        default_factory=dict,
        description="Filters to process on the prune list. "
                   "Valid filters: label (label=<key>=<value>), "
                   "label! (label!=<key>=<value>), all (true/false)"
    )

@mcp.tool(
    name="list_volumes",
    description="List Docker volumes with filtering options"
)
async def list_volumes(params: ListVolumesParams) -> Dict[str, Any]:
    """
    List Docker volumes with filtering options.
    
    This function lists all Docker volumes, with optional filtering by name, labels,
    dangling state, and driver.
    
    Args:
        params: ListVolumesParams containing:
            - names: List of volume names to filter by
            - labels: Dictionary of labels to filter by (key=value)
            - dangling: Filter for dangling volumes (true/false)
            - driver: Filter by volume driver name
        
    Returns:
        Dictionary with list of volumes and metadata
        
    Example:
        >>> await list_volumes(params=ListVolumesParams(
        ...     labels={"environment": "production"},
        ...     driver="local"
        ... ))
        {
            "status": "success",
            "data": {
                "volumes": [
                    {
                        "name": "my-volume",
                        "driver": "local",
                        "mountpoint": "/var/lib/docker/volumes/my-volume/_data",
                        "labels": {"environment": "production"},
                        "options": {},
                        "scope": "local",
                        "created_at": "2023-01-01T12:00:00Z",
                        "usage_data": {
                            "size": 10485760,
                            "ref_count": 2
                        }
                    }
                ],
                "count": 1
            },
            "message": "Found 1 volume(s)"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Build filters
        filters = {}
        if params.names:
            filters['name'] = params.names
        if params.labels:
            filters['label'] = [f"{k}={v}" for k, v in params.labels.items()]
        if params.dangling is not None:
            filters['dangling'] = [str(params.dangling).lower()]
        if params.driver:
            filters['driver'] = [params.driver]
        
        # List volumes
        volumes = client.volumes.list(filters=filters)
        
        # Prepare response
        result = []
        for vol in volumes:
            try:
                vol_info = vol.attrs
                usage_data = vol_info.get('UsageData', {})
                vol_info['usage_data'] = {
                    'size': usage_data.get('Size', 0),
                    'ref_count': usage_data.get('RefCount', 0)
                }
                result.append(vol_info)
            except (KeyError, AttributeError) as e:
                logger.warning(f"Error getting volume info: {str(e)}")
                vol_info['usage_data'] = None
                result.append(vol_info)
        
        count = len(result)
        return {
            'status': 'success',
            'data': {
                'volumes': result,
                'count': count
            },
            'message': f"Found {count} volume(s)"
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": "Docker daemon not available",
            "error": "DOCKER_DAEMON_UNAVAILABLE"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error listing volumes: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": "UNEXPECTED_ERROR"
        }

@mcp.tool(
    name="create_volume",
    description="Create a new Docker volume"
)
async def create_volume(params: CreateVolumeParams) -> Dict[str, Any]:
    """
    Create a new Docker volume.
    
    This function creates a new Docker volume with the specified configuration.
    
    Args:
        params: CreateVolumeParams containing:
            - name: Name of the volume (optional)
            - driver: Name of the volume driver to use (default: "local")
            - driver_opts: Key-value mapping of driver options and values
            - labels: Labels to set on the volume
        
    Returns:
        Dictionary with the created volume information
        
    Example:
        >>> await create_volume(params=CreateVolumeParams(
        ...     name="my-app-data",
        ...     driver="local",
        ...     driver_opts={"type": "nfs", "o": "addr=10.0.0.1"},
        ...     labels={"app": "my-app", "environment": "production"}
        ... ))
        {
            "status": "success",
            "data": {
                "volume": {
                    "name": "my-app-data",
                    "driver": "local",
                    "mountpoint": "/var/lib/docker/volumes/my-app-data/_data",
                    "labels": {"app": "my-app", "environment": "production"},
                    "options": {"type": "nfs", "o": "addr=10.0.0.1"},
                    "scope": "local",
                    "created_at": "2023-01-01T12:00:00Z"
                }
            },
            "message": "Volume 'my-app-data' created successfully"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Create the volume
        volume = client.volumes.create(
            name=params.name,
            driver=params.driver,
            driver_opts=params.driver_opts,
            labels=params.labels
        )
        
        # Get the created volume details
        volume.reload()
        
        volume_info = {
            'name': volume.name,
            'driver': volume.attrs['Driver'],
            'mountpoint': volume.attrs['Mountpoint'],
            'labels': volume.attrs.get('Labels', {}),
            'options': volume.attrs.get('Options', {}),
            'scope': volume.attrs.get('Scope', 'local'),
            'created_at': volume.attrs.get('CreatedAt')
        }
        
        return {
            'status': 'success',
            'data': {
                'volume': volume_info
            },
            'message': f"Volume '{volume.name}' created successfully"
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "error": "DOCKER_API_ERROR"
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": "Docker daemon not available",
            "error": "DOCKER_DAEMON_UNAVAILABLE"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error creating volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": "UNEXPECTED_ERROR"
        }

@mcp.tool(
    name="inspect_volume",
    description="Inspect a Docker volume"
)
async def inspect_volume(params: InspectVolumeParams) -> Dict[str, Any]:
    """
    Inspect a Docker volume.
    
    This function retrieves detailed information about a specific Docker volume.
    
    Args:
        params: InspectVolumeParams containing:
            - name: Name or ID of the volume to inspect
        
    Returns:
        Dictionary with the volume details
        
    Example:
        >>> await inspect_volume(params=InspectVolumeParams(name="my-volume"))
        {
            "status": "success",
            "data": {
                "volume": {
                    "name": "my-volume",
                    "driver": "local",
                    "mountpoint": "/var/lib/docker/volumes/my-volume/_data",
                    "labels": {"app": "my-app"},
                    "options": {},
                    "scope": "local",
                    "created_at": "2023-01-01T12:00:00Z",
                    "status": {},
                    "usage_data": {
                        "size": 10485760,
                        "ref_count": 2
                    }
                }
            },
            "message": "Volume 'my-volume' inspected successfully"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the volume
        try:
            volume = client.volumes.get(params.name)
        except NotFound:
            return {
                "status": "error",
                "message": f"Volume not found: {params.name}",
                "error": "VOLUME_NOT_FOUND"
            }
        
        # Get volume details
        volume.reload()
        
        # Prepare volume info
        volume_info = {
            'name': volume.name,
            'driver': volume.attrs['Driver'],
            'mountpoint': volume.attrs['Mountpoint'],
            'labels': volume.attrs.get('Labels', {}),
            'options': volume.attrs.get('Options', {}),
            'scope': volume.attrs.get('Scope', 'local'),
            'created_at': volume.attrs.get('CreatedAt'),
            'status': volume.attrs.get('Status', {})
        }
        
        # Add usage data if available
        if 'UsageData' in volume.attrs:
            volume_info['usage_data'] = volume.attrs['UsageData']
        
        return {
            'status': 'success',
            'data': {
                'volume': volume_info
            },
            'message': f"Volume '{volume.name}' inspected successfully"
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "error": "DOCKER_API_ERROR"
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": "Docker daemon not available",
            "error": "DOCKER_DAEMON_UNAVAILABLE"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error inspecting volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": "UNEXPECTED_ERROR"
        }

@mcp.tool(
    name="remove_volume",
    description="Remove a Docker volume"
)
async def remove_volume(params: RemoveVolumeParams) -> Dict[str, Any]:
    """
    Remove a Docker volume.
    
    Args:
        params: RemoveVolumeParams containing:
            - name: Name or ID of the volume to remove
            - force: Force removal even if in use (default: False)
        
    Returns:
        Dictionary with operation status and result
        
    Example:
        >>> await remove_volume(params=RemoveVolumeParams(
        ...     name="my-volume",
        ...     force=False
        ... ))
        {
            "status": "success",
            "data": {
                "volume_name": "my-volume",
                "removed": true
            },
            "message": "Volume 'my-volume' removed successfully"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the volume
        volume = client.volumes.get(params.name)
        volume.remove(force=params.force)
        
        return {
            "status": "success",
            "data": {
                "volume_name": params.name,
                "removed": True
            },
            "message": f"Volume '{params.name}' removed successfully"
        }
    except docker.errors.NotFound:
        return {
            "status": "error",
            "message": f"Volume '{params.name}' not found",
            "error": "VOLUME_NOT_FOUND"
        }
    except docker.errors.APIError as e:
        if "volume is in use" in str(e):
            return {
                "status": "error",
                "message": f"Cannot remove volume '{params.name}': volume is in use. Use force=True to remove it anyway.",
                "error": "VOLUME_IN_USE"
            }
        return {
            "status": "error",
            "message": f"Docker API error: {str(e)}",
            "error": "DOCKER_API_ERROR"
        }
    except Exception as e:
        error_msg = f"Failed to remove volume '{params.name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": "REMOVAL_FAILED"
        }

@mcp.tool(
    name="prune_volumes",
    description="Remove unused Docker volumes"
)
async def prune_volumes(params: PruneVolumesParams) -> Dict[str, Any]:
    """
    Remove unused Docker volumes.
    
    This function removes all unused volumes, with optional filtering.
    
    Args:
        params: PruneVolumesParams containing:
            - filters: Dictionary of filters to process on the prune list
                
    Returns:
        Dictionary with the prune results
        
    Example:
        >>> await prune_volumes(params=PruneVolumesParams(filters={"all": "true"}))
        {
            "status": "success",
            "data": {
                "volumes_deleted": ["volume1", "volume2"],
                "space_reclaimed": 104857600,
                "count": 2,
                "size_mb": 100.0
            },
            "message": "Pruned 2 volumes (100.0 MB)"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Prune volumes
        result = client.volumes.prune(filters=params.filters)
        
        # Prepare response
        volumes_deleted = result.get('VolumesDeleted', [])
        space_reclaimed = result.get('SpaceReclaimed', 0)
        size_mb = space_reclaimed / (1024 * 1024)
        count = len(volumes_deleted)
        
        return {
            "status": "success",
            "data": {
                "volumes_deleted": volumes_deleted,
                "space_reclaimed": space_reclaimed,
                "count": count,
                "size_mb": round(size_mb, 2)
            },
            "message": f"Pruned {count} volume(s) ({size_mb:.2f} MB)"
        }
        
    except docker.errors.APIError as e:
        error_msg = f"Docker API error while pruning volumes: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "error": "DOCKER_API_ERROR"
        }
    except docker.errors.DockerException as e:
        error_msg = f"Docker error while pruning volumes: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": "Docker daemon not available",
            "error": "DOCKER_DAEMON_UNAVAILABLE"
        }
    except Exception as e:
        error_msg = f"Unexpected error while pruning volumes: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": "UNEXPECTED_ERROR"
        }
