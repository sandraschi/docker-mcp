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
from typing import Any, Dict, List, Optional, Union, Literal

import docker
from docker.errors import DockerException, APIError, NotFound, ImageNotFound
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, validator, HttpUrl

from dockermcp.logging_config import logger

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
    """Base model for container management requests."""
    action: ContainerAction = Field(..., description="Action to perform on the container")
    container_id: Optional[str] = Field(None, description="Container ID or name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")

@Tool(
    name="manage_container",
    description="Manage Docker containers and related resources",
    parameters={
        'type': 'object',
        'properties': {
            'action': {
                'type': 'string',
                'enum': [action.value for action in ContainerAction],
                'description': 'Action to perform on the container or resource'
            },
            'container_id': {
                'type': 'string',
                'default': None,
                'description': 'Container ID or name (required for most actions)'
            },
            'params': {
                'type': 'object',
                'default': {},
                'description': 'Action-specific parameters'
            }
        },
        'required': ['action']
    }
)
async def manage_container(
    action: str,
    container_id: Optional[str] = None,
    params: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """
    Unified interface for managing Docker containers and related resources.
    
    This function routes container management requests to the appropriate
    handler function based on the specified action.
    
    Args:
        action: Action to perform (e.g., 'start', 'stop', 'inspect')
        container_id: Container ID or name (required for most actions)
        params: Action-specific parameters
        
    Returns:
        Dictionary with the operation results
        
    Example:
        >>> await manage_container(
        ...     action="start",
        ...     container_id="my-container",
        ...     params={"wait": True, "timeout": 30}
        ... )
        {
            "status": "success",
            "container_id": "my-container",
            "action": "start",
            "result": {"message": "Container started successfully"}
        }
    """
    try:
        # Convert action string to enum
        action_enum = ContainerAction(action)
        
        # Route to the appropriate handler based on the action
        if action_enum == ContainerAction.CREATE:
            result = await create_container(**params)
        elif action_enum == ContainerAction.START:
            if not container_id:
                raise ValueError("container_id is required for 'start' action")
            result = await start_container(container_id, **params)
        elif action_enum == ContainerAction.STOP:
            if not container_id:
                raise ValueError("container_id is required for 'stop' action")
            result = await stop_container(container_id, **params)
        elif action_enum == ContainerAction.RESTART:
            if not container_id:
                raise ValueError("container_id is required for 'restart' action")
            result = await restart_container(container_id, **params)
        elif action_enum == ContainerAction.PAUSE:
            if not container_id:
                raise ValueError("container_id is required for 'pause' action")
            result = await pause_container(container_id, **params)
        elif action_enum == ContainerAction.UNPAUSE:
            if not container_id:
                raise ValueError("container_id is required for 'unpause' action")
            result = await unpause_container(container_id, **params)
        elif action_enum == ContainerAction.REMOVE:
            if not container_id:
                raise ValueError("container_id is required for 'remove' action")
            result = await remove_container(container_id, **params)
        elif action_enum == ContainerAction.INSPECT:
            if not container_id:
                raise ValueError("container_id is required for 'inspect' action")
            result = await inspect_container(container_id, **params)
        elif action_enum == ContainerAction.LOGS:
            if not container_id:
                raise ValueError("container_id is required for 'logs' action")
            result = await get_container_logs(container_id, **params)
        elif action_enum == ContainerAction.EXEC:
            if not container_id:
                raise ValueError("container_id is required for 'exec' action")
            result = await execute_in_container(container_id, **params)
        elif action_enum == ContainerAction.STATS:
            if not container_id:
                raise ValueError("container_id is required for 'stats' action")
            if params.get('stream', False):
                result = await stream_container_stats(container_id, **params)
            else:
                result = await get_container_stats(container_id, **params)
        elif action_enum == ContainerAction.LIST_FILES:
            if not container_id:
                raise ValueError("container_id is required for 'list_files' action")
            result = await list_container_directory(container_id, **params)
        elif action_enum == ContainerAction.READ_FILE:
            if not container_id:
                raise ValueError("container_id is required for 'read_file' action")
            result = await read_container_file(container_id, **params)
        elif action_enum == ContainerAction.WRITE_FILE:
            if not container_id:
                raise ValueError("container_id is required for 'write_file' action")
            result = await write_container_file(container_id, **params)
        elif action_enum == ContainerAction.LIST_NETWORKS:
            result = await list_networks(**params)
        elif action_enum == ContainerAction.CREATE_NETWORK:
            result = await create_network(**params)
        elif action_enum == ContainerAction.REMOVE_NETWORK:
            network_id = params.get('network_id')
            if not network_id:
                raise ValueError("network_id is required in params for 'remove_network' action")
            result = await remove_network(network_id, **params)
        elif action_enum == ContainerAction.CONNECT_NETWORK:
            if not container_id:
                raise ValueError("container_id is required for 'connect_network' action")
            network_id = params.get('network_id')
            if not network_id:
                raise ValueError("network_id is required in params for 'connect_network' action")
            result = await connect_container_to_network(container_id, network_id, **params)
        elif action_enum == ContainerAction.DISCONNECT_NETWORK:
            if not container_id:
                raise ValueError("container_id is required for 'disconnect_network' action")
            network_id = params.get('network_id')
            if not network_id:
                raise ValueError("network_id is required in params for 'disconnect_network' action")
            result = await disconnect_container_from_network(container_id, network_id, **params)
        elif action_enum == ContainerAction.GET_RESOURCES:
            if not container_id:
                raise ValueError("container_id is required for 'get_resources' action")
            result = await get_container_resources(container_id, **params)
        elif action_enum == ContainerAction.UPDATE_RESOURCES:
            if not container_id:
                raise ValueError("container_id is required for 'update_resources' action")
            result = await update_container_resources(container_id, **params)
        elif action_enum == ContainerAction.RESET_RESOURCES:
            if not container_id:
                raise ValueError("container_id is required for 'reset_resources' action")
            result = await reset_container_resources(container_id, **params)
        elif action_enum == ContainerAction.LIST_VOLUMES:
            result = await list_volumes(**params)
        elif action_enum == ContainerAction.CREATE_VOLUME:
            result = await create_volume(**params)
        elif action_enum == ContainerAction.INSPECT_VOLUME:
            volume_name = params.get('name')
            if not volume_name:
                raise ValueError("name is required in params for 'inspect_volume' action")
            result = await inspect_volume(volume_name, **params)
        elif action_enum == ContainerAction.REMOVE_VOLUME:
            volume_name = params.get('name')
            if not volume_name:
                raise ValueError("name is required in params for 'remove_volume' action")
            result = await remove_volume(volume_name, **params)
        elif action_enum == ContainerAction.PRUNE_VOLUMES:
            result = await prune_volumes(**params)
        elif action_enum == ContainerAction.LIST_IMAGES:
            result = await list_images(**params)
        elif action_enum == ContainerAction.PULL_IMAGE:
            repository = params.get('repository')
            if not repository:
                raise ValueError("repository is required in params for 'pull_image' action")
            result = await pull_image(**params)
        elif action_enum == ContainerAction.BUILD_IMAGE:
            path = params.get('path')
            if not path:
                raise ValueError("path is required in params for 'build_image' action")
            result = await build_image(**params)
        elif action_enum == ContainerAction.REMOVE_IMAGE:
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
