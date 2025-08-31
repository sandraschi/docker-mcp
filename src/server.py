#!/usr/bin/env python3
"""
Sandra's Docker MCP Server - Austrian Efficiency Edition
Built with FastMCP 2.11.3 - Comprehensive Docker operations + Workflow intelligence

Features:
- 25 bread-and-butter Docker operations (complete CRUD)
- 15 Austrian efficiency workflow tools (stack health, problem detection)
- DIY customization framework for forkers
- Vienna-specific intelligence for Sandra's environment
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Literal, TypedDict

import json
from fastmcp import FastMCP, Tool, ToolException, Param, Return
from .json_encoder import dumps as custom_dumps, loads as custom_loads
from pydantic import BaseModel, Field, field_validator, HttpUrl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our specialized modules
from docker_ops.containers import ContainerManager
from docker_ops.images import ImageManager
from docker_ops.networks import NetworkManager
from docker_ops.volumes import VolumeManager
from docker_ops.system import SystemManager
from workflow_intel.stack_health import StackHealthChecker
from workflow_intel.problem_detection import ProblemDetector
from workflow_intel.automation import AutomationManager
from workflow_intel.vienna_specific import ViennaEnvironment

# Import refactored tool modules
from dockermcp.tools.containers import (
    list_containers, get_container_info, create_container, 
    start_container, stop_container, restart_container, 
    remove_container, get_container_logs
)
from dockermcp.tools.containers.container_tools_registry import register_container_tools
from dockermcp.tools.images import (
    list_images, pull_image, tag_image
)
from dockermcp.tools.networks import (
    list_networks, create_network, remove_network
)
from dockermcp.tools.volumes import (
    list_volumes, create_volume, remove_volume
)
from dockermcp.tools.system import (
    system_info, get_docker_version, system_df, ping, 
    docker_auth, system_prune, system_events, system_data_usage
)
from dockermcp.tools.workflow import (
    create_workflow, execute_workflow, get_workflow_status,
    list_workflows, cancel_workflow
)

# Initialize FastMCP server with custom JSON encoder
mcp = FastMCP(
    name="Sandra's Docker MCP Server",
    version="2.11.3",
    description="Comprehensive Docker operations with Austrian efficiency",
    json_dumps=custom_dumps,
    json_loads=custom_loads
)

# Pydantic models for request/response validation
class ContainerInfo(TypedDict):
    id: str
    name: str
    status: str
    image: str
    created: str
    state: str
    ports: Dict[str, str]
    networks: List[str]

class ContainerResponse(BaseModel):
    success: bool
    message: str
    container: Optional[ContainerInfo] = None
    error: Optional[str] = None

class ListContainersRequest(BaseModel):
    all_states: bool = Field(
        default=True,
        description="Include stopped containers"
    )

class ContainerOperationRequest(BaseModel):
    container_name: str = Field(
        ...,
        description="Name or ID of the container"
    )

class CreateContainerRequest(BaseModel):
    image: str = Field(
        ...,
        description="Docker image name (e.g., 'nginx:latest')",
        json_schema_extra={"example": "nginx:latest"}
    )
    name: str = Field(
        ...,
        description="Container name"
    )
    ports: Dict[str, str] = Field(
        default_factory=dict,
        description="Port mappings {'container_port': 'host_port'}"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
    volumes: Dict[str, str] = Field(
        default_factory=dict,
        description="Volume mounts {'host_path': 'container_path'}"
    )
    network: Optional[str] = Field(
        None,
        description="Network to connect to"
    )

    @field_validator('image')
    def validate_image(cls, v):
        if not v or ':' not in v:
            raise ValueError("Image must be in format 'name:tag'")
        return v

# Initialize managers
container_mgr = ContainerManager()
image_mgr = ImageManager()
network_mgr = NetworkManager()
volume_mgr = VolumeManager()
system_mgr = SystemManager()
stack_health = StackHealthChecker()
problem_detector = ProblemDetector()
automation_mgr = AutomationManager()
vienna_env = ViennaEnvironment()

# Register all tools with the MCP instance
# Container tools
mcp.tool(list_containers)
mcp.tool(get_container_info)
mcp.tool(create_container)
mcp.tool(start_container)
mcp.tool(stop_container)
mcp.tool(restart_container)
mcp.tool(remove_container)
mcp.tool(get_container_logs)

# Image tools
mcp.tool(list_images)
mcp.tool(pull_image)
mcp.tool(tag_image)

# Network tools
mcp.tool(list_networks)
mcp.tool(create_network)
mcp.tool(remove_network)

# Volume tools
mcp.tool(list_volumes)
mcp.tool(create_volume)
mcp.tool(remove_volume)

# System tools
mcp.tool(system_info)
mcp.tool(get_docker_version)
mcp.tool(system_df)
mcp.tool(ping)
mcp.tool(docker_auth)
mcp.tool(system_prune)
mcp.tool(system_events)
mcp.tool(system_data_usage)

# Workflow tools
mcp.tool(create_workflow)
mcp.tool(execute_workflow)
mcp.tool(get_workflow_status)
mcp.tool(list_workflows)
mcp.tool(cancel_workflow)

# Error handling
def handle_error(error: Exception, context: str = "") -> Dict[str, Any]:
    """Handle errors consistently across all tools."""
    error_msg = f"Error in {context}: {str(error)}" if context else f"Error: {str(error)}"
    logger.error(error_msg, exc_info=True)
    return {
        "success": False,
        "error": error_msg,
        "error_type": error.__class__.__name__
    }

# ============================================================================
# PART 1: BREAD-AND-BUTTER DOCKER OPERATIONS
# Standard Docker CRUD operations - the foundation
# ============================================================================

# CONTAINER LIFECYCLE OPERATIONS
@mcp.tool(
    name="list_containers",
    description="List all Docker containers with status information"
)
async def list_containers(
    request: ListContainersRequest
) -> Dict[str, Any]:
    """
    List all Docker containers with status information.
    
    Args:
        request: ListContainersRequest containing filter parameters
        
    Returns:
        Dictionary with container list and summary statistics
        
    Example:
        {
            "success": true,
            "containers": [...],
            "total": 5,
            "running": 3,
            "stopped": 2
        }
    """
    try:
        result = container_mgr.list_containers(all_states=request.all_states)
        return {
            'success': True,
            'containers': result.get('containers', []),
            'total': result.get('total', 0),
            'running': result.get('running', 0),
            'stopped': result.get('stopped', 0)
        }
    except Exception as e:
        return handle_error(e, "list_containers")

@mcp.tool(
    name="get_container_info",
    description="Get detailed information about a specific container"
)
async def get_container_info(
    request: ContainerOperationRequest
) -> ContainerResponse:
    """
    Get detailed information about a specific container.
    
    Args:
        request: ContainerOperationRequest with container_name
        
    Returns:
        ContainerResponse with container details or error
        
    Example:
        {
            "success": true,
            "message": "Container info retrieved",
            "container": {
                "id": "abc123",
                "name": "my-container",
                "status": "running",
                "image": "nginx:latest",
                "created": "2023-01-01T00:00:00Z",
                "state": "running",
                "ports": {"80/tcp": "8080"},
                "networks": ["bridge"]
            }
        }
    """
    try:
        container_info = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.get_container_info(request.container_name)
        )
        return {
            "success": True,
            "message": "Container info retrieved",
            "container": container_info
        }
    except Exception as e:
        return handle_error(e, f"get_container_info for {request.container_name}")

@mcp.tool(
    name="create_container",
    description="Create a new Docker container from an image"
)
async def create_container(
    request: CreateContainerRequest
) -> ContainerResponse:
    """
    Create a new Docker container from an image with validation and error handling.
    
    Args:
        request: CreateContainerRequest with container configuration
        
    Returns:
        ContainerResponse with creation result or error
        
    Example:
        {
            "success": true,
            "message": "Container created successfully",
            "container": {
                "id": "abc123",
                "name": "my-container",
                "status": "created"
            }
        }
    """
    try:
        container_info = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: container_mgr.create_container(
                image=request.image,
                name=request.name,
                ports=request.ports,
                environment=request.environment,
                volumes=request.volumes,
                network=request.network
            )
        )
        return {
            "success": True,
            "message": "Container created successfully",
            "container": container_info
        }
    except Exception as e:
        return handle_error(e, f"create_container {request.name}")

class StartContainerRequest(ContainerOperationRequest):
    pass

@mcp.tool(
    name="start_container",
    description="Start a stopped Docker container"
)
async def start_container(
    request: StartContainerRequest
) -> ContainerResponse:
    """
    Start a stopped container.
    
    Args:
        request: StartContainerRequest with container_name
        
    Returns:
        ContainerResponse with start operation result
        
    Example:
        {
            "success": true,
            "message": "Container started successfully",
            "container": {
                "id": "abc123",
                "name": "my-container",
                "status": "running"
            }
        }
    """
    try:
        container_info = await container_mgr.start_container(request.container_name)
        return {
            "success": True,
            "message": "Container started successfully",
            "container": container_info
        }
    except Exception as e:
        return handle_error(e, f"start_container {request.container_name}")

class StopContainerRequest(ContainerOperationRequest):
    timeout: int = Field(
        default=10,
        ge=1,
        le=300,
        description="Seconds to wait before force killing the container"
    )

@mcp.tool(
    name="stop_container",
    description="Stop a running Docker container gracefully"
)
async def stop_container(
    request: StopContainerRequest
) -> ContainerResponse:
    """
    Stop a running container gracefully with a configurable timeout.
    
    Args:
        request: StopContainerRequest with container_name and timeout
        
    Returns:
        ContainerResponse with stop operation result
        
    Example:
        {
            "success": true,
            "message": "Container stopped successfully",
            "container": {
                "id": "abc123",
                "name": "my-container",
                "status": "exited"
            }
        }
    """
    try:
        container_info = await container_mgr.stop_container(
            request.container_name, 
            timeout=request.timeout
        )
        return {
            "success": True,
            "message": "Container stopped successfully",
            "container": container_info
        }
    except Exception as e:
        return handle_error(e, f"stop_container {request.container_name}")

@mcp.tool(
    name="restart_container",
    description="Restart a container (stop + start) with proper error handling"
)
async def restart_container(
    request: RestartContainerRequest
) -> ContainerResponse:
    """
    Restart a container with proper error handling and status reporting.
    
    Args:
        request: RestartContainerRequest with container_name and timeout
        
    Returns:
        ContainerResponse with restart operation result
        
    Example:
        {
            "success": true,
            "message": "Container restarted successfully",
            "container": {
                "id": "abc123",
                "name": "my-container",
                "status": "running"
            }
        }
    """
    try:
        # First stop the container
        stop_request = StopContainerRequest(
            container_name=request.container_name,
            timeout=request.timeout
        )
        stop_result = await stop_container(stop_request)
        
        if not stop_result.get('success'):
            return stop_result
            
        # Then start it again
        start_request = StartContainerRequest(
            container_name=request.container_name
        )
        start_result = await start_container(start_request)
        
        if start_result.get('success'):
            return {
                "success": True,
                "message": "Container restarted successfully",
                "container": start_result.get('container')
            }
        return start_result
        
    except Exception as e:
        return handle_error(e, f"restart_container {request.container_name}")

@mcp.tool(
    name="remove_container",
    description="Remove a Docker container"
)
async def remove_container(
    request: RemoveContainerRequest
) -> ContainerResponse:
    """
    Remove a container with optional force flag.
    
    Args:
        request: RemoveContainerRequest with container_name and force flag
        
    Returns:
        ContainerResponse with remove operation result
        
    Example:
        {
            "success": true,
            "message": "Container removed successfully",
            "container": {
                "id": "abc123",
                "name": "my-container",
                "status": "removed"
            }
        }
    """
    try:
        container_info = await container_mgr.remove_container(
            request.container_name, 
            force=request.force
        )
        return {
            "success": True,
            "message": "Container removed successfully",
            "container": container_info
        }
    except Exception as e:
        return handle_error(e, f"remove_container {request.container_name}")

@mcp.tool(
    name="get_container_logs",
    description="Get logs from a Docker container"
)
async def get_container_logs(
    request: GetContainerLogsRequest
) -> ContainerLogsResponse:
    """
    Get logs from a container with configurable options.
    
    Args:
        request: GetContainerLogsRequest with log retrieval parameters
        
    Returns:
        ContainerLogsResponse with logs and metadata
        
    Example:
        {
            "success": true,
            "message": "Logs retrieved successfully",
            "container": {
                "id": "abc123",
                "name": "my-container"
            },
            "logs": "[timestamp] Log line 1\n[timestamp] Log line 2",
            "lines": 2
        }
    """
    try:
        logs = await container_mgr.get_logs(
            container_name=request.container_name,
            lines=request.lines,
            follow=request.follow,
            timestamps=request.timestamps
        )
        return {
            "success": True,
            "message": "Logs retrieved successfully",
            "container": {
                "id": request.container_name.split(':')[0],
                "name": request.container_name
            },
            "logs": logs,
            "lines": request.lines
        }
    except Exception as e:
        return handle_error(e, f"get_container_logs {request.container_name}")

# ============================================================================
# IMAGE MANAGEMENT OPERATIONS
# ============================================================================

class ListImagesRequest(BaseModel):
    include_unused: bool = Field(
        default=True,
        description="Include images not used by any container"
    )

class ImageInfo(TypedDict):
    id: str
    tags: List[str]
    size: int
    created: str
    virtual_size: int
    used: bool

class ListImagesResponse(BaseModel):
    success: bool
    message: str
    images: List[ImageInfo]
    total_size: int
    total: int
    error: Optional[str] = None

@mcp.tool(
    name="list_images",
    description="List all Docker images with size and usage information"
)
async def list_images(
    request: ListImagesRequest
) -> ListImagesResponse:
    """
    List all Docker images with size and usage information.
    
    Args:
        request: ListImagesRequest with filter parameters
        
    Returns:
        ListImagesResponse with image list and statistics
        
    Example:
        {
            "success": true,
            "message": "Images listed successfully",
            "images": [
                {
                    "id": "sha256:abc123",
                    "tags": ["nginx:latest"],
                    "size": 1337000000,
                    "created": "2023-01-01T00:00:00Z",
                    "virtual_size": 1337000000,
                    "used": true
                }
            ],
            "total_size": 1337000000,
            "total": 1
        }
    """
    try:
        result = await image_mgr.list_images(include_unused=request.include_unused)
        return {
            'success': True,
            'message': 'Images listed successfully',
            'images': result.get('images', []),
            'total_size': result.get('total_size', 0),
            'total': result.get('total', 0)
        }
    except Exception as e:
        return handle_error(e, "list_images")

class PullImageRequest(BaseModel):
    image_name: str = Field(
        ...,
        description="Name of the image to pull (with or without tag)",
        json_schema_extra={"example": "nginx"}
    )
    tag: str = Field(
        default="latest",
        description="Image tag/version"
    )
    
    @field_validator('image_name')
    def validate_image_name(cls, v):
        if not v or '/' not in v.split(':')[0]:
            raise ValueError("Image name should include repository (e.g., 'library/nginx' or 'nginx')")
        return v

@mcp.tool(
    name="pull_image",
    description="Pull a Docker image from a registry"
)
async def pull_image(
    request: PullImageRequest
) -> ImageStatusResponse:
    """
    Pull a Docker image from a registry with progress tracking.
    
    Args:
        request: PullImageRequest with image_name and tag
        
    Returns:
        ImageStatusResponse with pull result and image details
        
    Example:
        {
            "success": true,
            "message": "Image pulled successfully",
            "image": {
                "id": "sha256:abc123",
                "tags": ["nginx:latest"],
                "status": "downloaded"
            }
        }
    """
    try:
        full_image = (
            request.image_name 
            if ':' in request.image_name 
            else f"{request.image_name}:{request.tag}"
        )
        result = await image_mgr.pull(full_image)
        return {
            'success': True,
            'message': 'Image pulled successfully',
            'image': result
        }
    except Exception as e:
        return handle_error(e, f"pull_image {request.image_name}:{request.tag}")

class TagImageRequest(BaseModel):
    source_image: str = Field(
        ...,
        description="Source image name or ID"
    )
    target_tag: str = Field(
        ...,
        description="New tag to apply (format: [registry/]repository:tag)",
        json_schema_extra={"example": "myregistry/nginx:1.23"}
    )
    
    @field_validator('target_tag')
    def validate_target_tag(cls, v):
        if ':' not in v:
            raise ValueError("Target tag must include a tag (e.g., 'repo:tag')")
        return v

@mcp.tool(
    name="tag_image",
    description="Tag a Docker image with a new name and tag"
)
async def tag_image(
    request: TagImageRequest
) -> ImageStatusResponse:
    """
    Tag a Docker image with a new name and tag.
    
    Args:
        request: TagImageRequest with source and target image details
        
    Returns:
        ImageStatusResponse with operation result and image info
        
    Example:
        {
            "success": true,
            "message": "Image tagged successfully",
            "image": {
                "id": "sha256:abc123",
                "tags": ["nginx:latest", "myrepo/nginx:1.23"],
                "source": "nginx:latest"
            }
        }
    """
    try:
        result = await image_mgr.tag(request.source_image, request.target_tag)
        return {
            'success': True,
            'message': 'Image tagged successfully',
            'image': result
        }
    except Exception as e:
        return handle_error(e, f"tag_image {request.source_image} as {request.target_tag}")

# ============================================================================
# NETWORK OPERATIONS
# ============================================================================

class NetworkInfo(TypedDict):
    id: str
    name: str
    driver: str
    scope: str
    ipam: Dict[str, Any]
    containers: List[Dict[str, str]]
    created: str
    labels: Dict[str, str]

class ListNetworksResponse(BaseModel):
    success: bool
    message: str
    networks: List[NetworkInfo]
    error: Optional[str] = None

@mcp.tool(
    name="list_networks",
    description="List all Docker networks with detailed information"
)
async def list_networks() -> ListNetworksResponse:
    """
    List all Docker networks with their configurations and connected containers.
    
    Returns:
        ListNetworksResponse with network details
        
    Example:
        {
            "success": true,
            "message": "Networks listed successfully",
            "networks": [
                {
                    "id": "abc123",
                    "name": "bridge",
                    "driver": "bridge",
                    "scope": "local",
                    "ipam": {"Driver": "default", "Config": [{"Subnet": "172.17.0.0/16"}]},
                    "containers": [{"name": "web", "ip": "172.17.0.2"}],
                    "created": "2023-01-01T00:00:00Z",
                    "labels": {"com.example.vendor": "ACME"}
                }
            ]
        }
    """
    try:
        networks = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: network_mgr.list_networks()
        )
        return {
            'success': True,
            'message': 'Networks listed successfully',
            'networks': networks
        }
    except Exception as e:
        return handle_error(e, "list_networks")

class CreateNetworkRequest(BaseModel):
    name: str = Field(
        ...,
        description="Name of the network to create",
        min_length=2,
        max_length=64,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
    )
    driver: str = Field(
        default="bridge",
        description="Network driver to use",
        enum=["bridge", "overlay", "host", "none", "macvlan", "ipvlan"]
    )
    check_duplicate: bool = Field(
        default=True,
        description="Check for networks with duplicate names"
    )
    internal: bool = Field(
        default=False,
        description="Restrict external access to the network"
    )
    attachable: bool = Field(
        default=False,
        description="Enable manual container attachment"
    )
    ipam: Optional[Dict[str, Any]] = Field(
        default=None,
        description="IPAM configuration"
    )

class NetworkResponse(BaseModel):
    success: bool
    message: str
    network: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool(
    name="create_network",
    description="Create a new Docker network with configurable options"
)
async def create_network(
    request: CreateNetworkRequest
) -> NetworkResponse:
    """
    Create a new Docker network with the specified configuration.
    
    Args:
        request: CreateNetworkRequest with network configuration
        
    Returns:
        NetworkResponse with creation result and network details
        
    Example:
        {
            "success": true,
            "message": "Network created successfully",
            "network": {
                "id": "abc123",
                "name": "my-network",
                "driver": "bridge",
                "scope": "local",
                "ipam": {"Driver": "default", "Config": [{"Subnet": "172.18.0.0/16"}]}
            }
        }
    """
    try:
        network_config = {
            'name': request.name,
            'driver': request.driver,
            'check_duplicate': request.check_duplicate,
            'internal': request.internal,
            'attachable': request.attachable,
            'ipam': request.ipam or {}
        }
        
        result = await network_mgr.create(**network_config)
        return {
            'success': True,
            'message': 'Network created successfully',
            'network': result
        }
    except Exception as e:
        return handle_error(e, f"create_network {request.name}")

class RemoveNetworkRequest(BaseModel):
    name: str = Field(
        ...,
        description="Name or ID of the network to remove"
    )
    force: bool = Field(
        default=False,
        description="Force removal of the network even if in use"
    )

@mcp.tool(
    name="remove_network",
    description="Remove a Docker network with optional force flag"
)
async def remove_network(
    request: RemoveNetworkRequest
) -> NetworkResponse:
    """
    Remove a Docker network, with an option to force removal.
    
    Args:
        request: RemoveNetworkRequest with network name and force flag
        
    Returns:
        NetworkResponse with removal result
        
    Example:
        {
            "success": true,
            "message": "Network removed successfully",
            "network": {
                "id": "abc123",
                "name": "my-network"
            }
        }
    """
    try:
        result = await network_mgr.remove(request.name, force=request.force)
        return {
            'success': True,
            'message': 'Network removed successfully',
            'network': result
        }
    except Exception as e:
        return handle_error(e, f"remove_network {request.name}")

# ============================================================================
# VOLUME OPERATIONS
# ============================================================================

class VolumeInfo(TypedDict):
    name: str
    driver: str
    mountpoint: str
    created: str
    scope: str
    labels: Dict[str, str]
    options: Dict[str, str]
    usage_data: Optional[Dict[str, Any]]

class ListVolumesResponse(BaseModel):
    success: bool
    message: str
    volumes: List[VolumeInfo]
    total_size: int
    error: Optional[str] = None

@mcp.tool(
    name="list_volumes",
    description="List all Docker volumes with detailed information"
)
async def list_volumes() -> ListVolumesResponse:
    """
    List all Docker volumes with their configurations and usage information.
    
    Returns:
        ListVolumesResponse with volume details and total size
        
    Example:
        {
            "success": true,
            "message": "Volumes listed successfully",
            "volumes": [
                {
                    "name": "my-volume",
                    "driver": "local",
                    "mountpoint": "/var/lib/docker/volumes/my-volume/_data",
                    "created": "2023-01-01T00:00:00Z",
                    "scope": "local",
                    "labels": {"com.example.vendor": "ACME"},
                    "options": {},
                    "usage_data": {"size": 1048576, "ref_count": 2}
                }
            ],
            "total_size": 1048576
        }
    """
    try:
        volumes = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: volume_mgr.list_volumes()
        )
        total_size = sum(v.get('usage_data', {}).get('size', 0) for v in volumes)
        return {
            'success': True,
            'message': 'Volumes listed successfully',
            'volumes': volumes,
            'total_size': total_size
        }
    except Exception as e:
        return handle_error(e, "list_volumes")

class CreateVolumeRequest(BaseModel):
    name: str = Field(
        ...,
        description="Name of the volume to create",
        min_length=2,
        max_length=255,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
    )
    driver: str = Field(
        default="local",
        description="Volume driver to use"
    )
    driver_opts: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to apply to the volume"
    )

class VolumeResponse(BaseModel):
    success: bool
    message: str
    volume: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool(
    name="create_volume",
    description="Create a new Docker volume with configurable options"
)
async def create_volume(
    request: CreateVolumeRequest
) -> VolumeResponse:
    """
    Create a new Docker volume with the specified configuration.
    
    Args:
        request: CreateVolumeRequest with volume configuration
        
    Returns:
        VolumeResponse with creation result and volume details
        
    Example:
        {
            "success": true,
            "message": "Volume created successfully",
            "volume": {
                "name": "my-volume",
                "driver": "local",
                "mountpoint": "/var/lib/docker/volumes/my-volume/_data",
                "labels": {"com.example.vendor": "ACME"},
                "options": {}
            }
        }
    """
    try:
        volume_config = {
            'name': request.name,
            'driver': request.driver,
            'driver_opts': request.driver_opts,
            'labels': request.labels
        }
        
        result = await volume_mgr.create(**volume_config)
        return {
            'success': True,
            'message': 'Volume created successfully',
            'volume': result
        }
    except Exception as e:
        return handle_error(e, f"create_volume {request.name}")

class RemoveVolumeRequest(BaseModel):
    name: str = Field(
        ...,
        description="Name of the volume to remove"
    )
    force: bool = Field(
        default=False,
        description="Force removal even if the volume is in use"
    )

@mcp.tool(
    name="remove_volume",
    description="Remove a Docker volume with optional force flag"
)
async def remove_volume(
    request: RemoveVolumeRequest
) -> VolumeResponse:
    """
    Remove a Docker volume, with an option to force removal.
    
    Args:
        request: RemoveVolumeRequest with volume name and force flag
        
    Returns:
        VolumeResponse with removal result and freed space
        
    Example:
        {
            "success": true,
            "message": "Volume removed successfully",
            "volume": {
                "name": "my-volume",
                "freed_space": 1048576
            }
        }
    """
    try:
        result = await volume_mgr.remove(request.name, force=request.force)
        return {
            'success': True,
            'message': 'Volume removed successfully',
            'volume': {
                'name': request.name,
                'freed_space': result.get('freed_space', 0)
            }
        }
    except Exception as e:
        return handle_error(e, f"remove_volume {request.name}")

# ============================================================================
# SYSTEM OPERATIONS
# ============================================================================

class SystemInfoResponse(BaseModel):
    success: bool
    message: str
    info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool(
    name="system_info",
    description="Get detailed Docker system information and resource usage"
)
async def system_info() -> SystemInfoResponse:
    """
    Get comprehensive Docker system information including version, containers,
    images, and resource usage statistics.
    
    Returns:
        SystemInfoResponse with detailed system information
        
    Example:
        {
            "success": true,
            "message": "System info retrieved successfully",
            "info": {
                "containers": 5,
                "containers_running": 3,
                "containers_paused": 1,
                "containers_stopped": 1,
                "images": 15,
                "driver": "overlay2",
                "system_time": "2023-01-01T12:00:00Z",
                "os_type": "linux",
                "architecture": "x86_64",
                "cpus": 8,
                "memory": 17179869184,
                "docker_root_dir": "/var/lib/docker"
            }
        }
    """
    try:
        info = await system_mgr.info()
        return {
            'success': True,
            'message': 'System info retrieved successfully',
            'info': info
        }
    except Exception as e:
        return handle_error(e, "system_info")

class DockerVersionResponse(BaseModel):
    success: bool
    message: str
    version: Optional[Dict[str, Any]] = None
    components: Optional[List[Dict[str, str]]] = None
    error: Optional[str] = None

@mcp.tool(
    name="docker_version",
    description="Get Docker version and component information"
)
async def docker_version() -> DockerVersionResponse:
    """
    Get detailed version information for Docker and its components.
    
    Returns:
        DockerVersionResponse with version details
        
    Example:
        {
            "success": true,
            "message": "Docker version info retrieved",
            "version": {
                "Version": "20.10.7",
                "ApiVersion": "1.41",
                "MinAPIVersion": "1.12",
                "GitCommit": "b0f5bc3",
                "GoVersion": "go1.13.15",
                "Os": "linux",
                "Arch": "amd64",
                "KernelVersion": "5.10.25-linuxkit",
                "BuildTime": "2021-06-02T11:54:58.000000000+00:00"
            },
            "components": [
                {"Name": "Engine", "Version": "20.10.7"},
                {"Name": "containerd", "Version": "1.4.6"},
                {"Name": "runc", "Version": "1.0.0-rc95"},
                {"Name": "docker-init", "Version": "0.19.0"}
            ]
        }
    """
    try:
        version_info = await system_mgr.version()
        return {
            'success': True,
            'message': 'Docker version info retrieved',
            'version': version_info.get('Version'),
            'components': version_info.get('Components', [])
        }
    except Exception as e:
        return handle_error(e, "docker_version")

class DiskUsageResponse(BaseModel):
    success: bool
    message: str
    total_space: int
    reclaimed_space: int
    details: Dict[str, Any]
    error: Optional[str] = None

@mcp.tool(
    name="docker_disk_usage",
    description="Get detailed Docker disk usage statistics"
)
async def docker_disk_usage() -> DiskUsageResponse:
    """
    Get detailed disk usage information for Docker resources including images,
    containers, volumes, and build cache.
    
    Returns:
        DiskUsageResponse with detailed disk usage information
        
    Example:
        {
            "success": true,
            "message": "Disk usage retrieved successfully",
            "total_space": 10737418240,
            "reclaimed_space": 2147483648,
            "details": {
                "images": [
                    {
                        "id": "sha256:abc123",
                        "repository": "nginx",
                        "tag": "latest",
                        "size": 1337000000,
                        "shared_size": 0,
                        "containers": 1
                    }
                ],
                "containers": [
                    {
                        "id": "abc123",
                        "name": "my-container",
                        "image": "nginx:latest",
                        "size_rw": 0,
                        "size_root_fs": 0,
                        "created": "2023-01-01T00:00:00Z"
                    }
                ],
                "volumes": [
                    {
                        "name": "my-volume",
                        "driver": "local",
                        "mountpoint": "/var/lib/docker/volumes/my-volume/_data",
                        "size": 1073741824
                    }
                ],
                "build_cache": {
                    "total_size": 0,
                    "reclaimable_size": 0
                }
            }
        }
    """
    try:
        usage = await system_mgr.disk_usage()
        return {
            'success': True,
            'message': 'Disk usage retrieved successfully',
            'total_space': usage.get('LayersSize', 0),
            'reclaimed_space': usage.get('ReclaimedSpace', 0),
            'details': {
                'images': usage.get('Images', []),
                'containers': usage.get('Containers', []),
                'volumes': usage.get('Volumes', []),
                'build_cache': usage.get('BuildCache', {})
            }
        }
    except Exception as e:
        return handle_error(e, "docker_disk_usage")

class SystemPruneRequest(BaseModel):
    volumes: bool = Field(
        default=False,
        description="Prune volumes (dangling only, use with caution)"
    )
    networks: bool = Field(
        default=False,
        description="Prune unused networks"
    )
    build_cache: bool = Field(
        default=True,
        description="Prune build cache"
    )
    force: bool = Field(
        default=False,
        description="Do not prompt for confirmation"
    )
    all: bool = Field(
        default=False,
        description="Remove all unused images not just dangling ones"
    )

class SystemPruneResponse(BaseModel):
    success: bool
    message: str
    reclaimed_space: int = 0
    details: Dict[str, Any] = {}
    error: Optional[str] = None

@mcp.tool(
    name="docker_system_prune",
    description="Clean up unused Docker resources and reclaim disk space"
)
async def docker_system_prune(
    request: SystemPruneRequest
) -> SystemPruneResponse:
    """
    Clean up unused Docker resources including containers, networks, volumes, and images.
    
    WARNING: This operation is destructive and cannot be undone. Use with caution.
    
    Args:
        request: SystemPruneRequest with pruning options
        
    Returns:
        SystemPruneResponse with cleanup results and reclaimed space
        
    Example:
        {
            "success": true,
            "message": "System pruned successfully",
            "reclaimed_space": 1073741824,
            "details": {
                "containers_deleted": ["abc123", "def456"],
                "images_deleted": ["sha256:abc123", "sha256:def456"],
                "networks_deleted": ["old_network"],
                "volumes_deleted": ["old_volume"],
                "build_cache_deleted": true
            }
        }
    """
    try:
        if not request.force:
            # In a real implementation, you might want to prompt for confirmation
            # For MCP, we'll just log a warning
            logger.warning("Prune operation requested without force flag")
        
        result = await system_mgr.prune(
            volumes=request.volumes,
            networks=request.networks,
            build_cache=request.build_cache,
            all=request.all,
            force=request.force
        )
        
        return {
            'success': True,
            'message': 'System pruned successfully',
            'reclaimed_space': result.get('reclaimed_space', 0),
            'details': result.get('details', {})
        }
    except Exception as e:
        return handle_error(e, "docker_system_prune")

# ============================================================================
# WORKFLOW INTELLIGENCE TOOLS
# Sandra's environment-specific smart tools with Austrian efficiency
# ============================================================================

class StackHealthResponse(BaseModel):
    success: bool
    message: str
    status: str = Field(..., description="Overall status (healthy, degraded, down)")
    components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Status of individual stack components"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Performance and resource metrics"
    )
    issues: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of detected issues with severity and details"
    )
    last_checked: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the last health check"
    )
    error: Optional[str] = None

@mcp.tool(
    name="check_veogen_stack",
    description="Comprehensive health check for the Veogen stack with dependency analysis"
)
async def check_veogen_stack() -> StackHealthResponse:
    """
    Perform a complete health check of the Veogen stack, including all dependent services.
    
    The Veogen stack consists of:
    - Backend API service
    - Redis cache
    - PostgreSQL database
    - Grafana monitoring
    - Node Exporter for system metrics
    
    Returns:
        StackHealthResponse with detailed status of all components
        
    Example:
        {
            "success": true,
            "message": "Veogen stack health check completed",
            "status": "healthy",
            "components": [
                {
                    "name": "veogen-backend",
                    "status": "running",
                    "health": "healthy",
                    "version": "1.2.3",
                    "uptime": "3d 5h 12m"
                },
                {
                    "name": "redis",
                    "status": "running",
                    "health": "healthy",
                    "memory_used": 256000000,
                    "connected_clients": 5
                }
            ],
            "metrics": {
                "response_time_ms": 45.2,
                "error_rate": 0.1,
                "memory_usage_percent": 62.5,
                "cpu_usage_percent": 32.1
            },
            "issues": [
                {
                    "severity": "warning",
                    "component": "postgres",
                    "message": "High connection count (95/100)",
                    "suggestion": "Consider increasing max_connections or optimizing queries"
                }
            ],
            "last_checked": "2023-01-01T12:00:00Z"
        }
    """
    try:
        stack_status = await asyncio.get_event_loop().run_in_executor(
            None,
            stack_health.check_veogen_stack
        )
        
        return {
            'success': True,
            'message': 'Veogen stack health check completed',
            'status': stack_status.get('status', 'unknown'),
            'components': stack_status.get('components', []),
            'metrics': stack_status.get('metrics', {}),
            'issues': stack_status.get('issues', []),
            'last_checked': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return handle_error(e, "check_veogen_stack")

class ProjectHealth(BaseModel):
    name: str
    status: str
    health: str
    version: Optional[str] = None
    uptime: Optional[str] = None
    issues: List[Dict[str, str]] = []

class MyAIHealthResponse(BaseModel):
    success: bool
    message: str
    projects: List[ProjectHealth] = []
    overall_status: str = Field(..., description="Aggregated health status across all projects")
    metrics: Dict[str, Any] = {}
    error: Optional[str] = None

@mcp.tool(
    name="check_myai_health",
    description="Comprehensive health check for all MyAI projects with restart loop detection"
)
async def check_myai_health() -> MyAIHealthResponse:
    """
    Perform health checks across all MyAI projects in the portfolio.
    
    Monitored projects include:
    - document-viewer: Document processing and viewing service
    - calibre-plus: Enhanced e-book management
    - bob-and-alice: Secure communication tools
    - Other AI-powered applications
    
    Returns:
        MyAIHealthResponse with detailed status of all projects
        
    Example:
        {
            "success": true,
            "message": "MyAI projects health check completed",
            "overall_status": "degraded",
            "projects": [
                {
                    "name": "document-viewer",
                    "status": "running",
                    "health": "healthy",
                    "version": "2.1.0",
                    "uptime": "2d 3h 45m",
                    "issues": []
                },
                {
                    "name": "calibre-plus",
                    "status": "running",
                    "health": "degraded",
                    "version": "1.5.2",
                    "uptime": "1h 23m",
                    "issues": [
                        {
                            "severity": "warning",
                            "message": "Restart detected in last hour",
                            "details": "Container restarted 3 times in the last hour"
                        }
                    ]
                }
            ],
            "metrics": {
                "total_projects": 5,
                "healthy_projects": 4,
                "degraded_projects": 1,
                "down_projects": 0,
                "avg_response_time_ms": 87.3
            }
        }
    """
    try:
        health_data = await asyncio.get_event_loop().run_in_executor(
            None,
            stack_health.check_myai_health
        )
        
        return {
            'success': True,
            'message': 'MyAI projects health check completed',
            'projects': health_data.get('projects', []),
            'overall_status': health_data.get('overall_status', 'unknown'),
            'metrics': health_data.get('metrics', {})
        }
    except Exception as e:
        return handle_error(e, "check_myai_health")

class ImmichComponentHealth(BaseModel):
    name: str
    type: str = Field(..., description="Service type (api, database, cache, ml)")
    status: str
    health: str
    version: Optional[str] = None
    resources: Dict[str, Any] = {}

class ImmichHealthResponse(BaseModel):
    success: bool
    message: str
    status: str = Field(..., description="Overall stack status (healthy, degraded, down)")
    components: List[ImmichComponentHealth] = []
    storage: Dict[str, Any] = {}
    performance: Dict[str, float] = {}
    error: Optional[str] = None

@mcp.tool(
    name="check_immich_stack",
    description="Comprehensive health check for the Immich photo management stack"
)
async def check_immich_stack() -> ImmichHealthResponse:
    """
    Perform a complete health check of the Immich photo management stack.
    
    The Immich stack includes:
    - Main API server
    - PostgreSQL database
    - Redis cache
    - Machine Learning services (face recognition, object detection)
    - Storage backends
    
    Returns:
        ImmichHealthResponse with detailed status of all components
        
    Example:
        {
            "success": true,
            "message": "Immich stack health check completed",
            "status": "healthy",
            "components": [
                {
                    "name": "immich-server",
                    "type": "api",
                    "status": "running",
                    "health": "healthy",
                    "version": "1.45.0",
                    "resources": {
                        "cpu_usage": 12.5,
                        "memory_usage": 512000000,
                        "active_sessions": 3
                    }
                },
                {
                    "name": "immich-postgres",
                    "type": "database",
                    "status": "running",
                    "health": "healthy",
                    "resources": {
                        "connections": 5,
                        "cache_hit_ratio": 0.98,
                        "transaction_rate": 42.1
                    }
                }
            ],
            "storage": {
                "total_photos": 1250,
                "total_videos": 45,
                "total_size_gb": 42.7,
                "storage_used_gb": 18.3,
                "storage_location": "/mnt/photos"
            },
            "performance": {
                "api_response_time_ms": 87.3,
                "face_recognition_time_ms": 125.4,
                "thumbnail_generation_time_ms": 32.1
            }
        }
    """
    try:
        stack_status = await asyncio.get_event_loop().run_in_executor(
            None,
            stack_health.check_immich_stack
        )
        
        return {
            'success': True,
            'message': 'Immich stack health check completed',
            'status': stack_status.get('status', 'unknown'),
            'components': stack_status.get('components', []),
            'storage': stack_status.get('storage', {}),
            'performance': stack_status.get('performance', {})
        }
    except Exception as e:
        return handle_error(e, "check_immich_stack")

# PROBLEM DETECTION & DIAGNOSIS
@mcp.tool()
async def find_restart_loops(threshold_minutes: int = 10) -> Dict[str, Any]:
    """
    Find containers stuck in restart loops with root cause analysis.
    Austrian efficiency: Don't just detect, understand WHY.
    
    Args:
        threshold_minutes: Time window for restart detection
        
    Returns:
        Restart loop analysis with suggested fixes
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: problem_detector.detect_restart_loops(threshold_minutes)
        )
    except Exception as e:
        logger.error(f"Error finding restart loops: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to find restart loops: {str(e)}"
        }

