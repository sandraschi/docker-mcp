"""
Container inspection tool for Docker MCP.

This module provides detailed inspection of Docker containers including
configuration, state, and resource usage statistics with comprehensive
error handling and logging. It follows FastMCP 2.12+ standards.
"""
from __future__ import annotations

import logging
from typing import Any, TypeVar

import docker
from docker.errors import APIError, DockerException, NotFound
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import logger directly to avoid circular imports
logger = logging.getLogger(__name__)

# Type variable for generic response
T = TypeVar('T')

# Constants
DEFAULT_LOG_TAIL = 100
MAX_LOG_LINES = 1000

def _calculate_cpu_percent(stats: dict[str, Any]) -> float:
    """Calculate CPU usage percentage from container stats.

    Args:
        stats: Raw container stats dictionary from Docker API

    Returns:
        CPU usage as a percentage (0-100) of total available CPU

    Note:
        This calculation follows the same approach as 'docker stats' command.
        It accounts for multiple CPU cores and system-wide CPU usage.
    """
    try:
        # Get CPU usage delta between current and previous measurement
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        # Get system CPU usage delta
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']

        if system_delta > 0 and cpu_delta > 0:
            # Get number of CPU cores (or 1 if not available)
            cpu_count = len(stats['cpu_stats']['cpu_usage'].get('percpu_usage') or [1])
            # Calculate percentage (scaled by number of CPUs)
            return (cpu_delta / system_delta) * cpu_count * 100.0

    except (KeyError, ZeroDivisionError) as e:
        logger.warning(f"Error calculating CPU percentage: {e}", exc_info=True)

    return 0.0


def _calculate_memory_usage(stats: dict[str, Any]) -> dict[str, int]:
    """Calculate memory usage from container stats.

    Args:
        stats: Raw container stats dictionary from Docker API

    Returns:
        Dictionary with memory usage information:
        - usage: Memory used in bytes
        - limit: Memory limit in bytes (0 if unlimited)
        - percent: Memory usage as a percentage of the limit (0-100)
    """
    try:
        memory_stats = stats.get('memory_stats', {})

        # Get memory usage (use 'usage' or 'rss' + 'cache' if available)
        usage = memory_stats.get('usage')
        if usage is None and 'rss' in memory_stats and 'cache' in memory_stats:
            usage = memory_stats['rss'] + memory_stats['cache']

        # Get memory limit (or 0 if unlimited)
        limit = memory_stats.get('limit', 0)

        # Ensure we have valid values
        usage = usage or 0
        limit = limit or 0

        # Calculate percentage (handle division by zero)
        percent = (usage / limit * 100) if limit > 0 else 0

        return {
            'usage': usage,
            'limit': limit,
            'percent': percent
        }

    except Exception as e:
        logger.warning(f"Error calculating memory usage: {e}", exc_info=True)
        return {'usage': 0, 'limit': 0, 'percent': 0}


def _get_network_io(stats: dict[str, Any]) -> dict[str, int]:
    """Get network I/O statistics from container stats.

    Args:
        stats: Raw container stats dictionary from Docker API

    Returns:
        Dictionary with network I/O statistics:
        - rx_bytes: Total received bytes
        - tx_bytes: Total transmitted bytes
    """
    try:
        # Try to get network stats from the new location (Docker 1.12+)
        networks = stats.get('networks', {})

        # Fall back to the old location if not found
        if not networks and 'network' in stats:
            networks = stats['network']

        rx_bytes = 0
        tx_bytes = 0

        # Sum up bytes across all network interfaces
        for _if_name, if_stats in networks.items():
            if isinstance(if_stats, dict):
                rx_bytes += if_stats.get('rx_bytes', 0)
                tx_bytes += if_stats.get('tx_bytes', 0)

        return {
            'rx_bytes': rx_bytes,
            'tx_bytes': tx_bytes
        }

    except Exception as e:
        logger.warning(f"Error getting network I/O: {e}", exc_info=True)
        return {'rx_bytes': 0, 'tx_bytes': 0}

