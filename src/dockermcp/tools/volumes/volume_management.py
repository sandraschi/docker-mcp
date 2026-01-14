"""
Docker Volume Management for FastMCP 2.12+

This module provides comprehensive tools for managing Docker volumes including:
- Creating and removing volumes
- Inspecting volume details
- Listing and filtering volumes
- Managing volume data and metadata
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Literal, Annotated

import docker
from docker.errors import (
    DockerException, APIError, NotFound, 
    ImageNotFound, ContainerError, InvalidArgument
)
from dockermcp.mcp_instance import mcp
from pydantic import BaseModel, Field, Field, validator, HttpUrl, AnyUrl

from dockermcp.logging_config import logger

class VolumeDriver(str, Enum):
    """Supported Docker volume drivers."""
    LOCAL = "local"
    NONE = "none"
    # Add more drivers as needed

class VolumeCreateRequest(BaseModel):
    """Request model for creating a new Docker volume."""
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

class VolumeInspectResult(BaseModel):
    """Detailed information about a Docker volume."""
    name: str = Field(..., description="Name of the volume")
    driver: str = Field(..., description="Driver used by the volume")
    mountpoint: str = Field(..., description="Path where the volume is mounted on the host")
    created_at: Optional[datetime] = Field(None, description="When the volume was created")
    status: Optional[Dict[str, Any]] = Field(None, description="Status information about the volume")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels set on the volume")
    scope: str = Field(..., description="Scope of the volume (e.g., 'local', 'global')")
    options: Dict[str, str] = Field(default_factory=dict, description="Driver-specific options")
    usage_data: Optional[Dict[str, Any]] = Field(None, description="Usage statistics about the volume")

@mcp.tool()
async def list_volumes(
    names: Annotated[List[str], Field(default_factory=list, description="Filter by volume names")] = [],
    drivers: Annotated[List[str], Field(default_factory=list, description="Filter by volume drivers")] = [],
    labels: Annotated[Dict[str, str], Field(default_factory=dict, description="Filter by labels (e.g., {'environment': 'production'})")] = {},
    dangling: Annotated[Optional[bool], Field(None, description="Filter for dangling volumes (true/false)")] = None,
    driver: Annotated[Optional[str], Field(None, description="Filter by driver name (alias for drivers)")] = None,
    name: Annotated[Optional[str], Field(None, description="Filter by volume name (alias for names)")] = None
) -> Dict[str, Any]:
    """
    List Docker volumes with filtering options.
    
    This function lists all Docker volumes, with optional filtering by name,
    driver, labels, or dangling state.
    
    Args:
        names: Filter by volume names
        drivers: Filter by volume drivers
        labels: Filter by labels (key=value)
        dangling: Filter for dangling volumes (true/false)
        driver: Filter by driver name (alias for drivers)
        name: Filter by volume name (alias for names)
        
    Returns:
        Dictionary with list of volumes and metadata
        
    Example:
        >>> await list_volumes(
        ...     name="my-volume",
        ...     driver="local",
        ...     labels={"environment": "production"}
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
                    "created_at": "2023-01-01T12:00:00Z"
                }
            ],
            "count": 1
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Handle aliases
        if driver and driver not in drivers:
            drivers.append(driver)
        if name and name not in names:
            names.append(name)
        
        # Build filters
        filters = {}
        
        if names:
            filters['name'] = names
        if drivers:
            filters['driver'] = drivers
        if labels:
            filters['label'] = [f"{k}={v}" for k, v in labels.items()]
        if dangling is not None:
            filters['dangling'] = [str(dangling).lower()]
        
        # Get volumes
        volumes = client.volumes.list(filters=filters)
        
        # Prepare response
        volume_list = []
        
        for volume in volumes:
            try:
                # Get detailed information
                volume_info = {
                    'name': volume.name,
                    'driver': volume.attrs['Driver'],
                    'mountpoint': volume.attrs['Mountpoint'],
                    'labels': volume.attrs.get('Labels', {}),
                    'options': volume.attrs.get('Options', {}),
                    'scope': volume.attrs.get('Scope', 'local'),
                }
                
                # Add created_at if available
                if 'CreatedAt' in volume.attrs:
                    volume_info['created_at'] = volume.attrs['CreatedAt']
                
                # Add usage data if available
                if 'UsageData' in volume.attrs:
                    volume_info['usage_data'] = volume.attrs['UsageData']
                
                volume_list.append(volume_info)
                
            except Exception as e:
                logger.warning(f"Error processing volume {volume.name}: {str(e)}")
                continue
        
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

