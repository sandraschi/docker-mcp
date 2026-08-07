"""
Container Management for Docker MCP.

This module provides a unified interface for managing Docker containers,
including lifecycle operations, inspection, logs, execution, and more.
It follows FastMCP 2.13+ standards for tool registration and error handling.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from docker.errors import APIError, DockerException
from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, model_validator

from dockermcp.logging_config import logger

from .models import (
    ContainerExecResponse,
    ContainerFileResponse,
    ContainerImageResponse,
    ContainerInspectResponse,
    ContainerListResponse,
    ContainerLogsResponse,
    ContainerOperationResponse,
    ContainerStatsResponse,
    ContainerVolumeResponse,
)

# Initialize MCP instance
mcp = FastMCP("Docker MCP")


class ContainerAction(StrEnum):
    """Available container actions with metadata."""

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

    @property
    def requires_container_id(self) -> bool:
        """Check if this action requires a container_id."""
        return self not in [
            ContainerAction.LIST_VOLUMES,
            ContainerAction.CREATE_VOLUME,
            ContainerAction.LIST_IMAGES,
            ContainerAction.PULL_IMAGE,
            ContainerAction.BUILD_IMAGE,
        ]

    @property
    def is_read_only(self) -> bool:
        """Check if this is a read-only operation."""
        return self in [
            ContainerAction.INSPECT,
            ContainerAction.LOGS,
            ContainerAction.STATS,
            ContainerAction.LIST_FILES,
            ContainerAction.READ_FILE,
            ContainerAction.LIST_NETWORKS,
            ContainerAction.GET_RESOURCES,
            ContainerAction.INSPECT_VOLUME,
            ContainerAction.LIST_VOLUMES,
            ContainerAction.LIST_IMAGES,
        ]


class ContainerRequest(BaseModel):
    """
    Base model for container management requests with Pydantic v2 validation.

    Attributes:
        action: The action to perform on the container
        container_id: Optional container ID or name
        params: Dictionary of action-specific parameters
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"action": "start", "container_id": "my-container", "params": {"wait": True, "timeout": 30}},
                {
                    "action": "create",
                    "params": {
                        "image": "nginx:latest",
                        "name": "web-server",
                        "ports": {"80/tcp": 8080},
                        "environment": {"DEBUG": "true"},
                    },
                },
            ]
        }
    )

    action: ContainerAction = Field(..., description="Action to perform on the container")
    container_id: str | None = Field(None, description="Container ID or name (required for most actions)")
    params: dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")

    @model_validator(mode="after")
    def validate_container_id_required(self) -> ContainerRequest:
        """Validate that container_id is provided when required."""
        if self.action.requires_container_id and not self.container_id:
            raise ValueError(f"container_id is required for action: {self.action.value}")
        return self


@mcp.tool
async def manage_container(
    params: ContainerRequest,
) -> (
    ContainerOperationResponse
    | ContainerListResponse
    | ContainerInspectResponse
    | ContainerLogsResponse
    | ContainerStatsResponse
    | ContainerExecResponse
    | ContainerFileResponse
    | ContainerVolumeResponse
    | ContainerImageResponse
):
    """
    Unified interface for managing Docker containers and related resources.

    This function routes container management requests to the appropriate
    handler function based on the specified action, using Pydantic v2 models
    for request/response validation and serialization.

    Args:
        params: ContainerRequest containing:
            - action: The action to perform (e.g., 'start', 'stop', 'inspect')
            - container_id: Container ID or name (required for most actions)
            - params: Action-specific parameters

    Returns:
        One of the container response models based on the action type

    Raises:
        ToolError: If there's an error processing the request

    Example:
        >>> response = await manage_container(ContainerRequest(
        ...     action="start",
        ...     container_id="my-container",
        ...     params={"wait": True, "timeout": 30}
        ... ))
        >>> if response.status == 'success':
        ...     print(f"Container started: {response.container_id}")
    """
    try:
        action = params.action
        container_id = params.container_id

        # Route to the appropriate handler based on action
        if action in [
            ContainerAction.CREATE,
            ContainerAction.START,
            ContainerAction.STOP,
            ContainerAction.RESTART,
            ContainerAction.PAUSE,
            ContainerAction.UNPAUSE,
            ContainerAction.REMOVE,
        ]:
            from .container_lifecycle import ContainerLifecycleParams, manage_container_lifecycle

            return await manage_container_lifecycle(
                ContainerLifecycleParams(
                    container_id=container_id or "",
                    action=action.value,
                    force=bool(params.params.get("force", False)),
                    timeout=int(params.params.get("timeout", 10)),
                    remove_volumes=bool(params.params.get("remove_volumes", False)),
                )
            )

        elif action == ContainerAction.INSPECT:
            from .container_inspect import inspect_container

            return await inspect_container(container_id, **params.params)

        elif action == ContainerAction.LOGS:
            from .container_logs import get_container_logs

            return await get_container_logs(container_id, **params.params)

        elif action == ContainerAction.EXEC:
            from .container_exec import execute_in_container

            return await execute_in_container(container_id, **params.params)

        elif action == ContainerAction.STATS:
            from .container_stats import get_container_stats

            return await get_container_stats(container_id, **params.params)

        elif action == ContainerAction.LIST_FILES:
            from .container_files import list_container_directory

            return await list_container_directory(container_id, **params.params)

        elif action == ContainerAction.READ_FILE:
            from .container_files import read_container_file

            return await read_container_file(container_id, **params.params)

        elif action == ContainerAction.WRITE_FILE:
            from .container_files import write_container_file

            return await write_container_file(container_id, **params.params)

        elif action == ContainerAction.LIST_NETWORKS:
            from .container_network import list_networks

            return await list_networks(**params.params)

        elif action == ContainerAction.GET_RESOURCES:
            from .container_resources import get_container_resources

            return await get_container_resources(container_id, **params.params)

        elif action == ContainerAction.RESET_RESOURCES:
            from .container_resources import reset_container_resources

            return await reset_container_resources(container_id, **params.params)

        elif action == ContainerAction.LIST_VOLUMES:
            from .container_volumes import list_volumes

            return await list_volumes(**params.params)

        elif action == ContainerAction.CREATE_VOLUME:
            from .container_volumes import create_volume

            return await create_volume(**params.params)

        elif action == ContainerAction.INSPECT_VOLUME:
            from .container_volumes import inspect_volume

            return await inspect_volume(params.params.get("volume_name"))

        elif action == ContainerAction.LIST_IMAGES:
            from .container_images import list_images

            return await list_images(**params.params)

        elif action == ContainerAction.PULL_IMAGE:
            from .container_images import pull_image

            return await pull_image(params.params.get("image_name"), **params.params)

        elif action == ContainerAction.BUILD_IMAGE:
            from .container_images import build_image

            return await build_image(**params.params)

        else:
            error_msg = f"Unsupported action: {action}"
            logger.error(error_msg)
            return ContainerOperationResponse.error_response(
                container_id=container_id, error=error_msg, message=f"Unsupported action: {action}"
            )

    except (DockerException, APIError) as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg, exc_info=True)
        return ContainerOperationResponse.error_response(
            container_id=params.container_id, error=error_msg, message="Docker API error occurred"
        )

    except Exception as e:
        error_msg = f"Error managing container: {e!s}"
        logger.error(error_msg, exc_info=True)
        return ContainerOperationResponse.error_response(
            container_id=params.container_id, error=error_msg, message="An unexpected error occurred"
        )


# Register the tool with MCP
__all__ = ["ContainerAction", "ContainerRequest", "manage_container"]
