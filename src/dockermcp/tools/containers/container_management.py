"""
Container Management for Docker MCP.

This module provides a unified interface for managing Docker containers,
including lifecycle operations, inspection, logs, execution, and more.
It follows FastMCP 2.12+ standards for tool registration and error handling.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal, Type, TypeVar, cast, Generic

import docker
from docker.errors import DockerException, APIError, NotFound, ImageNotFound
from fastmcp.tools.tool import Tool
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, ConfigDict

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

# Import all container management tools to register them
from .list_containers import list_containers
from .container_lifecycle import manage_container_lifecycle
from .container_inspect import inspect_container
from .container_logs import get_container_logs
from .container_exec import execute_in_container
from .container_stats import get_container_stats
from .container_files import (
    list_container_directory,
    read_container_file,
    write_container_file
)
from .container_network import list_networks
from .container_resources import (
    get_container_resources,
    reset_container_resources
)
from .container_volumes import (
    list_volumes,
    create_volume,
    inspect_volume
)
from .container_images import (
    list_images,
    pull_image,
    build_image
)

class ContainerAction(str, Enum):
    """Available container actions."""
    CREATE = "create"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    UNPAUSE = "unpause"
    REMOVE = "remove"
    INSPECT = "inspect"
    LOGS = "logs"
    EXEC = "exec"
    STATS = "stats"
    LIST_FILES = "list_files"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    LIST_NETWORKS = "list_networks"
    GET_RESOURCES = "get_resources"
    RESET_RESOURCES = "reset_resources"
    LIST_VOLUMES = "list_volumes"
    CREATE_VOLUME = "create_volume"
    INSPECT_VOLUME = "inspect_volume"
    LIST_IMAGES = "list_images"
    PULL_IMAGE = "pull_image"
    BUILD_IMAGE = "build_image"


class ContainerRequest(BaseModel):
    """
    Base model for container management requests.
    
    Attributes:
        action: The action to perform on the container
        container_id: Optional container ID or name
        params: Dictionary of action-specific parameters
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action": "start",
                "container_id": "my-container",
                "params": {"wait": True, "timeout": 30}
            }
        }
    )
    
    action: ContainerAction = Field(
        ...,
        description="Action to perform on the container"
    )
    container_id: Optional[str] = Field(
        None,
        description="Container ID or name (required for most actions)"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters"
    )

