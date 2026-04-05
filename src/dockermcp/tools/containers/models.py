"""
Container Models for DockerMCP

This module contains Pydantic models for container-related operations.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContainerState(StrEnum):
    """Possible container states."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"


class ContainerStatus(StrEnum):
    """Container status values."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"


class ContainerHealth(StrEnum):
    """Container health status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    NONE = "none"


class PortConfig(BaseModel):
    """Configuration for container port bindings."""
    host_ip: str | None = Field(
        None,
        description="The host IP address to bind the port to"
    )
    host_port: int | str | None = Field(
        None,
        description="The port on the host to bind to"
    )


class ContainerPorts(BaseModel):
    """Port bindings for container networking."""
    ports: dict[str, list[PortConfig] | None] = Field(
        default_factory=dict,
        description="Port bindings in the format {'container_port': [{'host_ip': '...', 'host_port': '...'}]}"
    )


class ContainerVolume(BaseModel):
    """Volume configuration for container mounts."""
    bind: str = Field(..., description="Path to mount the volume in the container")
    mode: str = Field("rw", description="Mount mode (ro/rw)")


class ContainerDevice(BaseModel):
    """Device mapping for container."""
    path_on_host: str = Field(..., description="Path to the device on the host")
    path_in_container: str = Field(..., description="Path to the device in the container")
    cgroup_permissions: str = Field("rwm", description="Cgroup permissions (e.g., 'rwm')")


class ContainerResources(BaseModel):
    """Resource limits and reservations for a container."""
    cpu_shares: int | None = Field(
        None,
        ge=2,
        le=262144,
        description="CPU shares (relative weight)"
    )
    memory: int | str | None = Field(
        None,
        description="Memory limit as an integer (bytes) or string (e.g., '512m', '1g')"
    )
    memory_swap: int | str | None = Field(
        None,
        description="Total memory limit (memory + swap), '-1' to disable swap"
    )
    cpuset_cpus: str | None = Field(
        None,
        description="CPUs in which to allow execution (0-3, 0,1)"
    )
    cpuset_mems: str | None = Field(
        None,
        description="Memory nodes (MEMs) in which to allow execution (0-3, 0,1)"
    )
    cpu_quota: int | None = Field(
        None,
        description="Microseconds of CPU time that the container can use in a quota period"
    )
    cpu_period: int | None = Field(
        None,
        description="The length of a CPU period in microseconds"
    )
    blkio_weight: int | None = Field(
        None,
        ge=10,
        le=1000,
        description="Block IO weight (relative weight)"
    )


class ContainerCreateRequest(BaseModel):
    """Request model for creating a container."""
    image: str = Field(..., description="Name of the image to use")
    name: str | None = Field(None, description="Name for the container")
    command: str | list[str] | None = Field(
        None,
        description="Command to run in the container"
    )
    entrypoint: str | list[str] | None = Field(
        None,
        description="Entrypoint for the container"
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set in the container"
    )
    ports: dict[str, int | str | list[PortConfig] | None] | None = Field(
        None,
        description="Port bindings in the format {'container_port': {'host_ip': '...', 'host_port': '...'}}"
    )
    volumes: dict[str, str | ContainerVolume] | None = Field(
        None,
        description="Volume bindings in the format {'host_path': 'container_path' or ContainerVolume}"
    )
    network: str | None = Field(
        None,
        description="Name of the network to connect the container to"
    )
    network_mode: str | None = Field(
        None,
        description="Network mode for the container (e.g., 'bridge', 'host', 'none')"
    )
    restart_policy: dict[str, str] | None = Field(
        None,
        description="Restart policy for the container"
    )
    resources: ContainerResources | None = Field(
        None,
        description="Resource limits and reservations"
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Labels to add to the container"
    )
    working_dir: str | None = Field(
        None,
        description="Working directory inside the container"
    )
    user: str | None = Field(
        None,
        description="Username or UID to run the container as"
    )
    tty: bool = Field(
        False,
        description="Allocate a pseudo-TTY"
    )
    stdin_open: bool = Field(
        False,
        description="Keep STDIN open even if not attached"
    )
    detach: bool = Field(
        True,
        description="Run container in the background and return immediately"
    )
    hostname: str | None = Field(
        None,
        description="Container hostname"
    )
    domainname: str | None = Field(
        None,
        description="Container domain name"
    )
    privileged: bool = Field(
        False,
        description="Give extended privileges to the container"
    )
    devices: list[ContainerDevice] | None = Field(
        None,
        description="Device mappings for the container"
    )
    cap_add: list[str] | None = Field(
        None,
        description="Add Linux capabilities"
    )
    cap_drop: list[str] | None = Field(
        None,
        description="Drop Linux capabilities"
    )
    security_opt: list[str] | None = Field(
        None,
        description="Security options"
    )
    extra_hosts: dict[str, str] | None = Field(
        None,
        description="Additional host-to-IP mappings"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "image": "nginx:latest",
                "name": "my-nginx",
                "ports": {"80/tcp": {"host_port": 8080}},
                "environment": {"ENV": "development"},
                "volumes": {"/host/path": "/container/path"},
                "network": "bridge"
            }
        }
    )


