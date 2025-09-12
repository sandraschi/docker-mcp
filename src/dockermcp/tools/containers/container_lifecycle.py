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
from typing import Any, Dict, List, Optional, Type, TypeVar

import docker
from docker.errors import DockerException, APIError, NotFound, ImageNotFound, ContainerError
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, ConfigDict, field_validator

from dockermcp.logging_config import logger

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
    state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Current container state (if available)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the operation failed"
    )

@Tool(
    name="manage_container_lifecycle",
    description="Manage container lifecycle operations (start, stop, restart, remove, pause, unpause)",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'action': {
                'type': 'string',
                'enum': [e.value for e in ContainerAction],
                'description': 'Action to perform on the container'
            },
            'force': {
                'type': 'boolean',
                'default': False,
                'description': 'Force the action (e.g., force remove a running container)'
            },
            'timeout': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 300,
                'default': 10,
                'description': 'Timeout in seconds for stop/restart operations'
            },
            'remove_volumes': {
                'type': 'boolean',
                'default': False,
                'description': 'Remove volumes when removing a container'
            }
        },
        'required': ['container_id', 'action']
    }
)
async def manage_container_lifecycle(
    container_id: str,
    action: str,
    force: bool = False,
    timeout: int = 10,
    remove_volumes: bool = False
) -> Dict[str, Any]:
    """
    Execute container lifecycle operations with comprehensive error handling.
    
    This function provides a unified interface for common container operations
    including start, stop, restart, pause, unpause, and remove. It handles
    error cases and returns a standardized response format.
    
    Args:
        container_id: ID or name of the container
        action: Action to perform (start, stop, restart, remove, pause, unpause)
        force: Force the action (e.g., force remove a running container)
        timeout: Timeout in seconds for stop/restart operations
        remove_volumes: Remove volumes when removing a container
        
    Returns:
        Dictionary with operation status and container state
        
    Example:
        >>> await manage_container_lifecycle(
        ...     container_id="my-container",
        ...     action="restart",
        ...     timeout=30
        ... )
        {
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
    """
    try:
        # Validate action
        try:
            action_enum = ContainerAction(action.lower())
        except ValueError:
            valid_actions = [e.value for e in ContainerAction]
            raise ValueError(f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}")
            
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "success": False,
                "message": f"Container not found: {container_id}",
                "container_id": container_id,
                "action": action,
                "error": "Container not found"
            }
            
        # Execute the requested action
        try:
            if action_enum == ContainerAction.START:
                container.start()
                message = f"Container {container_id} started successfully"
                
            elif action_enum == ContainerAction.STOP:
                container.stop(timeout=timeout)
                message = f"Container {container_id} stopped successfully"
                
            elif action_enum == ContainerAction.RESTART:
                container.restart(timeout=timeout)
                message = f"Container {container_id} restarted successfully"
                
            elif action_enum == ContainerAction.REMOVE:
                container.remove(force=force, v=remove_volumes)
                return {
                    "success": True,
                    "message": f"Container {container_id} removed successfully",
                    "container_id": container_id,
                    "action": action
                }
                
            elif action_enum == ContainerAction.PAUSE:
                container.pause()
                message = f"Container {container_id} paused successfully"
                
            elif action_enum == ContainerAction.UNPAUSE:
                container.unpause()
                message = f"Container {container_id} unpaused successfully"
                
            # Get updated container state
            container.reload()
            
            return {
                "success": True,
                "message": message,
                "container_id": container_id,
                "action": action,
                "state": container.attrs.get("State", {})
            }
            
        except (APIError, ContainerError) as e:
            error_msg = f"Failed to {action} container {container_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "container_id": container_id,
                "action": action,
                "error": str(e)
            }
            
    except Exception as e:
        error_msg = f"Unexpected error during container {action}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "container_id": container_id,
            "action": action,
            "error": str(e)
        }
