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

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

# Import all container management tools to register them
from .list_containers import list_containers
from .container_lifecycle import (
    create_container, 
    start_container, 
    stop_container,
    restart_container,
    pause_container,
    unpause_container,
    remove_container
)
from .container_inspect import inspect_container
from .container_logs import get_container_logs
from .container_exec import execute_in_container
from .container_stats import get_container_stats, stream_container_stats
from .container_files import (
    list_container_directory,
    read_container_file,
    write_container_file
)
from .container_network import (
    list_networks,
    create_network,
    remove_network,
    connect_container_to_network,
    disconnect_container_from_network
)
from .container_resources import (
    get_container_resources,
    update_container_resources,
    reset_container_resources
)
from .container_volumes import (
    list_volumes,
    create_volume,
    inspect_volume,
    remove_volume,
    prune_volumes
)
from .container_images import (
    list_images,
    pull_image,
    build_image,
    remove_image
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
    CREATE_NETWORK = "create_network"
    REMOVE_NETWORK = "remove_network"
    CONNECT_NETWORK = "connect_network"
    DISCONNECT_NETWORK = "disconnect_network"
    GET_RESOURCES = "get_resources"
    UPDATE_RESOURCES = "update_resources"
    RESET_RESOURCES = "reset_resources"
    LIST_VOLUMES = "list_volumes"
    CREATE_VOLUME = "create_volume"
    INSPECT_VOLUME = "inspect_volume"
    REMOVE_VOLUME = "remove_volume"
    PRUNE_VOLUMES = "prune_volumes"
    LIST_IMAGES = "list_images"
    PULL_IMAGE = "pull_image"
    BUILD_IMAGE = "build_image"
    REMOVE_IMAGE = "remove_image"


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
        ToolResponse[Dict[str, Any]]: Response containing the operation results
        
    Raises:
        ToolError: If there's an error processing the request
        
    Example:
        >>> response = await manage_container(ContainerRequest(
        ...     action="start",
        ...     container_id="my-container",
        ...     params={"wait": True, "timeout": 30}
        ... ))
        >>> if response.success:
        ...     print(f"Container started: {response.data['container_id']}")
    """
    try:
        # Route to the appropriate handler based on action
        if params.action == ContainerAction.CREATE:
            result = await create_container(params.params)
        elif params.action == ContainerAction.START:
            result = await start_container(params.container_id, **params.params)
        elif params.action == ContainerAction.STOP:
            result = await stop_container(params.container_id, **params.params)
        elif params.action == ContainerAction.RESTART:
            result = await restart_container(params.container_id, **params.params)
        elif params.action == ContainerAction.PAUSE:
            result = await pause_container(params.container_id, **params.params)
        elif params.action == ContainerAction.UNPAUSE:
            result = await unpause_container(params.container_id, **params.params)
        elif params.action == ContainerAction.REMOVE:
            result = await remove_container(params.container_id, **params.params)
        elif params.action == ContainerAction.INSPECT:
            result = await inspect_container(params.container_id, **params.params)
        elif params.action == ContainerAction.LOGS:
            result = await get_container_logs(params.container_id, **params.params)
        elif params.action == ContainerAction.EXEC:
            result = await execute_in_container(params.container_id, **params.params)
        elif params.action == ContainerAction.STATS:
            if params.params.get('stream', False):
                return await stream_container_stats(params.container_id, **params.params)
            else:
                result = await get_container_stats(params.container_id, **params.params)
        elif params.action == ContainerAction.LIST_FILES:
            result = await list_container_directory(params.container_id, **params.params)
        elif params.action == ContainerAction.READ_FILE:
            result = await read_container_file(params.container_id, **params.params)
        elif params.action == ContainerAction.WRITE_FILE:
            result = await write_container_file(params.container_id, **params.params)
        elif params.action == ContainerAction.LIST_NETWORKS:
            result = await list_networks(**params.params)
        elif params.action == ContainerAction.CREATE_NETWORK:
            result = await create_network(**params.params)
        elif params.action == ContainerAction.REMOVE_NETWORK:
            result = await remove_network(**params.params)
        elif params.action == ContainerAction.CONNECT_NETWORK:
            result = await connect_container_to_network(params.container_id, **params.params)
        elif params.action == ContainerAction.DISCONNECT_NETWORK:
            result = await disconnect_container_from_network(params.container_id, **params.params)
        elif params.action == ContainerAction.GET_RESOURCES:
            result = await get_container_resources(params.container_id, **params.params)
        elif params.action == ContainerAction.UPDATE_RESOURCES:
            result = await update_container_resources(params.container_id, **params.params)
        elif params.action == ContainerAction.RESET_RESOURCES:
            result = await reset_container_resources(params.container_id, **params.params)
        elif params.action == ContainerAction.LIST_VOLUMES:
            result = await list_volumes(**params.params)
        elif params.action == ContainerAction.CREATE_VOLUME:
            result = await create_volume(**params.params)
        elif params.action == ContainerAction.INSPECT_VOLUME:
            result = await inspect_volume(params.params.get('volume_id'), **params.params)
        elif params.action == ContainerAction.REMOVE_VOLUME:
            result = await remove_volume(params.params.get('volume_id'), **params.params)
        elif params.action == ContainerAction.PRUNE_VOLUMES:
            result = await prune_volumes(**params.params)
        elif params.action == ContainerAction.LIST_IMAGES:
            result = await list_images(**params.params)
        elif params.action == ContainerAction.PULL_IMAGE:
            result = await pull_image(**params.params)
        elif params.action == ContainerAction.BUILD_IMAGE:
            result = await build_image(**params.params)
        elif params.action == ContainerAction.REMOVE_IMAGE:
            result = await remove_image(params.params.get('image_id'), **params.params)
            image = params.get('image')
            if not image:
                raise ValueError("image is required in params for 'remove_image' action")
            result = await remove_image(**params)
        else:
            raise ValueError(f"Unsupported action: {action}")
        
        # Return the result with additional context
        response = {
            'status': 'success',
            'action': action,
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
            'action': action,
            'container_id': container_id
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'action': action,
            'container_id': container_id
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'action': action,
            'container_id': container_id
        }
        
    except Exception as e:
        error_msg = f"Unexpected error during container management: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'action': action,
            'container_id': container_id
        }