class ContainerSummary(BaseModel):
    """Summary information about a container."""
    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Image name and tag")
    command: str = Field(..., description="Command run in the container")
    created: datetime = Field(..., description="When the container was created")
    status: str = Field(..., description="Container status")
    state: str = Field(..., description="Container state")
    ports: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of port bindings"
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Container labels"
    )

    @classmethod
    def from_docker_container(cls, container) -> ContainerSummary:
        """Create a ContainerSummary from a Docker container object."""
        attrs = getattr(container, 'attrs', {})

        # Parse created timestamp
        created = attrs.get('Created')
        if created and isinstance(created, str):
            try:
                if '.' in created:
                    created = datetime.fromisoformat(created.split('.')[0])
                else:
                    created = datetime.fromisoformat(created)
            except (ValueError, TypeError):
                created = datetime.now()
        else:
            created = datetime.now()

        # Get container state
        state = attrs.get('State', {})
        status = state.get('Status', 'unknown')

        # Get ports
        ports = []
        if 'Ports' in attrs.get('NetworkSettings', {}):
            for port in attrs['NetworkSettings']['Ports']:
                port_info = {"PrivatePort": port.split('/')[0], "Type": port.split('/')[1]}
                if attrs['NetworkSettings']['Ports'][port]:
                    port_info["PublicPort"] = attrs['NetworkSettings']['Ports'][port][0]['HostPort']
                    port_info["IP"] = attrs['NetworkSettings']['Ports'][port][0]['HostIp']
                ports.append(port_info)

        return cls(
            id=container.id,
            name=container.name.lstrip('/'),  # Remove leading slash from name
            image=attrs.get('Config', {}).get('Image', ''),
            command=' '.join(attrs.get('Config', {}).get('Cmd', [])),
            created=created,
            status=status,
            state=state.get('Status', 'unknown'),
            ports=ports,
            labels=attrs.get('Config', {}).get('Labels', {})
        )


class ContainerInspectResponse(BaseModel):
    """Response model for container inspection."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    data: dict[str, Any] = Field(default_factory=dict, description="Detailed container information")
    error: str | None = Field(None, description="Error message if operation failed")

    @classmethod
    def success(cls, data: dict[str, Any], message: str = "Success") -> ContainerInspectResponse:
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            data=data
        )

    @classmethod
    def error(cls, error: str, message: str = "An error occurred") -> ContainerInspectResponse:
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            error=error,
            data={}
        )


class ContainerListResponse(BaseModel):
    """Response model for listing containers."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    data: list[ContainerSummary] = Field(default_factory=list, description="List of container summaries")
    count: int = Field(0, description="Number of containers returned")
    error: str | None = Field(None, description="Error message if operation failed")

    @classmethod
    def success(
        cls,
        data: list[ContainerSummary],
        message: str = "Success"
    ) -> ContainerListResponse:
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            data=data,
            count=len(data)
        )

    @classmethod
    def error(
        cls,
        error: str,
        message: str = "An error occurred"
    ) -> ContainerListResponse:
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            error=error,
            data=[],
            count=0
        )


