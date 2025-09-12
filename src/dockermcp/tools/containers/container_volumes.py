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
from typing import Any, Dict, List, Optional, Union

import docker
from docker.errors import DockerException, APIError, NotFound
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, validator, HttpUrl

from dockermcp.logging_config import logger

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

@Tool(
    name="list_volumes",
    description="List Docker volumes",
    parameters={
        'type': 'object',
        'properties': {
            'names': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': [],
                'description': 'Filter by volume names'
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Filter by labels (key=value)'
            },
            'dangling': {
                'type': 'boolean',
                'default': None,
                'description': 'Filter for dangling volumes (true/false)'
            },
            'driver': {
                'type': 'string',
                'default': None,
                'description': 'Filter by volume driver name'
            }
        }
    }
)
async def list_volumes(
    names: List[str] = [],
    labels: Dict[str, str] = {},
    dangling: Optional[bool] = None,
    driver: Optional[str] = None
) -> Dict[str, Any]:
    """
    List Docker volumes with filtering options.
    
    This function lists all Docker volumes, with optional filtering by name, labels,
    dangling state, and driver.
    
    Args:
        names: Filter by volume names
        labels: Filter by labels (key=value)
        dangling: Filter for dangling volumes (true/false)
        driver: Filter by volume driver name
        
    Returns:
        Dictionary with list of volumes and metadata
        
    Example:
        >>> await list_volumes(
        ...     labels={"environment": "production"},
        ...     driver="local"
        ... )
        {
            "status": "success",
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
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Build filters
        filters = {}
        
        if names:
            filters['name'] = names
        if labels:
            filters['label'] = [f"{k}={v}" for k, v in labels.items()]
        if dangling is not None:
            filters['dangling'] = [str(dangling).lower()]
        if driver:
            filters['driver'] = driver
        
        # Get volumes
        volumes = client.volumes.list(filters=filters)
        
        # Prepare response
        volume_list = []
        
        for volume in volumes:
            volume_info = {
                'name': volume.name,
                'driver': volume.attrs['Driver'],
                'mountpoint': volume.attrs['Mountpoint'],
                'labels': volume.attrs.get('Labels', {}),
                'options': volume.attrs.get('Options', {}),
                'scope': volume.attrs.get('Scope', 'local'),
                'created_at': volume.attrs.get('CreatedAt')
            }
            
            # Try to get usage data (not always available)
            try:
                usage_data = volume.attrs.get('UsageData', {})
                volume_info['usage_data'] = {
                    'size': usage_data.get('Size', 0),
                    'ref_count': usage_data.get('RefCount', 0)
                }
            except (KeyError, AttributeError):
                volume_info['usage_data'] = None
            
            volume_list.append(volume_info)
        
        return {
            'status': 'success',
            'volumes': volume_list,
            'count': len(volume_list)
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error listing volumes: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="create_volume",
    description="Create a new Docker volume",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'default': None,
                'description': 'Name of the volume. If not specified, Docker generates a name.'
            },
            'driver': {
                'type': 'string',
                'default': 'local',
                'description': 'Name of the volume driver to use. Defaults to "local".'
            },
            'driver_opts': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Key-value mapping of driver options and values.'
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Labels to set on the volume, as a key-value mapping.'
            }
        }
    }
)
async def create_volume(
    name: Optional[str] = None,
    driver: str = 'local',
    driver_opts: Dict[str, str] = {},
    labels: Dict[str, str] = {}
) -> Dict[str, Any]:
    """
    Create a new Docker volume.
    
    This function creates a new Docker volume with the specified configuration.
    
    Args:
        name: Name of the volume. If not specified, Docker generates a name.
        driver: Name of the volume driver to use. Defaults to "local".
        driver_opts: Key-value mapping of driver options and values.
        labels: Labels to set on the volume, as a key-value mapping.
        
    Returns:
        Dictionary with the created volume information
        
    Example:
        >>> await create_volume(
        ...     name="my-app-data",
        ...     driver="local",
        ...     driver_opts={"type": "nfs", "o": "addr=10.0.0.1"},
        ...     labels={"app": "my-app", "environment": "production"}
        ... )
        {
            "status": "success",
            "volume": {
                "name": "my-app-data",
                "driver": "local",
                "mountpoint": "/var/lib/docker/volumes/my-app-data/_data",
                "labels": {"app": "my-app", "environment": "production"},
                "options": {"type": "nfs", "o": "addr=10.0.0.1"},
                "scope": "local",
                "created_at": "2023-01-01T12:00:00Z"
            }
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Create the volume
        volume = client.volumes.create(
            name=name,
            driver=driver,
            driver_opts=driver_opts,
            labels=labels
        )
        
        # Get the created volume details
        volume.reload()
        
        return {
            'status': 'success',
            'volume': {
                'name': volume.name,
                'driver': volume.attrs['Driver'],
                'mountpoint': volume.attrs['Mountpoint'],
                'labels': volume.attrs.get('Labels', {}),
                'options': volume.attrs.get('Options', {}),
                'scope': volume.attrs.get('Scope', 'local'),
                'created_at': volume.attrs.get('CreatedAt')
            }
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error creating volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="inspect_volume",
    description="Inspect a Docker volume",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Name or ID of the volume'
            }
        },
        'required': ['name']
    }
)
async def inspect_volume(name: str) -> Dict[str, Any]:
    """
    Inspect a Docker volume.
    
    This function retrieves detailed information about a specific Docker volume.
    
    Args:
        name: Name or ID of the volume
        
    Returns:
        Dictionary with the volume details
        
    Example:
        >>> await inspect_volume("my-volume")
        {
            "status": "success",
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
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the volume
        try:
            volume = client.volumes.get(name)
        except NotFound:
            return {
                "status": "error",
                "error": f"Volume not found: {name}"
            }
        
        # Get volume details
        volume.reload()
        
        # Prepare response
        result = {
            'status': 'success',
            'volume': {
                'name': volume.name,
                'driver': volume.attrs['Driver'],
                'mountpoint': volume.attrs['Mountpoint'],
                'labels': volume.attrs.get('Labels', {}),
                'options': volume.attrs.get('Options', {}),
                'scope': volume.attrs.get('Scope', 'local'),
                'created_at': volume.attrs.get('CreatedAt'),
                'status': volume.attrs.get('Status', {})
            }
        }
        
        # Add usage data if available
        if 'UsageData' in volume.attrs:
            result['volume']['usage_data'] = volume.attrs['UsageData']
        
        return result
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error inspecting volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="remove_volume",
    description="Remove a Docker volume",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Name or ID of the volume'
            },
            'force': {
                'type': 'boolean',
                'default': False,
                'description': 'Force the removal of the volume even if it's in use'
            }
        },
        'required': ['name']
    }
)
async def remove_volume(name: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker volume.
    
    This function removes a Docker volume. If the volume is in use by containers,
    the operation will fail unless force=True is specified.
    
    Args:
        name: Name or ID of the volume
        force: Force the removal of the volume even if it's in use
        
    Returns:
        Dictionary with the operation status
        
    Example:
        >>> await remove_volume("my-volume", force=True)
        {
            "status": "success",
            "message": "Volume removed successfully",
            "volume_name": "my-volume"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the volume
        try:
            volume = client.volumes.get(name)
        except NotFound:
            return {
                "status": "error",
                "error": f"Volume not found: {name}"
            }
        
        # Remove the volume
        volume.remove(force=force)
        
        return {
            'status': 'success',
            'message': 'Volume removed successfully',
            'volume_name': name
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error removing volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="prune_volumes",
    description="Remove unused Docker volumes",
    parameters={
        'type': 'object',
        'properties': {
            'filters': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Filters to process on the prune list. Valid filters: label (label=<key>=<value>), label! (label!=<key>=<value>), all (true/false)'
            }
        }
    }
)
async def prune_volumes(filters: Dict[str, str] = {}) -> Dict[str, Any]:
    """
    Remove unused Docker volumes.
    
    This function removes all unused volumes, with optional filtering.
    
    Args:
        filters: Filters to process on the prune list.
                Valid filters:
                - label (label=<key>=<value>)
                - label! (label!=<key>=<value>)
                - all (true/false)
                
    Returns:
        Dictionary with the prune results
        
    Example:
        >>> await prune_volumes(filters={"all": "true"})
        {
            "status": "success",
            "volumes_deleted": ["volume1", "volume2"],
            "space_reclaimed": 104857600,
            "message": "Pruned 2 volumes (100 MB)"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Prune volumes
        result = client.volumes.prune(filters=filters)
        
        # Prepare response
        volumes_deleted = result.get('VolumesDeleted', [])
        space_reclaimed = result.get('SpaceReclaimed', 0)
        
        return {
            'status': 'success',
            'volumes_deleted': volumes_deleted,
            'space_reclaimed': space_reclaimed,
            'message': f"Pruned {len(volumes_deleted)} volumes ({space_reclaimed / (1024*1024):.1f} MB)"
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error pruning volumes: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}
