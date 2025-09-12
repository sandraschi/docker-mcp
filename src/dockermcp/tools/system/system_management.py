"""
Docker System Management for FastMCP 2.12+

This module provides comprehensive tools for managing the Docker system including:
- System-wide information and statistics
- Disk usage and cleanup
- Docker daemon configuration
- System events and logs
"""
from __future__ import annotations

import json
import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal

import docker
from docker.errors import (
    DockerException, APIError, NotFound, 
    ImageNotFound, ContainerError, InvalidArgument
)
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, validator, HttpUrl, AnyUrl, ByteSize

from dockermcp.logging_config import logger

class SystemInfo(BaseModel):
    """System information model."""
    docker_version: str = Field(..., description="Docker server version")
    api_version: str = Field(..., description="Docker API version")
    min_api_version: str = Field(..., description="Minimum API version supported by the server")
    git_commit: str = Field(..., description="Git commit of the source code used to build the Docker daemon")
    go_version: str = Field(..., description="Go version used to compile the Docker daemon")
    os: str = Field(..., description="Host operating system")
    arch: str = Field(..., description="CPU architecture")
    kernel_version: str = Field(..., description="Kernel version")
    containers_running: int = Field(..., description="Number of running containers")
    containers_paused: int = Field(..., description="Number of paused containers")
    containers_stopped: int = Field(..., description="Number of stopped containers")
    containers_total: int = Field(..., description="Total number of containers")
    images: int = Field(..., description="Number of images")
    n_cpu: int = Field(..., description="Number of CPUs available to the Docker daemon")
    mem_total: int = Field(..., description="Total memory available to the Docker daemon in bytes")
    server_version: str = Field(..., description="Docker server version")
    cluster_store: str = Field(..., description="Storage driver used for the cluster")
    cluster_advertise: str = Field(..., description="Network address advertised for clustering")
    default_runtime: str = Field(..., description="Default runtime configured")
    runtimes: Dict[str, Any] = Field(..., description="Available container runtimes")
    init_binary: str = Field(..., description="Path to the init binary")
    containerd_commit: Dict[str, str] = Field(..., description="Containerd commit information")
    runc_commit: Dict[str, str] = Field(..., description="Runc commit information")
    init_commit: Dict[str, str] = Field(..., description="Init commit information")
    security_options: List[str] = Field(..., description="List of security options")
    http_proxy: str = Field(..., description="HTTP proxy configured for the Docker daemon")
    https_proxy: str = Field(..., description="HTTPS proxy configured for the Docker daemon")
    no_proxy: str = Field(..., description="No proxy configured for the Docker daemon")
    name: str = Field(..., description="Name of the Docker host")
    server_errors: List[str] = Field(..., description="List of warnings/errors from the Docker daemon")
    client_version: str = Field(..., description="Docker client version")
    debug: bool = Field(..., description="Whether debug mode is enabled")
    experimental_build: bool = Field(..., description="Whether experimental features are enabled")
    build_version: str = Field(..., description="Docker build version")

class DiskUsageInfo(BaseModel):
    """Disk usage information model."""
    layers_size: int = Field(..., description="Total size of filesystem layers in bytes")
    images: List[Dict[str, Any]] = Field(..., description="List of images and their sizes")
    containers: List[Dict[str, Any]] = Field(..., description="List of containers and their sizes")
    volumes: List[Dict[str, Any]] = Field(..., description="List of volumes and their sizes")
    build_cache: List[Dict[str, Any]] = Field(..., description="List of build cache objects and their sizes")
    total_size: int = Field(..., description="Total disk space used by Docker in bytes")
    reclaimable_size: int = Field(..., description="Disk space that can be reclaimed in bytes")

class PruneResult(BaseModel):
    """Prune operation result model."""
    containers_deleted: List[str] = Field(..., description="List of deleted container IDs")
    containers_space_reclaimed: int = Field(..., description="Disk space reclaimed from deleted containers in bytes")
    images_deleted: List[str] = Field(..., description="List of deleted image IDs")
    images_space_reclaimed: int = Field(..., description="Disk space reclaimed from deleted images in bytes")
    networks_deleted: List[str] = Field(..., description="List of deleted network IDs")
    volumes_deleted: List[str] = Field(..., description="List of deleted volume names")
    volumes_space_reclaimed: int = Field(..., description="Disk space reclaimed from deleted volumes in bytes")
    build_cache_deleted: List[str] = Field(..., description="List of deleted build cache IDs")
    build_cache_space_reclaimed: int = Field(..., description="Disk space reclaimed from deleted build cache in bytes")
    total_space_reclaimed: int = Field(..., description="Total disk space reclaimed in bytes")