@mcp.tool()
async def check_frontend_health() -> Dict[str, Any]:
    """
    Sandra's insight: "frontends with no exposed ports" = broken.
    Find web frontends that should have ports but don't.
    
    Returns:
        Frontend health analysis with connectivity tests
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            problem_detector.check_frontend_health
        )
    except Exception as e:
        logger.error(f"Error checking frontend health: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to check frontend health: {str(e)}"
        }

@mcp.tool()
async def detect_dependency_issues() -> Dict[str, Any]:
    """
    Detect containers waiting for dependencies (databases, Redis, etc.)
    Focus on actual blocking relationships in Sandra's stacks.
    
    Returns:
        Dependency issue analysis with startup order recommendations
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            problem_detector.detect_dependency_issues
        )
    except Exception as e:
        logger.error(f"Error detecting dependency issues: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to detect dependency issues: {str(e)}"
        }

@mcp.tool()
async def find_missing_containers() -> Dict[str, Any]:
    """
    Detect expected containers that don't exist (like zen_goldstine).
    Knows Sandra's expected container ecosystem.
    
    Returns:
        Missing container report with recreation instructions
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            problem_detector.find_missing_containers
        )
    except Exception as e:
        logger.error(f"Error finding missing containers: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to find missing containers: {str(e)}"
        }

# INTELLIGENT AUTOMATION
@mcp.tool()
async def fix_restart_loops(container_name: str, strategy: str = "smart") -> Dict[str, Any]:
    """
    Actually fix restart loops, don't just report them.
    Strategies: restart_fresh, update_image, fix_dependencies, resource_adjust
    
    Args:
        container_name: Container with restart loop
        strategy: Fix strategy (smart, restart_fresh, update_image, fix_dependencies)
        
    Returns:
        Fix operation result with success/failure details
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: automation_mgr.fix_restart_loop(container_name, strategy)
        )
    except Exception as e:
        logger.error(f"Error fixing restart loop for {container_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to fix restart loop for {container_name}: {str(e)}"
        }