# Define response models first to avoid circular imports
class BaseResponse[T](BaseModel):
    """Base response model for all API responses.

    This generic model provides a consistent response format with status, message,
    data, and error fields. It's designed to work with Pydantic v2 features.
    """
    model_config = ConfigDict(
        json_encoders={
            # Custom JSON encoders for common types
            'datetime': lambda v: v.isoformat() if v else None,
            'IPv4Network': str,
            'IPv6Network': str,
            'IPv4Address': str,
            'IPv6Address': str,
        },
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": None,
                "error": None
            }
        }
    )

    status: str = Field(..., description="Status of the operation (success/error)")
    message: str | None = Field(default=None, description="Human-readable message")
    data: T | None = Field(default=None, description="Response data")
    error: str | None = Field(default=None, description="Error message if operation failed")

    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation of the model.

        Overrides the default to ensure proper serialization of custom types.
        """
        return super().model_dump_json(exclude_none=True, **kwargs)

    @classmethod
    def success(
        cls,
        data: T | None = None,
        message: str | None = None
    ) -> BaseResponse[T]:
        """Create a success response.

        Args:
            data: The response data
            message: Optional success message

        Returns:
            BaseResponse with status 'success' and the provided data/message
        """
        return cls(
            status="success",
            message=message or "Operation completed successfully",
            data=data
        )

    @classmethod
    def error(
        cls,
        error: str,
        message: str | None = None,
        data: Any | None = None
    ) -> BaseResponse[T]:
        """Create an error response.

        Args:
            error: Error message or code
            message: Optional human-readable message
            data: Optional error details

        Returns:
            BaseResponse with status 'error' and the provided error details
        """
        return cls(
            status="error",
            message=message or "An error occurred",
            error=error,
            data=data
        )

class ContainerInspectRequest(BaseModel):
    """Request model for container inspection.

    This model defines the parameters for inspecting a Docker container,
    including options for including resource usage statistics and logs.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "my-container",
                "show_stats": True,
                "show_logs": True,
                "log_tail": 100
            }
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )

    container_id: str = Field(
        ...,
        min_length=1,
        description="ID or name of the container to inspect",
        json_schema_extra={"example": "my-container"}
    )

    show_stats: bool = Field(
        default=False,
        description=(
            "Whether to include resource usage statistics (CPU, memory, network). "
            "Note: This may add some overhead to the request."
        )
    )

    show_logs: bool = Field(
        default=False,
        description=(
            "Whether to include container logs in the response. "
            "Logs can be large, so use with caution."
        )
    )

    log_tail: int = Field(
        default=DEFAULT_LOG_TAIL,
        ge=1,
        le=MAX_LOG_LINES,
        description=(
            f"Number of log lines to include when show_logs is True. "
            f"Must be between 1 and {MAX_LOG_LINES}."
        ),
        json_schema_extra={"example": 100}
    )

    @field_validator('container_id')
    @classmethod
    def validate_container_id(cls, v: str) -> str:
        """Validate container ID or name."""
        # Remove any leading slashes (Docker adds these to container names)
        v = v.lstrip('/')

        # Basic validation - container IDs and names should not be empty
        if not v:
            raise ValueError("Container ID or name cannot be empty")

        # Additional validation could be added here if needed
        # (e.g., check for invalid characters, length limits, etc.)

        return v


