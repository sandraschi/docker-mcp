"""
Container lifecycle management for Docker MCP.

This module provides tools for managing the complete lifecycle of Docker containers,
including creation, starting, stopping, restarting, and removal. It follows FastMCP 2.12+
standards for tool registration and error handling.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypeVar

import docker
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

# Type variable for generic type hints
T = TypeVar("T", bound="BaseModel")


class ContainerAction(StrEnum):
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
                "remove_volumes": False,
            }
        }
    )

    container_id: str = Field(..., min_length=1, description="ID or name of the container")
    action: ContainerAction = Field(
        ..., description=f"Action to perform on the container. Options: {', '.join([e.value for e in ContainerAction])}"
    )
    force: bool = Field(default=False, description="Force the action (e.g., force remove a running container)")
    timeout: int = Field(default=10, ge=1, le=300, description="Timeout in seconds for stop/restart operations")
    remove_volumes: bool = Field(default=False, description="Remove volumes when removing a container")


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
                    "started_at": "2023-01-01T12:00:00Z",
                },
            }
        }
    )

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable result message")
    container_id: str = Field(..., description="ID of the container")
    action: str = Field(..., description="Action that was performed")
    state: dict[str, Any] | None = Field(default=None, description="Current container state (if available)")
    error: str | None = Field(default=None, description="Error message if the operation failed")


class ContainerLifecycleParams(BaseModel):
    """Parameters for container lifecycle operations."""

    container_id: str = Field(..., description="ID or name of the container to manage")
    action: str = Field(
        ...,
        description="Action to perform (start, stop, restart, remove, pause, unpause)",
        pattern="^(start|stop|restart|remove|pause|unpause)$",
    )
    force: bool = Field(False, description="Force the action (e.g., force remove a running container)")
    timeout: int = Field(10, ge=1, le=300, description="Timeout in seconds for stop/restart operations")
    remove_volumes: bool = Field(False, description="Remove volumes when removing a container")


async def _manage_container_lifecycle_impl(params: ContainerLifecycleParams) -> dict[str, Any]:
    """
    Internal async implementation of container lifecycle management.
    """
    try:
        # Get Docker client
        client = docker.from_env()

        # Get the container
        try:
            container = client.containers.get(params.container_id)
        except docker.errors.NotFound:
            raise ToolError(f"Container {params.container_id} not found") from None

        # Execute the requested action
        if params.action == "start":
            container.start()
            message = f"Container {params.container_id} started successfully"

        elif params.action == "stop":
            container.stop(timeout=params.timeout)
            message = f"Container {params.container_id} stopped successfully"

        elif params.action == "restart":
            container.restart(timeout=params.timeout)
            message = f"Container {params.container_id} restarted successfully"

        elif params.action == "remove":
            container.remove(force=params.force, v=params.remove_volumes)
            message = f"Container {params.container_id} removed successfully"

        elif params.action == "pause":
            container.pause()
            message = f"Container {params.container_id} paused successfully"

        elif params.action == "unpause":
            container.unpause()
            message = f"Container {params.container_id} unpaused successfully"

        else:
            raise ValueError(f"Unsupported action: {params.action}")

        # Get container state if it still exists
        try:
            container.reload()
            state = {
                "status": container.status,
                "running": container.status == "running",
                "paused": container.status == "paused",
                "restarting": container.status == "restarting",
                "started_at": container.attrs["State"]["StartedAt"],
            }
        except (docker.errors.NotFound, docker.errors.APIError):
            # Container may have been removed
            state = None

        return {
            "success": True,
            "message": message,
            "container_id": params.container_id,
            "action": params.action,
            "state": state,
        }

    except docker.errors.APIError as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
    except Exception as e:
        error_msg = f"Error managing container {params.container_id}: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


@mcp.tool
async def manage_container_lifecycle(params: ContainerLifecycleParams) -> dict[str, Any]:
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
    return await _manage_container_lifecycle_impl(params)
