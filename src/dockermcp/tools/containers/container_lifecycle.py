"""
Container lifecycle management for Docker MCP.

This module provides tools for managing the complete lifecycle of Docker containers,
including creation, starting, stopping, restarting, and removal. It is designed to
work with FastMCP 2.12+ and follows the project's coding standards.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, Optional, List, TypeVar, Type, cast
from enum import Enum

# Pydantic models
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Docker SDK
import aiodocker
from aiodocker.exceptions import DockerError

# FastMCP imports
from fastmcp.tools import tool as Tool
from fastmcp.exceptions import ToolError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Type variables
T = TypeVar('T', bound=BaseModel)

class ContainerAction(str, Enum):
    """
    Available container lifecycle actions.
    
    Attributes:
        START: Start a stopped container
        STOP: Stop a running container
        RESTART: Restart a container
        REMOVE: Remove a container
        PAUSE: Pause a running container
        UNPAUSE: Unpause a paused container
    """
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    REMOVE = "remove"
    PAUSE = "pause"
    UNPAUSE = "unpause"
    
    @classmethod
    def get_description(cls, action: 'ContainerAction') -> str:
        """Get a human-readable description of the action."""
        descriptions = {
            cls.START: "Start a stopped container",
            cls.STOP: "Stop a running container",
            cls.RESTART: "Restart a container",
            cls.REMOVE: "Remove a container",
            cls.PAUSE: "Pause a running container",
            cls.UNPAUSE: "Unpause a paused container"
        }
        return descriptions.get(action, f"Unknown action: {action}")

class ContainerLifecycleRequest(BaseModel):
    """
    Request model for container lifecycle operations.
    
    Attributes:
        container_id: ID or name of the container
        action: Action to perform on the container
        force: Force the action (e.g., force remove a running container)
        timeout: Timeout in seconds for stop/restart operations (1-300)
        remove_volumes: Remove volumes when removing a container
    """
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
    
    @field_validator('container_id')
    @classmethod
    def validate_container_id(cls, v: str) -> str:
        """Validate container ID is not empty."""
        if not v.strip():
            raise ValueError("Container ID cannot be empty")
        return v.strip()

class ContainerLifecycleResponse(BaseModel):
    """
    Response model for container lifecycle operations.
    
    Attributes:
        success: Whether the operation was successful
        message: Human-readable result message
        container_id: ID of the container
        action: Action that was performed
        state: Current container state (if available)
        error: Error message if the operation failed
    """
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

@Tool.register(
    name="manage_container_lifecycle",
    description="Execute container lifecycle operations (start, stop, restart, pause, unpause, remove)"
)
async def manage_container_lifecycle(request: ContainerLifecycleRequest) -> ContainerLifecycleResponse:
    """
    Execute container lifecycle operations.
    
    This function provides a unified interface for common container operations
    including start, stop, restart, pause, unpause, and remove. It handles
    error cases and returns a standardized response format.
    
    Args:
        request: ContainerLifecycleRequest with operation parameters
        
    Returns:
        ContainerLifecycleResponse with operation result and container state
        
    Raises:
        ToolError: If the operation fails or the container is not found
        
    Example:
        ```python
        # Restart a container with a 30-second timeout
        request = ContainerLifecycleRequest(
            container_id="my-container",
            action=ContainerAction.RESTART,
            timeout=30
        )
        response = await manage_container_lifecycle(request)
        ```
    """
    action = request.action
    container_id = request.container_id
    action_desc = ContainerAction.get_description(action)
    
    try:
        async with aiodocker.Docker() as docker_client:
            # Get container reference
            container = docker_client.containers.container(container_id)
            
            # Get current container state
            try:
                container_info = await container.show()
                current_state = container_info["State"]
            except aiodocker.DockerContainerError as e:
                if e.status == 404:
                    raise ToolError(f"Container {container_id} not found") from e
                raise
                
                # Execute the requested action
                if action == ContainerAction.START:
                    if current_state["Running"]:
                        message = f"Container {container_id} is already running"
                    else:
                        await container.start()
                        container_info = await container.show()
                        current_state = container_info["State"]
                        message = f"Started container {container_id}"
                
                elif action == ContainerAction.STOP:
                    if not current_state["Running"]:
                        message = f"Container {container_id} is not running"
                    else:
                        await container.stop(timeout=request.timeout)
                        container_info = await container.show()
                        current_state = container_info["State"]
                        message = f"Stopped container {container_id}"
                
                elif action == ContainerAction.RESTART:
                    await container.restart(timeout=request.timeout)
                    container_info = await container.show()
                    current_state = container_info["State"]
                    message = f"Restarted container {container_id}"
                
                elif action == ContainerAction.PAUSE:
                    if current_state["Paused"]:
                        message = f"Container {container_id} is already paused"
                    else:
                        await container.pause()
                        container_info = await container.show()
                        current_state = container_info["State"]
                        message = f"Paused container {container_id}"
                
                elif action == ContainerAction.UNPAUSE:
                    if not current_state["Paused"]:
                        message = f"Container {container_id} is not paused"
                    else:
                        await container.unpause()
                        container_info = await container.show()
                        current_state = container_info["State"]
                        message = f"Unpaused container {container_id}"
                
                elif action == ContainerAction.REMOVE:
                    if current_state.get("Running", False) and not request.force:
                        raise ToolError(
                            f"Cannot remove running container {container_id} without force=True"
                        )
                    await container.delete(v=request.remove_volumes, force=request.force)
                    return ContainerLifecycleResponse(
                        success=True,
                        message=f"Removed container {container_id}",
                        container_id=container_id,
                        action=action.value,
                        state={"status": "removed"}
                    )
                else:
                    raise ToolError(f"Unsupported container action: {action}")
                
                return ContainerLifecycleResponse(
                    success=True,
                    message=message,
                    container_id=container_id,
                    action=action.value,
                    state=current_state
                )
        
    except aiodocker.DockerContainerError as e:
        if e.status == 404:
            error_msg = f"Container {container_id} not found"
        else:
            error_msg = f"Container operation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
        
    except asyncio.TimeoutError as e:
        error_msg = (
            f"Timeout while {action}ing container {container_id} "
            f"(timeout: {request.timeout}s)"
        )
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
        
    except DockerError as e:
        error_msg = f"Docker error while {action}ing container {container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
        
    except Exception as e:
        error_msg = f"Unexpected error while {action}ing container {container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def get_tools() -> list[Tool]:
    """
    Get all tools defined in this module for registration with FastMCP.
    
    This function returns a list of Tool instances that should be registered
    with the FastMCP tool registry. Each tool is wrapped with the @Tool.register
    decorator to provide metadata and enable remote invocation.
    
    Returns:
        List of Tool instances to register with FastMCP
        
    Example:
        >>> from fastmcp.tools import Toolntainer_lifecycle': {...}}
    """
    # The manage_container_lifecycle function is already decorated with @Tool.register
    # so we just need to return it in a list
    return [manage_container_lifecycle]