class ContainerOperationResponse(BaseModel):
    """Generic response model for container operations."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    container_id: str | None = Field(None, description="ID of the affected container")
    error: str | None = Field(None, description="Error message if operation failed")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional operation data")

    @classmethod
    def success(
        cls,
        container_id: str,
        message: str = "Operation completed successfully",
        **data: Any
    ) -> ContainerOperationResponse:
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            container_id=container_id,
            data=data or {}
        )

    @classmethod
    def error(
        cls,
        error: str,
        container_id: str | None = None,
        message: str = "An error occurred",
        **data: Any
    ) -> ContainerOperationResponse:
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            container_id=container_id,
            error=error,
            data=data or {}
        )


class ContainerLogsResponse(BaseModel):
    """Response model for container logs."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    container_id: str = Field(..., description="ID of the container")
    logs: list[str] = Field(default_factory=list, description="List of log lines")
    error: str | None = Field(None, description="Error message if operation failed")

    @classmethod
    def success(
        cls,
        container_id: str,
        logs: list[str],
        message: str = "Successfully retrieved logs"
    ) -> ContainerLogsResponse:
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            container_id=container_id,
            logs=logs
        )

    @classmethod
    def error(
        cls,
        container_id: str,
        error: str,
        message: str = "Failed to retrieve logs"
    ) -> ContainerLogsResponse:
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            container_id=container_id,
            error=error,
            logs=[]
        )


class ContainerStatsResponse(BaseModel):
    """Response model for container statistics."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    container_id: str = Field(..., description="ID of the container")
    stats: dict[str, Any] = Field(default_factory=dict, description="Container statistics")
    error: str | None = Field(None, description="Error message if operation failed")

    @classmethod
    def success(
        cls,
        container_id: str,
        stats: dict[str, Any],
        message: str = "Successfully retrieved stats"
    ) -> ContainerStatsResponse:
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            container_id=container_id,
            stats=stats
        )

    @classmethod
    def error(
        cls,
        container_id: str,
        error: str,
        message: str = "Failed to retrieve stats"
    ) -> ContainerStatsResponse:
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            container_id=container_id,
            error=error,
            stats={}
        )


class ContainerExecResponse(BaseModel):
    """Response model for container exec operations."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    exec_id: str | None = Field(None, description="ID of the exec instance")
    container_id: str | None = Field(None, description="ID of the container")
    output: str | None = Field(None, description="Command output")
    exit_code: int | None = Field(None, description="Exit code of the command")
    error: str | None = Field(None, description="Error message if operation failed")

    @classmethod
    def success(
        cls,
        exec_id: str,
        container_id: str,
        output: str = "",
        exit_code: int = 0,
        message: str = "Command executed successfully"
    ) -> ContainerExecResponse:
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            exec_id=exec_id,
            container_id=container_id,
            output=output,
            exit_code=exit_code
        )

    @classmethod
    def error(
        cls,
        error: str,
        container_id: str | None = None,
        exec_id: str | None = None,
        message: str = "Failed to execute command"
    ) -> ContainerExecResponse:
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            error=error,
            container_id=container_id,
            exec_id=exec_id
        )


class ContainerFileResponse(BaseModel):
    """Response model for container file operations."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    container_id: str | None = Field(None, description="ID of the container")
    path: str | None = Field(None, description="File path in the container")
    data: dict[str, Any] = Field(default_factory=dict, description="File content or listing data")
    error: str | None = Field(None, description="Error message if operation failed")


class ContainerVolumeResponse(BaseModel):
    """Response model for container volume operations."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    container_id: str | None = Field(None, description="ID of the container")
    data: dict[str, Any] = Field(default_factory=dict, description="Volume or mount data")
    error: str | None = Field(None, description="Error message if operation failed")


class ContainerImageResponse(BaseModel):
    """Response model for container image operations."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    container_id: str | None = Field(None, description="ID of the container")
    data: dict[str, Any] = Field(default_factory=dict, description="Image or commit data")
    error: str | None = Field(None, description="Error message if operation failed")
