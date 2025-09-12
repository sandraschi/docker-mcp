"""
Container lifecycle management for Docker MCP.

This module provides tools for managing the complete lifecycle of Docker containers,
including creation, starting, stopping, restarting, and removal. It is designed to
work with FastMCP 2.12+ and follows the project's coding standards.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
from functools import wraps
from typing import Dict, Any, Optional, List, TypeVar, Type, cast, Callable, Awaitable, TypeVar, ParamSpec
from enum import Enum
from contextlib import asynccontextmanager

# Pydantic models
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError

# Docker SDK
import aiodocker
import docker
from aiodocker.exceptions import DockerError
from docker.errors import APIError, NotFound, ImageNotFound, ContainerError

# FastMCP imports
from fastmcp.tools import tool, tool

# Import custom exceptions
from .container_models import ContainerError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Type variables for decorators
T = TypeVar('T', bound=BaseModel)
P = ParamSpec('P')
R = TypeVar('R')

def handle_docker_errors(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """
    Decorator to handle Docker API errors and standardize error responses.
    
    Args:
        func: The async function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except ValidationError as ve:
            error_msg = f"Container lifecycle validation error: {str(ve)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from ve
        except NotFound as nf:
            error_msg = f"Container not found: {str(nf)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from nf
        except ContainerError as ce:
            error_msg = f"Container error during {func.__name__}: {str(ce)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from ce
        except APIError as ae:
            error_msg = f"Docker API error in {func.__name__}: {str(ae)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from ae
        except DockerError as de:
            error_msg = f"Docker error in {func.__name__}: {str(de)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from de
        except asyncio.CancelledError:
            logger.info(f"{func.__name__} was cancelled")
            raise
        except Exception as e:
            error_msg = f"Unexpected error in {func.__name__}: {str(e)}"
            logger.error(f"{func.__name__} - {error_msg}\n{traceback.format_exc()}")
            raise ContainerError(f"Internal server error: {str(e)}") from e
    return wrapper

@asynccontextmanager
async def get_docker_client():
    """Context manager for Docker client with proper cleanup."""
    client = None
    try:
        client = docker.from_env()
        yield client
    except Exception as e:
        error_msg = f"Failed to initialize Docker client: {str(e)}"
        logger.error(error_msg)
        raise ContainerError(error_msg) from e
    finally:
        if client is not None:
            client.close()

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

@tool(
    name="manage_container_lifecycle",
    description="Execute container lifecycle operations (start, stop, restart, remove, etc.)",
    args_schema=ContainerLifecycleRequest,
    return_schema=ContainerLifecycleResponse
)
@handle_docker_errors
async def manage_container_lifecycle(request: ContainerLifecycleRequest) -> ContainerLifecycleResponse:
    """
    Execute container lifecycle operations with comprehensive error handling and logging.
    
    This function provides a unified interface for common container operations
    including start, stop, restart, pause, unpause, and remove. It handles
    error cases and returns a standardized response format.
    
    Args:
        request: ContainerLifecycleRequest with operation parameters
        
    Returns:
        ContainerLifecycleResponse with operation result and container state
        
    Raises:
        ToolException: If the operation fails or the container is not found
        
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
    logger.info(
        f"Processing {request.action} operation for container {request.container_id}"
        f" (force={request.force}, timeout={request.timeout}s)"
    )
    
    async with get_docker_client() as client:
        try:
            container = client.containers.get(request.container_id)
            logger.debug(f"Found container: {container.id} (status: {container.status})")
            
            # Execute the requested action
            result = await _execute_container_action(container, request)
            logger.info(
                f"Successfully completed {request.action} operation "
                f"for container {request.container_id}"
            )
            return result
            
        except docker.errors.NotFound:
            error_msg = f"Container {request.container_id} not found"
            logger.error(error_msg)
            return ContainerLifecycleResponse(
                success=False,
                message=error_msg,
                container_id=request.container_id,
                action=request.action.value,
                error=error_msg
            )
        except docker.errors.APIError as e:
            error_msg = f"Docker API error during {request.action}: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return ContainerLifecycleResponse(
                success=False,
                message=error_msg,
                container_id=request.container_id,
                action=request.action.value,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error during {request.action}: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return ContainerLifecycleResponse(
                success=False,
                message=error_msg,
                container_id=request.container_id,
                action=request.action.value,
                error=error_msg
            )
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
                    raise ToolException(f"Container {container_id} not found") from e
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
                        raise ToolException(
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
                    raise ToolException(f"Unsupported container action: {action}")
                
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
        raise ToolException(error_msg) from e
        
    except asyncio.TimeoutError as e:
        error_msg = (
            f"Timeout while {action}ing container {container_id} "
            f"(timeout: {request.timeout}s)"
        )
        logger.error(error_msg, exc_info=True)
        raise ToolException(error_msg) from e
        
    except DockerError as e:
        error_msg = f"Docker error while {action}ing container {container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolException(error_msg) from e
        
    except Exception as e:
        error_msg = f"Error during {action} operation: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise ToolException(error_msg) from e

def _create_success_response(
    container: docker.models.containers.Container,
    action: ContainerAction,
    message: str
) -> ContainerLifecycleResponse:
    """Create a success response with container state."""
    # Refresh container attributes to get current state
    container.reload()
    
    return ContainerLifecycleResponse(
        success=True,
        message=message,
        container_id=container.id,
        action=action.value,
        state={
            'status': container.status,
            'running': container.status == 'running',
            'paused': container.status == 'paused',
            'restarting': container.attrs.get('State', {}).get('Restarting', False),
            'started_at': container.attrs.get('State', {}).get('StartedAt'),
            'exit_code': container.attrs.get('State', {}).get('ExitCode')
        }
    )

def get_tools() -> List[Tool]:
    """
    Get all tools defined in this module for registration with FastMCP 2.12+.
    
    This function returns a list of tool functions that should be registered
    with the FastMCP tool registry. Each tool is decorated with @tool
    to provide metadata and enable remote invocation.
    
    Returns:
        List of tool functions to register with FastMCP
        
    Example:
        >>> from fastmcp.tools import tool
        >>> @tool()
        ... def my_tool():
        ...     pass
        >>> get_tools()
        [<function my_tool at 0x...>]
    """
    return [
        Tool(
            name="manage_container_lifecycle",
            func=manage_container_lifecycle,
            description=(
                "Manage container lifecycle operations. "
                "Supported actions: start, stop, restart, pause, unpause, remove. "
                "Includes comprehensive error handling and logging."
            ),
            args_schema=ContainerLifecycleRequest,
            return_schema=ContainerLifecycleResponse,
            examples=[
                {
                    "container_id": "my-container",
                    "action": "restart",
                    "timeout": 30,
                    "force": False
                },
                {
                    "container_id": "another-container",
                    "action": "stop",
                    "timeout": 10
                }
            ]
        )
    ]
