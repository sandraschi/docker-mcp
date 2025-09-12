"""
Container lifecycle management for Docker MCP.

This module provides tools for managing the complete lifecycle of Docker containers,
including creation, starting, stopping, restarting, and removal. It follows FastMCP 2.12+
standards for tool registration and error handling.
"""
from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any, Optional, TypeVar, Dict, List, Annotated

import docker
from docker.errors import DockerException, APIError, NotFound, ImageNotFound, ContainerError
from pydantic import BaseModel, Field, ConfigDict, field_validator, HttpUrl, AnyUrl
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

# Type variable for generic type hints
T = TypeVar('T', bound='BaseModel')

class ContainerAction(str, Enum):
    """Available container lifecycle actions."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    REMOVE = "remove"
    PAUSE = "pause"
    UNPAUSE = "unpause"

class ContainerLifecycleRequest(BaseModel):
    """Request model for container lifecycle operations."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "my-container",
                "action": "restart",
                "force": False,
                "timeout": 10,
                "remove_volumes": False
            }
        }
    )
    
    container_id: str = Field(
        ...,
        min_length=1,
        description="ID or name of the container"
    )
    action: ContainerAction = Field(
        ...,
        description=f"Action to perform on the container. Options: {', '.join([e.value for e in ContainerAction])}"
    )
    force: bool = Field(
        default=False,
        description="Force the action (e.g., force remove a running container)"
    )
    timeout: int = Field(
        default=10,
        ge=1,
        le=300,
        description="Timeout in seconds for stop/restart operations"
    )
    remove_volumes: bool = Field(
        default=False,
        description="Remove volumes when removing a container"
    )

class ContainerLifecycleResponse(BaseModel):
    """Response model for container lifecycle operations."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Container restarted successfully",
                "container_id": "a1b2c3d4e5f6",
                "action": "restart",
                "state": {
                    "status": "running",
                    "running": True,
                    "paused": False,
                    "restarting": False,
                    "started_at": "2023-01-01T12:00:00Z"
                }
            }
        }
    )
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable result message")
    container_id: str = Field(..., description="ID of the container")
    action: str = Field(..., description="Action that was performed")
    state: Optional[dict[str, Any]] = Field(
        default=None,
        description="Current container state (if available)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the operation failed"
    )

class ContainerLifecycleParams(BaseModel):
    """Parameters for container lifecycle operations."""
    container_id: str = Field(
        ...,
        description="ID or name of the container to manage"
    )
    action: str = Field(
        ...,
        description="Action to perform (start, stop, restart, remove, pause, unpause)",
        pattern="^(start|stop|restart|remove|pause|unpause)$"
    )
    force: bool = Field(
        False,
        description="Force the action (e.g., force remove a running container)"
    )
    timeout: int = Field(
        10,
        ge=1,
        le=300,
        description="Timeout in seconds for stop/restart operations"
    )
    remove_volumes: bool = Field(
        False,
        description="Remove volumes when removing a container"
    )

@mcp.tool(
    name="manage_container_lifecycle",
    description="Manage the lifecycle of a Docker container (start, stop, restart, remove, pause, unpause)"
)
async def manage_container_lifecycle(params: ContainerLifecycleParams) -> Dict[str, Any]:
    """
    Execute container lifecycle operations with comprehensive error handling.
    
    This function provides a unified interface for common container operations
    including start, stop, restart, pause, unpause, and remove. It handles
    error cases and returns a standardized response format.
    
    Args:
        params: ContainerLifecycleParams containing:
            - container_id: ID or name of the container
            - action: Action to perform (start, stop, restart, remove, pause, unpause)
            - force: Force the action (default: False)
            - timeout: Timeout in seconds (default: 10)
            - remove_volumes: Remove volumes when removing (default: False)
            
    Returns:
        Dict[str, Any] containing the operation result and container state
        
    Example:
        >>> from dockermcp.tools.containers.container_lifecycle import ContainerLifecycleParams
        >>> params = ContainerLifecycleParams(
        ...     container_id="my-container",
        ...     action="restart",
        ...     timeout=30
        ... )
        >>> await manage_container_lifecycle(params)
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the container
        container = client.containers.get(params.container_id)
        
        # Store initial state for response
        initial_state = container.attrs.get('State', {})
        
        # Execute the requested action
        if params.action == 'start':
            container.start()
            action_performed = 'started'
        elif params.action == 'stop':
            container.stop(timeout=params.timeout)
            action_performed = 'stopped'
        elif params.action == 'restart':
            container.restart(timeout=params.timeout)
            action_performed = 'restarted'
        elif params.action == 'pause':
            container.pause()
            action_performed = 'paused'
        elif params.action == 'unpause':
            container.unpause()
            action_performed = 'unpaused'
        elif params.action == 'remove':
            container.remove(force=params.force, v=params.remove_volumes)
            action_performed = 'removed'
        else:
            error_msg = f"Unsupported action: {params.action}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error": "UNSUPPORTED_ACTION"
            }
        
        # Get updated state (if container still exists)
        updated_state = {}
        if params.action != 'remove':
            container.reload()
            updated_state = container.attrs.get('State', {})
        
        # Build response
        response_data = {
            "container_id": params.container_id,
            "action": params.action,
            "state": updated_state or initial_state
        }
        
        return {
            "status": "success",
            "message": f"Container {params.container_id} {action_performed} successfully",
            "data": response_data
        }
        
    except NotFound as e:
        error_msg = f"Container not found: {params.container_id}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "container_id": params.container_id,
            "action": params.action
        }
    except (DockerException, APIError) as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "container_id": params.container_id,
            "action": params.action
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "container_id": params.container_id if 'params' in locals() else 'unknown',
            "action": params.action if 'params' in locals() else 'unknown'
        }