@mcp.tool()
async def create_volume(
    name: Annotated[Optional[str], Field(
        None,
        description="Name of the volume. If not specified, Docker generates a name."
    )] = None,
    driver: Annotated[str, Field(
        "local",
        description="Name of the volume driver to use. Defaults to 'local'."
    )] = "local",
    driver_opts: Annotated[Dict[str, str], Field(
        default_factory=dict,
        description="Key-value mapping of driver options and values."
    )] = {},
    labels: Annotated[Dict[str, str], Field(
        default_factory=dict,
        description="Labels to set on the volume, as a key-value mapping."
    )] = {}
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
        ...     name="my-volume",
        ...     driver="local",
        ...     driver_opts={"type": "nfs", "o": "addr=10.0.0.1"},
        ...     labels={"environment": "production"}
        ... )
        {
            "status": "success",
            "volume": {
                "name": "my-volume",
                "driver": "local",
                "mountpoint": "/var/lib/docker/volumes/my-volume/_data",
                "labels": {"environment": "production"},
                "options": {"type": "nfs", "o": "addr=10.0.0.1"},
                "scope": "local"
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
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'name': name
        }
        
    except Exception as e:
        error_msg = f"Unexpected error creating volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }

@mcp.tool
async def inspect_volume(
    name: Annotated[str, Field(
        description="Name of the volume"
    )],
    size: Annotated[bool, Field(
        False,
        description="Calculate the size of the volume"
    )] = False
) -> Dict[str, Any]:
    """
    Inspect a Docker volume.
    
    This function retrieves detailed information about a Docker volume.
    
    Args:
        name: Name of the volume
        size: Calculate the size of the volume (may be slow for large volumes)
        
    Returns:
        Dictionary with the volume details
        
    Example:
        >>> await inspect_volume("my-volume", size=True)
        {
            "status": "success",
            "volume": {
                "name": "my-volume",
                "driver": "local",
                "mountpoint": "/var/lib/docker/volumes/my-volume/_data",
                "labels": {"environment": "production"},
                "options": {},
                "scope": "local",
                "created_at": "2023-01-01T12:00:00Z",
                "size": 1024,
                "size_human": "1.0 KB"
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
                'status': 'error',
                'error': f'Volume not found: {name}'
            }
        
        # Get detailed information
        volume.reload()
        
        # Prepare the response
        result = {
            'name': volume.name,
            'driver': volume.attrs['Driver'],
            'mountpoint': volume.attrs['Mountpoint'],
            'labels': volume.attrs.get('Labels', {}),
            'options': volume.attrs.get('Options', {}),
            'scope': volume.attrs.get('Scope', 'local'),
            'created_at': volume.attrs.get('CreatedAt')
        }
        
        # Calculate size if requested
        if size and 'Mountpoint' in volume.attrs:
            try:
                mountpoint = volume.attrs['Mountpoint']
                if os.path.exists(mountpoint):
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(mountpoint):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            try:
                                total_size += os.path.getsize(fp)
                            except OSError:
                                continue
                    
                    result['size'] = total_size
                    # Convert to human-readable format
                    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                        if total_size < 1024.0:
                            result['size_human'] = f"{total_size:.1f} {unit}"
                            break
                        total_size /= 1024.0
            except Exception as e:
                logger.warning(f"Error calculating volume size: {str(e)}")
        
        return {
            'status': 'success',
            'volume': result
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'name': name
        }
        
    except Exception as e:
        error_msg = f"Unexpected error inspecting volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }

@mcp.tool()
async def remove_volume(
    name: Annotated[str, Field(
        ...,
        description="Name of the volume to remove"
    )],
    force: Annotated[bool, Field(
        False,
        description="Force the removal of the volume even if it is in use"
    )] = False
) -> Dict[str, Any]:
    """
    Remove a Docker volume.
    
    This function removes a Docker volume. If the volume is in use by containers,
    the operation will fail unless force=True is specified.
    
    Args:
        name: Name of the volume
        force: Force the removal of the volume even if it is in use
        
    Returns:
        Dictionary with the removal result
        
    Example:
        >>> await remove_volume("my-volume", force=True)
        {
            "status": "success",
            "message": "Volume removed successfully",
            "name": "my-volume"
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
                'status': 'error',
                'error': f'Volume not found: {name}'
            }
        
        # Remove the volume
        volume.remove(force=force)
        
        return {
            'status': 'success',
            'message': 'Volume removed successfully',
            'name': name
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'name': name
        }
        
    except Exception as e:
        error_msg = f"Unexpected error removing volume: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }

@mcp.tool()
async def prune_volumes(
    filters: Annotated[Dict[str, str], Field(
        default_factory=dict,
        description="Filters to process on the prune (e.g., {'label': ['maintainer=admin']})"
    )] = {},
    dry_run: Annotated[bool, Field(
        False,
        description="If true, only show what would be deleted"
    )] = False
) -> Dict[str, Any]:
    """
    Remove unused Docker volumes.
    
    This function removes all unused volumes, or volumes matching the
    specified filters.
    
    Args:
        filters: Filters to process on the prune
        dry_run: If true, only show what would be deleted
        
    Returns:
        Dictionary with prune results
        
    Example:
        >>> await prune_volumes(filters={"label": ["maintainer=admin"]})
        {
            "status": "success",
            "volumes_deleted": [
                {
                    "deleted": "volume1",
                    "size": 1024
                },
                ...
            ],
            "space_reclaimed": 1048576,
            "message": "Pruned 2 volumes (1.0 MB)"
        }
    """
    try:
        if dry_run:
            # For dry run, we'll just list the volumes that would be removed
            client = docker.from_env()
            
            # Get all volumes
            volumes = client.volumes.list(filters=filters)
            
            # Filter for unused volumes
            unused_volumes = []
            for vol in volumes:
                try:
                    # A volume is considered unused if it has no containers
                    if not vol.attrs.get('UsageData', {}).get('RefCount', 0) > 0:
                        unused_volumes.append(vol)
                except Exception as e:
                    logger.warning(f"Error checking volume {vol.name}: {str(e)}")
            
            # Calculate total size
            total_size = 0
            for vol in unused_volumes:
                try:
                    mountpoint = vol.attrs.get('Mountpoint')
                    if mountpoint and os.path.exists(mountpoint):
                        for dirpath, dirnames, filenames in os.walk(mountpoint):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                try:
                                    total_size += os.path.getsize(fp)
                                except OSError:
                                    continue
                except Exception as e:
                    logger.warning(f"Error calculating size for volume {vol.name}: {str(e)}")
            
            return {
                'status': 'success',
                'dry_run': True,
                'volumes_that_would_be_deleted': [v.name for v in unused_volumes],
                'space_that_would_be_reclaimed': total_size,
                'count': len(unused_volumes),
                'message': f'Would remove {len(unused_volumes)} volumes ({total_size/1024/1024:.1f} MB)'
            }
        
        # Initialize Docker client
        client = docker.from_env()
        
        # Prune volumes
        result = client.volumes.prune(filters=filters)
        
        # Process the result
        volumes_deleted = result.get('VolumesDeleted', [])
        space_reclaimed = result.get('SpaceReclaimed', 0)
        
        # Convert to a more detailed format
        deleted_details = []
        for vol_name in volumes_deleted:
            try:
                vol = client.volumes.get(vol_name)
                deleted_details.append({
                    'deleted': vol_name,
                    'size': vol.attrs.get('UsageData', {}).get('Size', 0)
                })
            except Exception as e:
                logger.warning(f"Error getting details for deleted volume {vol_name}: {str(e)}")
                deleted_details.append({'deleted': vol_name})
        
        return {
            'status': 'success',
            'volumes_deleted': deleted_details,
            'space_reclaimed': space_reclaimed,
            'count': len(volumes_deleted),
            'message': f'Pruned {len(volumes_deleted)} volumes ({space_reclaimed/1024/1024:.1f} MB)'
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error pruning volumes: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }
