"""
Container resource management for Docker MCP.

This module provides tools for managing container resource constraints including
CPU, memory, I/O, and other resource limits. It follows FastMCP 2.12+ standards
for tool registration and error handling.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import docker
from docker.errors import APIError, NotFound

# from fastmcp.exceptions import ToolError  # Not used, causes import error in FastMCP 2.12+
from fastmcp import FastMCP
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    conint,
)

from dockermcp.logging_config import logger
from dockermcp.tools import ToolResponse

# Initialize FastMCP instance
mcp = FastMCP("Container Resource Tools")


# Enums for resource management
class CpuPriority(StrEnum):
    """CPU priority levels for container CPU shares."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryUnit(StrEnum):
    """Memory unit options for resource limits."""

    BYTES = "b"
    KILOBYTES = "k"
    MEGABYTES = "m"
    GIGABYTES = "g"


# Request/Response Models
class IoDeviceWeight(BaseModel):
    """I/O weight configuration for a device."""

    model_config = ConfigDict(json_schema_extra={"example": {"path": "/dev/sda", "weight": 200}})
    path: str = Field(..., description="Path to the device")
    weight: conint(ge=10, le=1000) = Field(default=100, description="I/O weight (10-1000, default: 100)", example=200)


class ResourceUpdateResult(BaseModel):
    """Result of a resource update operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "resource_type": "memory_limit",
                "previous_value": 536870912,
                "new_value": 1073741824,
                "warnings": [],
            }
        }
    )
    container_id: str = Field(..., description="ID of the container")
    resource_type: str = Field(..., description="Type of resource that was updated")
    previous_value: Any = Field(None, description="Previous resource value")
    new_value: Any = Field(..., description="New resource value")
    warnings: list[str] = Field(default_factory=list, description="List of warning messages, if any")


class GetContainerResourcesParams(BaseModel):
    """Parameters for getting container resources."""

    model_config = ConfigDict(json_schema_extra={"example": {"container_id": "my-container", "include_usage": True}})

    container_id: str = Field(..., description="ID or name of the container")
    include_usage: bool = Field(default=True, description="Include current resource usage statistics")


class ContainerResourcesResponse(BaseModel):
    """Response model for container resources."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "resources": {
                    "cpu": {"shares": 1024, "quota": 100000, "period": 100000, "cpus": "0-3"},
                    "memory": {"limit": 1073741824, "reservation": 536870912},
                },
                "usage": {
                    "cpu_usage": {
                        "total_usage": 1000000000,
                        "percpu_usage": [500000000, 500000000],
                        "system_cpu_usage": 5000000000,
                        "online_cpus": 2,
                    }
                },
            }
        }
    )

    container_id: str = Field(..., description="ID of the container")
    resources: dict[str, Any] = Field(..., description="Resource limits and configuration")
    usage: dict[str, Any] | None = Field(None, description="Current resource usage statistics")


@mcp.tool
async def get_container_resources(params: GetContainerResourcesParams) -> ToolResponse[ContainerResourcesResponse]:
    """
    Get detailed resource allocation and usage information for a container.

    This function provides a comprehensive view of a container's resource configuration
    including CPU, memory, I/O, and process limits. It can optionally include current
    resource usage statistics.

    Args:
        params: GetContainerResourcesParams containing:
            - container_id: ID or name of the container
            - include_usage: Whether to include current resource usage statistics

    Returns:
        ToolResponse[ContainerResourcesResponse] containing container resource information

    Raises:
        DockerException: If there's an error communicating with the Docker daemon
        APIError: If the Docker API returns an error
        NotFound: If the container doesn't exist
    """
    logger.info(
        "Getting container resources",
        extra={"container_id": params.container_id, "include_usage": params.include_usage},
    )

    try:
        client = docker.from_env()
        container = client.containers.get(params.container_id)

        # Get container attributes
        attrs = container.attrs

        # Build resources dictionary
        resources = {
            "cpu": {
                "shares": attrs.get("HostConfig", {}).get("CpuShares"),
                "quota": attrs.get("HostConfig", {}).get("CpuQuota"),
                "period": attrs.get("HostConfig", {}).get("CpuPeriod"),
                "cpus": attrs.get("HostConfig", {}).get("CpusetCpus"),
                "realtime_period": attrs.get("HostConfig", {}).get("CpuRealtimePeriod"),
                "realtime_runtime": attrs.get("HostConfig", {}).get("CpuRealtimeRuntime"),
                "cfs_period": attrs.get("HostConfig", {}).get("CpuPeriod"),
                "cfs_quota": attrs.get("HostConfig", {}).get("CpuQuota"),
            },
            "memory": {
                "limit": attrs.get("HostConfig", {}).get("Memory"),
                "reservation": attrs.get("HostConfig", {}).get("MemoryReservation"),
                "swap": attrs.get("HostConfig", {}).get("MemorySwap"),
                "swappiness": attrs.get("HostConfig", {}).get("MemorySwappiness"),
                "oom_kill_disable": attrs.get("HostConfig", {}).get("OomKillDisable"),
            },
            "blkio": {
                "weight": attrs.get("HostConfig", {}).get("BlkioWeight"),
                "device_weights": attrs.get("HostConfig", {}).get("BlkioWeightDevice"),
                "device_read_bps": attrs.get("HostConfig", {}).get("BlkioDeviceReadBps"),
                "device_write_bps": attrs.get("HostConfig", {}).get("BlkioDeviceWriteBps"),
                "device_read_iops": attrs.get("HostConfig", {}).get("BlkioDeviceReadIOps"),
                "device_write_iops": attrs.get("HostConfig", {}).get("BlkioDeviceWriteIOps"),
            },
            "pids": {"limit": attrs.get("HostConfig", {}).get("PidsLimit")},
            "restart_policy": attrs.get("HostConfig", {}).get("RestartPolicy"),
        }

        # Get usage stats if requested
        usage = None
        if params.include_usage:
            try:
                stats = container.stats(stream=False)
                usage = {
                    "cpu_usage": stats.get("cpu_stats"),
                    "memory_usage": stats.get("memory_stats"),
                    "block_io": stats.get("blkio_stats"),
                    "network": stats.get("networks"),
                    "pids_stats": stats.get("pids_stats"),
                    "read": stats.get("read"),
                }
            except Exception as e:
                logger.warning(
                    f"Failed to get container stats: {e!s}", extra={"container_id": params.container_id}, exc_info=True
                )

        return ToolResponse[ContainerResourcesResponse](
            success=True,
            message=f"Retrieved resources for container {container.id}",
            data=ContainerResourcesResponse(container_id=container.id, resources=resources, usage=usage),
        )

    except NotFound as e:
        logger.error(
            f"Container not found: {params.container_id}", extra={"container_id": params.container_id}, exc_info=True
        )
        return ToolResponse[ContainerResourcesResponse](
            success=False, message=f"Container not found: {e!s}", error=f"Container not found: {e!s}"
        )
    except APIError as e:
        logger.error(f"Docker API error: {e!s}", extra={"container_id": params.container_id}, exc_info=True)
        return ToolResponse[ContainerResourcesResponse](
            success=False, message=f"Docker API error: {e!s}", error=f"Docker API error: {e!s}"
        )
    except Exception as e:
        logger.error(
            f"Error getting container resources: {e!s}", extra={"container_id": params.container_id}, exc_info=True
        )
        return ToolResponse[ContainerResourcesResponse](
            success=False,
            message=f"Error getting container resources: {e!s}",
            error=f"Error getting container resources: {e!s}",
        )


class ResetContainerResourcesParams(BaseModel):
    """Parameters for resetting container resources."""

    model_config = ConfigDict(json_schema_extra={"example": {"container_id": "my-container"}})

    container_id: str = Field(..., description="ID or name of the container to reset")


class ResetContainerResourcesResponse(BaseModel):
    """Response model for resetting container resources."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "reset_resources": ["cpu_shares", "memory_limit", "blkio_weight"],
            }
        }
    )

    container_id: str = Field(..., description="ID of the container")
    reset_resources: list[str] = Field(..., description="List of resource types that were reset")


@mcp.tool
async def reset_container_resources(
    params: ResetContainerResourcesParams,
) -> ToolResponse[ResetContainerResourcesResponse]:
    """
    Reset all resource limits for a container to their default values.

    This function removes all custom resource constraints (CPU, memory, I/O, etc.)
    from a container, restoring them to their default values. This is useful for
    removing resource limitations or troubleshooting resource-related issues.

    Args:
        params: ResetContainerResourcesParams containing:
            - container_id: ID or name of the container to reset

    Returns:
        ToolResponse[ResetContainerResourcesResponse] containing:
            - container_id: ID of the container
            - reset_resources: List of resource types that were reset

    Raises:
        DockerException: If there's an error communicating with the Docker daemon
        APIError: If the Docker API returns an error

    Example:
        >>> response = await reset_container_resources(
        ...     ResetContainerResourcesParams(container_id="my-container")
        ... )
        >>> if response.success:
        ...     print(f"Reset {len(response.data.reset_resources)} resources for {response.data.container_id}")
    """
    logger.info("Resetting container resources to default values", extra={"container_id": params.container_id})

    try:
        client = docker.from_env()
        container = client.containers.get(params.container_id)

        # Get current container config
        current_config = container.attrs["HostConfig"]

        # Build update config with default/empty values
        update_config = {
            # Reset CPU settings
            "CpuShares": 0,  # 0 means use the default
            "CpuQuota": 0,  # 0 means use the default
            "CpuPeriod": 0,  # 0 means use the default
            "CpusetCpus": "",  # Empty means use all CPUs
            # Reset memory settings
            "Memory": 0,  # 0 means no limit
            "MemoryReservation": 0,  # 0 means no limit
            "MemorySwap": 0,  # 0 means no limit
            "MemorySwappiness": None,  # None means use the default
            # Reset I/O settings
            "BlkioWeight": 0,  # 0 means use the default
            "BlkioWeightDevice": None,
            "BlkioDeviceReadBps": None,
            "BlkioDeviceWriteBps": None,
            "BlkioDeviceReadIOps": None,
            "BlkioDeviceWriteIOps": None,
            # Reset process limits
            "PidsLimit": 0,  # 0 means no limit
            # Reset restart policy
            "RestartPolicy": {"Name": "no"},
        }

        # Track which resources were reset
        reset_resources = []

        # Check which resources were actually set and need to be reset
        if current_config.get("CpuShares") != 0:
            reset_resources.append("cpu_shares")
        if current_config.get("CpuQuota") != 0:
            reset_resources.append("cpu_quota")
        if current_config.get("CpuPeriod") != 0:
            reset_resources.append("cpu_period")
        if current_config.get("CpusetCpus") not in ("", None):
            reset_resources.append("cpuset_cpus")
        if current_config.get("Memory") != 0:
            reset_resources.append("memory_limit")
        if current_config.get("MemoryReservation") != 0:
            reset_resources.append("memory_reservation")
        if current_config.get("MemorySwap") != 0:
            reset_resources.append("memory_swap")
        if current_config.get("MemorySwappiness") is not None:
            reset_resources.append("memory_swappiness")
        if current_config.get("BlkioWeight") != 0:
            reset_resources.append("blkio_weight")
        if current_config.get("BlkioWeightDevice"):
            reset_resources.append("blkio_device_weights")
        if current_config.get("BlkioDeviceReadBps"):
            reset_resources.append("blkio_read_bps")
        if current_config.get("BlkioDeviceWriteBps"):
            reset_resources.append("blkio_write_bps")
        if current_config.get("BlkioDeviceReadIOps"):
            reset_resources.append("blkio_read_iops")
        if current_config.get("BlkioDeviceWriteIOps"):
            reset_resources.append("blkio_write_iops")
        if current_config.get("PidsLimit") != 0:
            reset_resources.append("pids_limit")
        if current_config.get("RestartPolicy", {}).get("Name") != "no":
            reset_resources.append("restart_policy")

        # Only update if there are resources to reset
        if reset_resources:
            # Update the container with the reset configuration
            container.update(**update_config)

            logger.info(
                f"Reset {len(reset_resources)} resources for container {params.container_id}",
                extra={"container_id": params.container_id, "reset_resources": reset_resources},
            )
        else:
            logger.info(
                f"No resource limits to reset for container {params.container_id}",
                extra={"container_id": params.container_id},
            )

        return ToolResponse[ResetContainerResourcesResponse](
            success=True,
            message=f"Reset {len(reset_resources)} resources for container {container.id}",
            data=ResetContainerResourcesResponse(container_id=container.id, reset_resources=reset_resources),
        )

    except NotFound as e:
        logger.error(
            f"Container not found: {params.container_id}", extra={"container_id": params.container_id}, exc_info=True
        )
        return ToolResponse[ResetContainerResourcesResponse](
            success=False, message=f"Container not found: {e!s}", error=f"Container not found: {e!s}"
        )
    except APIError as e:
        logger.error(f"Docker API error: {e!s}", extra={"container_id": params.container_id}, exc_info=True)
        return ToolResponse[ResetContainerResourcesResponse](
            success=False, message=f"Docker API error: {e!s}", error=f"Docker API error: {e!s}"
        )
    except Exception as e:
        logger.error(
            f"Error resetting container resources: {e!s}", extra={"container_id": params.container_id}, exc_info=True
        )
        return ToolResponse[ResetContainerResourcesResponse](
            success=False,
            message=f"Error resetting container resources: {e!s}",
            error=f"Error resetting container resources: {e!s}",
        )


# Register tools with FastMCP
def get_tools():
    """Return a list of tools for FastMCP to register."""
    return [get_container_resources, reset_container_resources]