@mcp.tool()
async def smart_stack_restart(stack_name: str) -> Dict[str, Any]:
    """
    Restart stacks in proper dependency order.
    Knows: Veogen, Immich, MyAI dependency chains
    
    Args:
        stack_name: Stack to restart (veogen, immich, myai)
        
    Returns:
        Stack restart result with dependency coordination
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: automation_mgr.restart_stack(stack_name)
        )
    except Exception as e:
        logger.error(f"Error restarting stack {stack_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to restart stack {stack_name}: {str(e)}"
        }

@mcp.tool()
async def emergency_stack_recovery(stack_name: str) -> Dict[str, Any]:
    """
    Nuclear option: Complete stack recovery when everything is broken.
    One command for catastrophic failure recovery.
    
    Args:
        stack_name: Stack to recover (veogen, immich, myai)
        
    Returns:
        Emergency recovery result with rollback capability
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: automation_mgr.emergency_recovery(stack_name)
        )
    except Exception as e:
        logger.error(f"Error in emergency recovery for stack {stack_name}: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to perform emergency recovery for stack {stack_name}: {str(e)}"
        }

# SPECIALIZED RECOVERY
@mcp.tool()
async def zen_goldstine_recovery() -> Dict[str, Any]:
    """
    Specialized recovery for missing zen_goldstine (fetch MCP).
    Knows exactly how to recreate this critical container.
    
    Returns:
        zen_goldstine recovery result with MCP integration status
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            vienna_env.zen_goldstine_recovery
        )
    except Exception as e:
        logger.error(f"Error in zen_goldstine recovery: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to perform zen_goldstine recovery: {str(e)}"
        }

@mcp.tool()
async def find_zombie_images(age_threshold_days: int = 90) -> Dict[str, Any]:
    """
    Find old, unused images eating disk space.
    Sandra's insight: "weed out the year old zombies"
    
    Args:
        age_threshold_days: Age threshold for zombie detection
        
    Returns:
        Zombie image report with cleanup recommendations
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: problem_detector.find_zombie_images(age_threshold_days)
        )
    except Exception as e:
        logger.error(f"Error finding zombie images: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to find zombie images: {str(e)}"
        }

