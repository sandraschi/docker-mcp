"""
Container listing functionality for Docker MCP.

This module provides tools for listing Docker containers with various filtering options.
It follows FastMCP 2.12+ standards for tool registration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from docker.errors import DockerException
from pydantic import BaseModel, ConfigDict, Field

from dockermcp.docker_context import check_docker_available, docker_client
from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp


def created_iso(value: Any) -> str:
    """Normalize Docker Created values (unix timestamp or ISO string) to ISO-8601."""
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    return str(value)


def format_ports(attrs: dict[str, Any]) -> list[str]:
    """Render published ports from either list-API or inspect-API shapes."""
    out: list[str] = []
    ports = attrs.get("Ports")
    if isinstance(ports, list):
        for item in ports:
            if not isinstance(item, dict):
                continue
            priv = item.get("PrivatePort")
            if priv is None:
                continue
            pub = item.get("PublicPort")
            ip = item.get("IP") or "*"
            typ = item.get("Type") or "tcp"
            if pub:
                out.append(f"{ip}:{pub}->{priv}/{typ}")
            else:
                out.append(f"{priv}/{typ}")
        return out

    ns_ports = (attrs.get("NetworkSettings") or {}).get("Ports") or {}
    if isinstance(ns_ports, dict):
        for key, bindings in ns_ports.items():
            if not bindings:
                out.append(str(key))
                continue
            for binding in bindings:
                if not isinstance(binding, dict):
                    continue
                hip = binding.get("HostIp") or "*"
                hp = binding.get("HostPort")
                out.append(f"{hip}:{hp}->{key}")
    return out


def container_row(container: Any) -> dict[str, Any]:
    """Build a list row from docker-py Container using list attrs only (no image inspect)."""
    attrs = container.attrs or {}
    labels = attrs.get("Labels") or (attrs.get("Config") or {}).get("Labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    labels = {str(k): str(v) for k, v in labels.items() if k is not None}

    image_name = attrs.get("Image") or (attrs.get("Config") or {}).get("Image") or attrs.get("ImageID", "") or "unknown"
    networks = list(((attrs.get("NetworkSettings") or {}).get("Networks") or {}).keys())
    command = attrs.get("Command")
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)

    names = attrs.get("Names") or [""]
    raw_name = getattr(container, "name", None) or names[0]
    name = str(raw_name).lstrip("/")

    raw_state = attrs.get("State")
    if isinstance(raw_state, dict):
        state = str(raw_state.get("Status") or getattr(container, "status", "") or "")
    else:
        state = str(raw_state or getattr(container, "status", "") or "")
    status = str(getattr(container, "status", None) or attrs.get("Status") or state)

    return ContainerInfo(
        id=container.id,
        name=name,
        status=status,
        image=str(image_name),
        created=created_iso(attrs.get("Created", "")),
        state=state,
        labels=labels,
        ports=format_ports(attrs),
        compose_project=labels.get("com.docker.compose.project"),
        compose_service=labels.get("com.docker.compose.service"),
        networks=networks,
        command=str(command) if command else None,
    ).model_dump()


class ContainerInfo(BaseModel):
    """Information about a Docker container."""

    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    status: str = Field(..., description="Container status")
    image: str = Field(..., description="Container image")
    created: str = Field(..., description="Creation timestamp")
    state: str = Field(..., description="Container state")
    labels: dict[str, str] = Field(default_factory=dict, description="Container labels")
    ports: list[str] = Field(default_factory=list, description="Published host port mappings")
    compose_project: str | None = Field(default=None, description="Compose project label if present")
    compose_service: str | None = Field(default=None, description="Compose service label if present")
    networks: list[str] = Field(default_factory=list, description="Attached network names")
    command: str | None = Field(default=None, description="Container command")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "abc123",
                "name": "my-container",
                "status": "running",
                "image": "alpine:latest",
                "created": "2023-01-01T00:00:00Z",
                "state": "running",
                "labels": {"com.example.key": "value"},
                "ports": ["0.0.0.0:8080->80/tcp"],
                "compose_project": "stack",
                "compose_service": "web",
                "networks": ["bridge"],
                "command": "nginx -g daemon off;",
            }
        }
    )


class ListContainersParams(BaseModel):
    """Parameters for listing Docker containers."""

    all_states: bool = Field(True, description="If True, include stopped containers")
    filters: dict[str, str] | None = Field(None, description="Dictionary of filter key-value pairs")


@mcp.tool
@check_docker_available
async def list_containers(params: ListContainersParams) -> dict[str, Any]:
    """
    List Docker containers with optional filtering.

    Args:
        params: ListContainersParams containing:
            - all_states: If True, include stopped containers
            - filters: Dictionary of filter key-value pairs

    Returns:
        Dictionary containing:
            - status: "success" or "error"
            - message: Status message
            - containers: List of container information dictionaries
            - error: Error message if any

    Raises:
        ToolError: If there's an error communicating with the Docker daemon

    Example:
        >>> from dockermcp.tools.containers.list_containers import ListContainersParams
        >>> params = ListContainersParams(all_states=True, filters={"status": "running"})
        >>> await list_containers(params)
                }
            ]
        }
    """
    try:
        # Use shared client
        client = docker_client

        # Convert empty dict to None for Docker SDK
        filters = params.filters or {}
        if not filters:
            filters = None

        containers = client.containers.list(all=params.all_states, filters=filters)
        container_list = [container_row(container) for container in containers]
        return {"status": "success", "message": f"Found {len(container_list)} containers", "containers": container_list}

    except DockerException as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": "Failed to list containers", "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error listing containers: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": "Failed to list containers", "error": error_msg}