class ContainerInspectResponse(BaseModel):
    """Response model for container inspection.

    This model represents detailed information about a Docker container,
    including its configuration, state, and resource usage.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "container_id_123",
                "name": "my-container",
                "image": "nginx:latest",
                "status": "running",
                "state": {"Status": "running"},
                "created": "2023-01-01T00:00:00Z",
                "config": {},
                "host_config": {},
                "network_settings": {},
                "mounts": [],
                "environment": {"ENV_VAR": "value"},
                "labels": {}
            }
        },
        # Enable orm_mode for compatibility with SQLAlchemy models if needed
        from_attributes=True,
        # Enable arbitrary types for nested dictionaries
        arbitrary_types_allowed=True,
        # Enable JSON encoders for custom types
        json_encoders={
            'datetime': lambda v: v.isoformat() if v else None,
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )

    # Container identification
    id: str = Field(
        ...,
        description="Unique container ID (64-character hexadecimal string)",
        min_length=1,
        json_schema_extra={"example": "a1b2c3d4e5f6"}
    )

    name: str = Field(
        ...,
        description="Container name (without leading slash)",
        min_length=1,
        json_schema_extra={"example": "my-container"}
    )

    # Container configuration
    image: str = Field(
        ...,
        description="Container image name and tag or digest",
        json_schema_extra={"example": "nginx:latest"}
    )

    status: str = Field(
        ...,
        description="Container status (e.g., 'running', 'exited', 'paused', 'restarting')",
        json_schema_extra={"example": "running"}
    )

    state: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Container state details including health, exit code, etc. "
            "This is a direct mapping from the Docker API."
        )
    )

    created: str = Field(
        ...,
        description="ISO 8601 timestamp of container creation",
        json_schema_extra={"example": "2023-01-01T12:00:00Z"}
    )

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Container configuration as provided during creation"
    )

    host_config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Host-specific configuration for the container, "
            "including resource limits and security options"
        )
    )

    network_settings: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Network settings including IP addresses, ports, "
            "and network mode"
        )
    )

    # Storage and networking
    mounts: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of volume and bind mounts attached to the container, "
            "including source, destination, and mount options"
        )
    )

    environment: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Environment variables set in the container, "
            "as key-value pairs"
        )
    )

    labels: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Labels assigned to the container, "
            "typically used for metadata and orchestration"
        )
    )

    # Optional fields with default values
    command: str | None = Field(
        default=None,
        description=(
            "Command run in the container. "
            "This is the command that was specified when the container was created."
        )
    )

    args: list[str] | None = Field(
        default=None,
        description=(
            "Arguments passed to the container command. "
            "These are the arguments that were specified when the container was created."
        )
    )

    working_dir: str | None = Field(
        default=None,
        description=(
            "Working directory inside the container. "
            "This is the directory where the command will be executed."
        )
    )

    # Resource usage (populated if show_stats=True)
    cpu_usage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description=(
            "CPU usage as a percentage (0-100) of total available CPU. "
            "This is only included if show_stats was True in the request."
        ),
        json_schema_extra={"example": 25.5}
    )

    memory_usage: dict[str, int] | None = Field(
        default=None,
        description=(
            "Memory usage statistics in bytes. "
            "This is only included if show_stats was True in the request. "
            "Includes 'usage', 'limit', and 'percent' keys."
        )
    )

    network_io: dict[str, int] | None = Field(
        default=None,
        description=(
            "Network I/O statistics in bytes. "
            "This is only included if show_stats was True in the request. "
            "Includes 'rx_bytes' and 'tx_bytes' for received and transmitted data."
        )
    )

    # Logs (populated if show_logs=True)
    logs: str | None = Field(
        default=None,
        description=(
            "Container logs as a string. "
            "This is only included if show_logs was True in the request. "
            "May be truncated based on the log_tail parameter."
        )
    )

    # Validators
    @field_validator('created')
    @classmethod
    def validate_created_timestamp(cls, v: str) -> str:
        """Validate that the created timestamp is in ISO 8601 format."""
        if not isinstance(v, str):
            raise ValueError("Created timestamp must be a string")
        # Basic validation - could be enhanced with actual datetime parsing
        if len(v) < 10:  # At least YYYY-MM-DD
            raise ValueError("Invalid timestamp format, expected ISO 8601")
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate container status."""
        valid_statuses = {
            'created', 'running', 'paused', 'restarting',
            'removing', 'exited', 'dead'
        }
        if v.lower() not in valid_statuses:
            logger.warning(f"Unexpected container status: {v}")
        return v.lower()

    # Methods
    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation of the model.

        Overrides the default to ensure proper serialization of custom types.
        """
        # Use exclude_none to skip None values in the output
        return super().model_dump_json(exclude_none=True, **kwargs)

    def is_running(self) -> bool:
        """Check if the container is currently running."""
        return self.status.lower() == 'running'

    def get_ip_address(self) -> str | None:
        """Get the primary IP address of the container if available."""
        try:
            # Try to get the IP address from network settings
            networks = self.network_settings.get('Networks', {})
            for network in networks.values():
                if network.get('IPAddress'):
                    return network['IPAddress']
            return None
        except Exception as e:
            logger.warning(f"Failed to get container IP address: {e}")
            return None

    @classmethod
    def from_docker_container(
        cls,
        container: Any,
        show_stats: bool = False,
        show_logs: bool = False,
        log_tail: int = 100
    ) -> ContainerInspectResponse:
        """Create a ContainerInspectResponse from a Docker container object.

        Args:
            container: Docker container object
            show_stats: Whether to include resource usage statistics
            show_logs: Whether to include container logs
            log_tail: Number of log lines to include if show_logs is True

        Returns:
            ContainerInspectResponse with container information
        """
        container.reload()  # Ensure we have the latest state
        container_dict = container.attrs

        # Extract basic information
        response_data = {
            'id': container.id,
            'name': container.name.lstrip('/'),
            'image': container.image.tags[0] if container.image.tags else container.image.id,
            'status': container.status,
            'state': container_dict.get('State', {}),
            'created': container_dict.get('Created'),
            'config': container_dict.get('Config', {}),
            'host_config': container_dict.get('HostConfig', {}),
            'network_settings': container_dict.get('NetworkSettings', {}),
            'mounts': container_dict.get('Mounts', []),
            'environment': {k: v for k, v in [
                env.split('=', 1) if '=' in env else (env, '')
                for env in container_dict.get('Config', {}).get('Env', [])
            ]},
            'labels': container_dict.get('Config', {}).get('Labels', {}),
            'command': container_dict.get('Config', {}).get('Cmd'),
            'args': container_dict.get('Args'),
            'working_dir': container_dict.get('Config', {}).get('WorkingDir')
        }

        # Add resource usage statistics if requested
        if show_stats:
            try:
                stats = container.stats(stream=False)
                response_data.update({
                    'cpu_usage': _calculate_cpu_percent(stats),
                    'memory_usage': _calculate_memory_usage(stats),
                    'network_io': _get_network_io(stats)
                })
            except (DockerException, APIError) as e:
                logger.warning(f"Failed to get container stats: {e}")

        # Add logs if requested
        if show_logs:
            try:
                logs = container.logs(tail=log_tail).decode('utf-8')
                response_data['logs'] = logs
            except (DockerException, APIError) as e:
                logger.warning(f"Failed to get container logs: {e}")

        return cls(**response_data)

async def _inspect_container_impl(request: ContainerInspectRequest) -> BaseResponse[ContainerInspectResponse]:
    """
    Inspect a Docker container and return detailed information.

    Args:
        request: ContainerInspectRequest instance containing container ID and inspection options

    Returns:
        BaseResponse containing ContainerInspectResponse with container details or error information
    """
    try:
        # Initialize Docker client
        client = docker.from_env()

        # Get container by ID or name
        container = client.containers.get(request.container_id)

        # Create response using the from_docker_container class method
        response = ContainerInspectResponse.from_docker_container(
            container=container,
            show_stats=request.show_stats,
            show_logs=request.show_logs,
            log_tail=request.log_tail
        )

        return BaseResponse[ContainerInspectResponse].success(
            data=response,
            message="Container inspection completed successfully"
        )

    except NotFound:
        error_msg = f"Container not found: {request.container_id}"
        logger.error(error_msg)
        return BaseResponse[ContainerInspectResponse].error(
            error="container_not_found",
            message=error_msg,
            data={"container_id": request.container_id}
        )

    except APIError as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg)
        return BaseResponse[ContainerInspectResponse].error(
            error="docker_api_error",
            message=error_msg,
            data={"container_id": request.container_id}
        )

    except DockerException as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg)
        return BaseResponse[ContainerInspectResponse].error(
            error="docker_error",
            message="Docker daemon not available or not running",
            data={"container_id": request.container_id}
        )

    except Exception as e:
        error_msg = f"Error inspecting container {request.container_id}: {e!s}"
        logger.error(error_msg, exc_info=True)
        return BaseResponse[ContainerInspectResponse].error(
            error="unexpected_error",
            message=error_msg,
            data={"container_id": request.container_id}
        )

# Public interface function
async def inspect_container(params: ContainerInspectRequest) -> BaseResponse[ContainerInspectResponse]:
    """Public interface for container inspection.

    Args:
        params: ContainerInspectRequest with container ID and inspection options

    Returns:
        BaseResponse containing ContainerInspectResponse with container details or error information
    """
    return await _inspect_container_impl(params)

# Alias for compatibility with container_management.py
ContainerInspectParams = ContainerInspectRequest