@mcp.tool()
async def maintenance_recommendations() -> Dict[str, Any]:
    """
    Proactive maintenance suggestions. Austrian efficiency.
    Prevent problems before they happen.
    
    Returns:
        Maintenance recommendations with priority levels
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None,
            vienna_env.maintenance_recommendations
        )
    except Exception as e:
        logger.error(f"Error getting maintenance recommendations: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get maintenance recommendations: {str(e)}"
        }

# ============================================================================
# SERVER STARTUP AND CONFIGURATION
# ============================================================================

def main():
    """
    Start Sandra's Docker MCP Server with Austrian efficiency.
    """
    logger.info("🚀 Starting Sandra's Docker MCP Server - Austrian Efficiency Edition")
    logger.info("📊 Features: 25 Docker CRUD + 15 Workflow Intelligence Tools")
    logger.info("🏛️ Vienna-specific environment optimization enabled")
    
    # Verify Docker is available
    try:
        result = subprocess.run(['docker', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error("❌ Docker not available or not running")
            sys.exit(1)
        logger.info("✅ Docker connection verified")
    except Exception as e:
        logger.error(f"❌ Docker verification failed: {e}")
        sys.exit(1)
    
    # Register container tools with detailed logging
    try:
        logger.info("🔄 Registering container tools...")
        register_container_tools(mcp)
        logger.info("✅ Container tools registered successfully")
    except Exception as e:
        logger.error(f"❌ Failed to register container tools: {e}")
        sys.exit(1)
    
    # Start the FastMCP server
    logger.info("🎯 Austrian efficiency: All systems operational")
    logger.info("🌐 Starting FastMCP server...")
    mcp.run(
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )

if __name__ == "__main__":
    main()