@Tool(
    name="get_system_info",
    description="Get detailed information about the Docker system",
    parameters={
        'type': 'object',
        'properties': {
            'include_disk_usage': {
                'type': 'boolean',
                'default': False,
                'description': 'Include disk usage information (may be slow)'
            }
        }
    }
)
async def get_system_info(include_disk_usage: bool = False) -> Dict[str, Any]:
    """
    Get detailed information about the Docker system.
    
    This function retrieves comprehensive information about the Docker system,
    including version information, container and image counts, system resources,
    and optionally disk usage.
    
    Args:
        include_disk_usage: Whether to include disk usage information (may be slow)
        
    Returns:
        Dictionary with system information
        
    Example:
        >>> await get_system_info(include_disk_usage=True)
        {
            "status": "success",
            "system_info": {
                "docker_version": "20.10.7",
                "api_version": "1.41",
                "min_api_version": "1.12",
                "os": "linux",
                "arch": "x86_64",
                "kernel_version": "5.10.25-linuxkit",
                "containers_running": 3,
                "containers_paused": 0,
                "containers_stopped": 2,
                "containers_total": 5,
                "images": 15,
                "n_cpu": 4,
                "mem_total": 17179869184,
                "disk_usage": {
                    "layers_size": 123456789,
                    "images": [...],
                    "containers": [...],
                    "volumes": [...],
                    "build_cache": [...],
                    "total_size": 987654321,
                    "reclaimable_size": 12345678
                }
            }
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get system-wide information
        info = client.info()
        
        # Prepare the response
        system_info = {
            'docker_version': info.get('ServerVersion', ''),
            'api_version': info.get('ServerAPIVersion', ''),
            'min_api_version': info.get('APIVersion', ''),
            'git_commit': info.get('GitCommit', ''),
            'go_version': info.get('GoVersion', ''),
            'os': info.get('OSType', ''),
            'arch': info.get('Architecture', ''),
            'kernel_version': info.get('KernelVersion', ''),
            'containers_running': info.get('ContainersRunning', 0),
            'containers_paused': info.get('ContainersPaused', 0),
            'containers_stopped': info.get('ContainersStopped', 0),
            'containers_total': info.get('Containers', 0),
            'images': info.get('Images', 0),
            'n_cpu': info.get('NCPU', 0),
            'mem_total': info.get('MemTotal', 0),
            'server_version': info.get('ServerVersion', ''),
            'cluster_store': info.get('ClusterStore', ''),
            'cluster_advertise': info.get('ClusterAdvertise', ''),
            'default_runtime': info.get('DefaultRuntime', ''),
            'runtimes': info.get('Runtimes', {}),
            'init_binary': info.get('InitBinary', ''),
            'containerd_commit': info.get('ContainerdCommit', {}),
            'runc_commit': info.get('RuncCommit', {}),
            'init_commit': info.get('InitCommit', {}),
            'security_options': info.get('SecurityOptions', []),
            'http_proxy': info.get('HTTPProxy', ''),
            'https_proxy': info.get('HTTPSProxy', ''),
            'no_proxy': info.get('NoProxy', ''),
            'name': info.get('Name', ''),
            'server_errors': info.get('ServerErrors', []),
            'client_version': client.version(api_version=False)['Version'],
            'debug': info.get('Debug', False),
            'experimental_build': info.get('ExperimentalBuild', False),
            'build_version': info.get('BuildTime', '')
        }
        
        # Include disk usage if requested
        if include_disk_usage:
            disk_usage = await get_disk_usage()
            if disk_usage['status'] == 'success':
                system_info['disk_usage'] = disk_usage['disk_usage']
        
        return {
            'status': 'success',
            'system_info': system_info
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
        error_msg = f"Unexpected error getting system info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="get_disk_usage",
    description="Get detailed disk usage information about Docker resources",
    parameters={
        'type': 'object',
        'properties': {
            'all': {
                'type': 'boolean',
                'default': False,
                'description': 'Show all disk usage, including unused data'
            },
            'type': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'enum': ['container', 'image', 'volume', 'build-cache']
                },
                'default': ['container', 'image', 'volume', 'build-cache'],
                'description': 'Filter by resource type'
            }
        }
    }
)
async def get_disk_usage(
    all: bool = False,
    type: List[str] = ['container', 'image', 'volume', 'build-cache']
) -> Dict[str, Any]:
    """
    Get detailed disk usage information about Docker resources.
    
    This function retrieves detailed information about disk usage by Docker,
    including space used by images, containers, volumes, and build cache.
    
    Args:
        all: Show all disk usage, including unused data
        type: Filter by resource type (container, image, volume, build-cache)
        
    Returns:
        Dictionary with disk usage information
        
    Example:
        >>> await get_disk_usage(type=["image", "volume"])
        {
            "status": "success",
            "disk_usage": {
                "layers_size": 123456789,
                "images": [
                    {
                        "id": "sha256:abc123...",
                        "repository": "nginx",
                        "tag": "latest",
                        "size": 12345678,
                        "shared_size": 1234567,
                        "containers": 2
                    },
                    ...
                ],
                "containers": [
                    {
                        "id": "a1b2c3d4...",
                        "name": "web",
                        "image": "nginx:latest",
                        "size_rw": 12345,
                        "size_root_fs": 123456
                    },
                    ...
                ],
                "volumes": [
                    {
                        "name": "my-volume",
                        "driver": "local",
                        "size": 10485760
                    },
                    ...
                ],
                "build_cache": [
                    {
                        "id": "abc123...",
                        "type": "exec.cachemount",
                        "description": "local",
                        "size": 1234567,
                        "created_at": "2023-01-01T12:00:00Z",
                        "last_used_at": "2023-01-02T12:00:00Z",
                        "usage_count": 5
                    },
                    ...
                ],
                "total_size": 987654321,
                "reclaimable_size": 12345678
            }
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get disk usage data
        disk_usage = client.df()
        
        # Prepare the response
        result = {
            'layers_size': disk_usage.get('LayersSize', 0),
            'images': [],
            'containers': [],
            'volumes': [],
            'build_cache': [],
            'total_size': 0,
            'reclaimable_size': 0
        }
        
        # Process images if requested
        if 'image' in type:
            for image in disk_usage.get('Images', []):
                try:
                    repo_tags = image.get('RepoTags', [])
                    repository = ''
                    tag = ''
                    if repo_tags and repo_tags[0] != '<none>:<none>':
                        repo_tag = repo_tags[0].split(':')
                        repository = repo_tag[0]
                        tag = repo_tag[1] if len(repo_tag) > 1 else 'latest'
                    
                    result['images'].append({
                        'id': image.get('Id', ''),
                        'repository': repository,
                        'tag': tag,
                        'size': image.get('Size', 0),
                        'shared_size': image.get('SharedSize', 0),
                        'containers': image.get('Containers', 0),
                        'created': image.get('Created', 0),
                        'virtual_size': image.get('VirtualSize', 0)
                    })
                except Exception as e:
                    logger.warning(f"Error processing image {image.get('Id', 'unknown')}: {str(e)}")
        
        # Process containers if requested
        if 'container' in type:
            for container in disk_usage.get('Containers', []):
                try:
                    result['containers'].append({
                        'id': container.get('Id', ''),
                        'name': container.get('Names', [''])[0].lstrip('/'),
                        'image': container.get('Image', ''),
                        'image_id': container.get('ImageID', ''),
                        'command': container.get('Command', ''),
                        'state': container.get('State', ''),
                        'status': container.get('Status', ''),
                        'size_rw': container.get('SizeRw', 0),
                        'size_root_fs': container.get('SizeRootFs', 0),
                        'created': container.get('Created', 0)
                    })
                except Exception as e:
                    logger.warning(f"Error processing container {container.get('Id', 'unknown')}: {str(e)}")
        
        # Process volumes if requested
        if 'volume' in type:
            for volume in disk_usage.get('Volumes', []):
                try:
                    result['volumes'].append({
                        'name': volume.get('Name', ''),
                        'driver': volume.get('Driver', ''),
                        'mountpoint': volume.get('Mountpoint', ''),
                        'size': volume.get('UsageData', {}).get('Size', 0),
                        'ref_count': volume.get('UsageData', {}).get('RefCount', 0)
                    })
                except Exception as e:
                    logger.warning(f"Error processing volume {volume.get('Name', 'unknown')}: {str(e)}")
        
        # Process build cache if requested (Docker 17.07+)
        if 'build-cache' in type and 'BuildCache' in disk_usage:
            for cache in disk_usage['BuildCache']:
                try:
                    result['build_cache'].append({
                        'id': cache.get('ID', ''),
                        'type': cache.get('Type', ''),
                        'description': cache.get('Description', ''),
                        'size': cache.get('Size', 0),
                        'created_at': cache.get('CreatedAt', ''),
                        'last_used_at': cache.get('LastUsedAt', ''),
                        'usage_count': cache.get('UsageCount', 0),
                        'shared': cache.get('Shared', False),
                        'in_use': cache.get('InUse', False)
                    })
                except Exception as e:
                    logger.warning(f"Error processing build cache {cache.get('ID', 'unknown')}: {str(e)}")
        
        # Calculate totals
        result['total_size'] = result['layers_size']
        result['reclaimable_size'] = 0
        
        # Add reclaimable space from dangling images
        for image in result['images']:
            if '<none>' in image.get('repository', '') or not image.get('repository'):
                result['reclaimable_size'] += image.get('size', 0)
        
        # Add reclaimable space from stopped containers
        for container in result['containers']:
            if container.get('state') in ('exited', 'dead'):
                result['reclaimable_size'] += container.get('size_root_fs', 0)
        
        # Add reclaimable space from unused volumes
        for volume in result['volumes']:
            if volume.get('ref_count', 0) == 0:
                result['reclaimable_size'] += volume.get('size', 0)
        
        # Add reclaimable space from build cache
        for cache in result['build_cache']:
            if not cache.get('in_use', True):
                result['reclaimable_size'] += cache.get('size', 0)
        
        return {
            'status': 'success',
            'disk_usage': result
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
        error_msg = f"Unexpected error getting disk usage: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="prune_system",
    description="Remove unused Docker data",
    parameters={
        'type': 'object',
        'properties': {
            'prune_volumes': {
                'type': 'boolean',
                'default': False,
                'description': 'Prune volumes as well as containers, networks, and images'
            },
            'prune_build_cache': {
                'type': 'boolean',
                'default': True,
                'description': 'Prune build cache'
            },
            'filters': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Filters to process on the prune (e.g., `{"until": ["24h"]}`)'
            },
            'dry_run': {
                'type': 'boolean',
                'default': False,
                'description': 'If true, only show what would be deleted'
            }
        }
    }
)
async def prune_system(
    prune_volumes: bool = False,
    prune_build_cache: bool = True,
    filters: Dict[str, str] = {},
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Remove unused Docker data (system prune).
    
    This function removes all stopped containers, unused networks,
    dangling images, and optionally volumes and build cache.
    
    Args:
        prune_volumes: Prune volumes as well as containers, networks, and images
        prune_build_cache: Prune build cache
        filters: Filters to process on the prune (e.g., `{"until": ["24h"]}`)
        dry_run: If true, only show what would be deleted
        
    Returns:
        Dictionary with prune results
        
    Example:
        >>> await prune_system(prune_volumes=True, filters={"until": ["24h"]})
        {
            "status": "success",
            "prune_result": {
                "containers_deleted": ["a1b2c3d4...", "b2c3d4e5..."],
                "containers_space_reclaimed": 12345678,
                "images_deleted": ["sha256:abc123...", "sha256:def456..."],
                "images_space_reclaimed": 23456789,
                "networks_deleted": ["net1", "net2"],
                "volumes_deleted": ["vol1", "vol2"],
                "volumes_space_reclaimed": 34567890,
                "build_cache_deleted": ["cache1", "cache2"],
                "build_cache_space_reclaimed": 1234567,
                "total_space_reclaimed": 70699924
            },
            "message": "Pruned 2 containers, 2 images, 2 networks, 2 volumes, and 2 build cache entries (67.4 MB total)"
        }
    """
    try:
        if dry_run:
            # For dry run, we'll just calculate what would be pruned
            client = docker.from_env()
            
            # Get current state
            containers = client.containers.list(all=True, filters={'status': 'exited'})
            images = client.images.list(filters={'dangling': True})
            networks = client.networks.list(ids=[])
            volumes = client.volumes.list(filters={'dangling': True}) if prune_volumes else []
            
            # Filter by time if specified
            if 'until' in filters:
                until_timestamp = datetime.now(timezone.utc).timestamp() - parse_duration(filters['until']).total_seconds()
                
                # Filter containers
                containers = [c for c in containers if 
                    datetime.fromisoformat(c.attrs['State']['FinishedAt'].replace('Z', '+00:00')).timestamp() < until_timestamp
                ]
                
                # Filter images (this is a simplification, as image timestamps aren't directly available)
                # We'll just take a subset for the dry run
                if len(images) > 0:
                    images = images[:max(1, len(images) // 2)]
            
            # Calculate space that would be reclaimed (this is an estimate)
            containers_space = len(containers) * 100000000  # ~100MB per container
            images_space = len(images) * 200000000  # ~200MB per image
            volumes_space = len(volumes) * 500000000  # ~500MB per volume
            build_cache_space = 100000000 if prune_build_cache else 0  # ~100MB
            
            total_space = containers_space + images_space + volumes_space + build_cache_space
            
            return {
                'status': 'success',
                'dry_run': True,
                'would_prune': {
                    'containers': [c.id[:12] for c in containers],
                    'containers_space': containers_space,
                    'images': [i.id for i in images],
                    'images_space': images_space,
                    'networks': [n.id[:12] for n in networks],
                    'volumes': [v.name for v in volumes] if prune_volumes else [],
                    'volumes_space': volumes_space if prune_volumes else 0,
                    'build_cache_space': build_cache_space if prune_build_cache else 0,
                    'total_space': total_space
                },
                'message': f'Would prune {len(containers)} containers, {len(images)} images, {len(networks)} networks, {len(volumes)} volumes, and {1 if prune_build_cache else 0} build cache entries ({total_space/1024/1024:.1f} MB total)'
            }
        
        # Initialize Docker client
        client = docker.from_env()
        
        # Prune containers
        containers_prune = client.containers.prune(filters=filters)
        
        # Prune images
        images_prune = client.images.prune(filters=filters)
        
        # Prune networks (no filters for networks in Docker API)
        networks_prune = client.networks.prune()
        
        # Prune volumes if requested
        volumes_prune = {'VolumesDeleted': [], 'SpaceReclaimed': 0}
        if prune_volumes:
            volumes_prune = client.volumes.prune(filters=filters)
        
        # Prune build cache if requested (Docker 17.07+)
        build_cache_prune = {'CachesDeleted': [], 'SpaceReclaimed': 0}
        if prune_build_cache and hasattr(client.api, 'prune_builds'):
            try:
                build_cache_prune = client.api.prune_builds(filters=filters)
            except (AttributeError, APIError):
                # Build cache pruning not supported
                pass
        
        # Prepare the response
        result = {
            'containers_deleted': containers_prune.get('ContainersDeleted', []),
            'containers_space_reclaimed': containers_prune.get('SpaceReclaimed', 0),
            'images_deleted': images_prune.get('ImagesDeleted', []),
            'images_space_reclaimed': images_prune.get('SpaceReclaimed', 0),
            'networks_deleted': networks_prune.get('NetworksDeleted', []),
            'volumes_deleted': volumes_prune.get('VolumesDeleted', []),
            'volumes_space_reclaimed': volumes_prune.get('SpaceReclaimed', 0),
            'build_cache_deleted': build_cache_prune.get('CachesDeleted', []),
            'build_cache_space_reclaimed': build_cache_prune.get('SpaceReclaimed', 0),
            'total_space_reclaimed': (
                containers_prune.get('SpaceReclaimed', 0) +
                images_prune.get('SpaceReclaimed', 0) +
                volumes_prune.get('SpaceReclaimed', 0) +
                build_cache_prune.get('SpaceReclaimed', 0)
            )
        }
        
        # Generate a human-readable message
        message_parts = []
        if result['containers_deleted']:
            message_parts.append(f"{len(result['containers_deleted'])} containers")
        if result['images_deleted']:
            message_parts.append(f"{len(result['images_deleted'])} images")
        if result['networks_deleted']:
            message_parts.append(f"{len(result['networks_deleted'])} networks")
        if result['volumes_deleted']:
            message_parts.append(f"{len(result['volumes_deleted'])} volumes")
        if result['build_cache_deleted']:
            message_parts.append(f"{len(result['build_cache_deleted'])} build cache entries")
        
        if not message_parts:
            message = "Nothing to prune"
        else:
            message = f"Pruned {', '.join(message_parts)} ({(result['total_space_reclaimed'] / 1024 / 1024):.1f} MB total)"
        
        return {
            'status': 'success',
            'prune_result': result,
            'message': message
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
        error_msg = f"Unexpected error pruning system: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

def parse_duration(duration_str: str) -> timedelta:
    """
    Parse a duration string into a timedelta.
    
    Args:
        duration_str: Duration string (e.g., '24h', '1d', '3600s')
        
    Returns:
        timedelta object representing the duration
    """
    # This is a simplified implementation
    # For a full implementation, consider using dateutil.parser or similar
    if not duration_str:
        return timedelta()
    
    # Handle simple formats
    if duration_str.endswith('s'):
        return timedelta(seconds=int(duration_str[:-1]))
    elif duration_str.endswith('m'):
        return timedelta(minutes=int(duration_str[:-1]))
    elif duration_str.endswith('h'):
        return timedelta(hours=int(duration_str[:-1]))
    elif duration_str.endswith('d'):
        return timedelta(days=int(duration_str[:-1]))
    elif duration_str.endswith('w'):
        return timedelta(weeks=int(duration_str[:-1]))
    else:
        # Default to seconds if no unit specified
        try:
            return timedelta(seconds=int(duration_str))
        except ValueError:
            raise ValueError(f"Invalid duration format: {duration_str}")