@mcp.tool(
    name="manage_container",
    description="Manage Docker containers and related resources"
)
async def manage_container(params: ContainerRequest) -> Dict[str, Any]:
    """
    Unified interface for managing Docker containers and related resources.
    
    This function routes container management requests to the appropriate
    handler function based on the specified action.
    
    Args:
        params: ContainerRequest containing:
            - action: The action to perform (e.g., 'start', 'stop', 'inspect')
            - container_id: Container ID or name (required for most actions)
            - params: Action-specific parameters
            
    Returns:
        Dict[str, Any]: Response containing the operation results
        
    Raises:
        ToolError: If there's an error processing the request
        
    Example:
        >>> response = await manage_container(ContainerRequest(
        ...     action="start",
        ...     container_id="my-container",
        ...     params={"wait": True, "timeout": 30}
        ... ))
        >>> if response['status'] == 'success':
        ...     print(f"Container started: {response['container_id']}")
    """
    try:
        action = params.action
        container_id = params.container_id
        
        # Route to the appropriate handler based on action
        if action in [ContainerAction.CREATE, ContainerAction.START, ContainerAction.STOP, 
                     ContainerAction.RESTART, ContainerAction.PAUSE, ContainerAction.UNPAUSE, 
                     ContainerAction.REMOVE]:
            # Use container lifecycle management
            from .container_lifecycle import ContainerLifecycleParams
            lifecycle_params = ContainerLifecycleParams(
                container_id=container_id,
                action=action.value,
                **params.params
            )
            result = await manage_container_lifecycle(lifecycle_params)
            
        elif action == ContainerAction.INSPECT:
            from .container_inspect import ContainerInspectParams
            inspect_params = ContainerInspectParams(
                container_id=container_id,
                **params.params
            )
            result = await inspect_container(inspect_params)
            
        elif action == ContainerAction.LOGS:
            from .container_logs import ContainerLogsParams
            logs_params = ContainerLogsParams(
                container_id=container_id,
                **params.params
            )
            result = await get_container_logs(logs_params)
            
        elif action == ContainerAction.EXEC:
            from .container_exec import ExecuteInContainerParams
            exec_params = ExecuteInContainerParams(
                container_id=container_id,
                **params.params
            )
            result = await execute_in_container(exec_params)
            
        elif action == ContainerAction.STATS:
            from .container_stats import ContainerStatsParams
            stats_params = ContainerStatsParams(
                container_id=container_id,
                **params.params
            )
            result = await get_container_stats(stats_params)
            
        elif action == ContainerAction.LIST_FILES:
            from .container_files import ListDirectoryParams
            files_params = ListDirectoryParams(
                container_id=container_id,
                **params.params
            )
            result = await list_container_directory(files_params)
            
        elif action == ContainerAction.READ_FILE:
            from .container_files import ReadFileParams
            read_params = ReadFileParams(
                container_id=container_id,
                **params.params
            )
            result = await read_container_file(read_params)
            
        elif action == ContainerAction.WRITE_FILE:
            from .container_files import WriteFileParams
            write_params = WriteFileParams(
                container_id=container_id,
                **params.params
            )
            result = await write_container_file(write_params)
            
        elif action == ContainerAction.LIST_NETWORKS:
            from .container_network import ListNetworksParams
            network_params = ListNetworksParams(**params.params)
            result = await list_networks(network_params)
            
        elif action == ContainerAction.GET_RESOURCES:
            from .container_resources import GetContainerResourcesParams
            resources_params = GetContainerResourcesParams(
                container_id=container_id,
                **params.params
            )
            result = await get_container_resources(resources_params)
            
        elif action == ContainerAction.RESET_RESOURCES:
            from .container_resources import ResetContainerResourcesParams
            reset_params = ResetContainerResourcesParams(
                container_id=container_id,
                **params.params
            )
            result = await reset_container_resources(reset_params)
            
        elif action == ContainerAction.LIST_VOLUMES:
            from .container_volumes import ListVolumesParams
            volumes_params = ListVolumesParams(**params.params)
            result = await list_volumes(volumes_params)
            
        elif action == ContainerAction.CREATE_VOLUME:
            from .container_volumes import CreateVolumeParams
            create_vol_params = CreateVolumeParams(**params.params)
            result = await create_volume(create_vol_params)
            
        elif action == ContainerAction.INSPECT_VOLUME:
            from .container_volumes import InspectVolumeParams
            inspect_vol_params = InspectVolumeParams(**params.params)
            result = await inspect_volume(inspect_vol_params)
            
        elif action == ContainerAction.LIST_IMAGES:
            from .container_images import ListImagesParams
            images_params = ListImagesParams(**params.params)
            result = await list_images(images_params)
            
        elif action == ContainerAction.PULL_IMAGE:
            from .container_images import PullImageParams
            pull_params = PullImageParams(**params.params)
            result = await pull_image(pull_params)
            
        elif action == ContainerAction.BUILD_IMAGE:
            from .container_images import BuildImageParams
            build_params = BuildImageParams(**params.params)
            result = await build_image(build_params)
            
        else:
            raise ValueError(f"Unsupported action: {action}")
        
        # Return the result with additional context
        response = {
            'status': 'success',
            'action': action.value,
            'result': result
        }
        
        if container_id:
            response['container_id'] = container_id
            
        return response
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'action': action.value if 'action' in locals() else 'unknown',
            'container_id': container_id if 'container_id' in locals() else None
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'action': action.value if 'action' in locals() else 'unknown',
            'container_id': container_id if 'container_id' in locals() else None
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'action': action.value if 'action' in locals() else 'unknown',
            'container_id': container_id if 'container_id' in locals() else None
        }
        
    except Exception as e:
        error_msg = f"Unexpected error during container management: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'action': action.value if 'action' in locals() else 'unknown',
            'container_id': container_id if 'container_id' in locals() else None
        }
