"""
Container resource management for Docker MCP.

This module provides tools for managing container resource constraints including
CPU, memory, I/O, and other resource limits. It follows FastMCP 2.12+ standards
for tool registration and error handling.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Annotated

import docker
from docker.errors import APIError, ContainerError, DockerException, NotFound
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolException
from fastmcp import FastMCP
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    confloat,
    conint,
    field_validator,
    model_validator,
)

from dockermcp.logging_config import logger

# Initialize FastMCP instance
mcp = FastMCP("Container Resource Tools")

# Enums for resource management
class CpuPriority(str, Enum):
    """CPU priority levels for container CPU shares."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class MemoryUnit(str, Enum):
    """Memory unit options for resource limits."""
    BYTES = "b"
    KILOBYTES = "k"
    MEGABYTES = "m"
    GIGABYTES = "g"

# Request/Response Models
class IoDeviceWeight(BaseModel):
    """I/O weight configuration for a device."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "path": "/dev/sda",
                "weight": 200
            }
        }
    )
    path: str = Field(..., description="Path to the device")
    weight: conint(ge=10, le=1000) = Field(
        default=100,
        description="I/O weight (10-1000, default: 100)",
        example=200
    )

class ResourceUpdateResult(BaseModel):
    """Result of a resource update operation."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "resource_type": "memory_limit",
                "previous_value": 536870912,
                "new_value": 1073741824,
                "warnings": []
            }
        }
    )
    container_id: str = Field(..., description="ID of the container")
    resource_type: str = Field(..., description="Type of resource that was updated")
    previous_value: Any = Field(None, description="Previous resource value")
    new_value: Any = Field(..., description="New resource value")
    warnings: List[str] = Field(
        default_factory=list,
        description="List of warning messages, if any"
    )

class ContainerResourcesParams(BaseModel):
    """Parameters for managing container resources."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "my-container",
                "cpu_priority": "high",
                "memory_limit": "1g",
                "memory_reservation": "512m",
                "blkio_weight": 500,
                "device_weights": [{"path": "/dev/sda", "weight": 200}],
                "pids_limit": 1024
            }
        }
    )
    
    container_id: str = Field(..., description="ID or name of the container")
    cpu_priority: Optional[CpuPriority] = Field(
        None,
        description="CPU priority level (overrides cpu_shares if set)",
        example="high"
    )
    cpu_shares: Optional[conint(ge=2, le=262144)] = Field(
        None,
        description="CPU shares (relative weight)",
        example=512
    )
    cpu_quota: Optional[conint(ge=1000)] = Field(
        None,
        description="Microseconds of CPU time the container gets per cpu_period",
        example=50000
    )
    cpu_period: conint(ge=1000, le=1000000) = Field(
        100000,
        description="The length of a CPU period in microseconds",
        example=100000
    )
    cpus: Optional[str] = Field(
        None,
        description="CPUs in which to allow execution (0-3, 0,1)",
        example="0-2"
    )
    memory_limit: Optional[str] = Field(
        None,
        description="Memory limit (e.g., 512m, 2g)",
        example="1g"
    )
    memory_reservation: Optional[str] = Field(
        None,
        description="Memory soft limit (e.g., 512m, 2g)",
        example="512m"
    )
    memory_swappiness: Optional[conint(ge=0, le=100)] = Field(
        None,
        description="Tune container memory swappiness (0-100)",
        example=60
    )
    blkio_weight: Optional[conint(ge=10, le=1000)] = Field(
        None,
        description="Block IO weight (relative weight), between 10 and 1000",
        example=500
    )
    device_weights: List[IoDeviceWeight] = Field(
        default_factory=list,
        description="List of per-device block IO weights"
    )
    device_read_bps: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Limit read rate (bytes per second) from a device"
    )
    device_write_bps: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Limit write rate (bytes per second) to a device"
    )
    device_read_iops: List[Dict[str, Union[str, int]]] = Field(
        default_factory=list,
        description="Limit read rate (IO per second) from a device"
    )
    device_write_iops: List[Dict[str, Union[str, int]]] = Field(
        default_factory=list,
        description="Limit write rate (IO per second) to a device"
    )
    pids_limit: Optional[int] = Field(
        None,
        description="Limit the number of processes (set -1 for unlimited)",
        example=1024
    )
    restart_policy: Optional[Dict[str, Any]] = Field(
        None,
        description="Restart policy to apply when a container exits"
    )

    @field_validator('memory_limit', 'memory_reservation', mode='before')
    @classmethod
    def validate_memory_string(cls, v):
        """Validate memory string format."""
        if v is not None:
            try:
                return _parse_memory_string(v)
            except ValueError as e:
                raise ValueError(f"Invalid memory format: {str(e)}") from e
        return v

class UpdateContainerResourcesResponse(BaseModel):
    """Response model for updating container resources."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "updates": [
                    {
                        "resource_type": "cpu_shares",
                        "previous_value": 1024,
                        "new_value": 2048,
                        "warnings": []
                    },
                    {
                        "resource_type": "memory_limit",
                        "previous_value": 536870912,
                        "new_value": 1073741824,
                        "warnings": []
                    }
                ]
            }
        }
    )
    
    container_id: str = Field(..., description="ID of the container")
    updates: List[ResourceUpdateResult] = Field(
        ...,
        description="List of resource updates that were applied"
    )

class GetContainerResourcesParams(BaseModel):
    """Parameters for getting container resources."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "my-container",
                "include_usage": True
            }
        }
    )
    
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    include_usage: bool = Field(
        default=True,
        description="Include current resource usage statistics"
    )

class ContainerResourcesResponse(BaseModel):
    """Response model for container resources."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "resources": {
                    "cpu": {
                        "shares": 1024,
                        "quota": 100000,
                        "period": 100000,
                        "cpus": "0-3"
                    },
                    "memory": {
                        "limit": 1073741824,
                        "reservation": 536870912
                    }
                },
                "usage": {
                    "cpu_usage": {
                        "total_usage": 1000000000,
                        "percpu_usage": [500000000, 500000000],
                        "system_cpu_usage": 5000000000,
                        "online_cpus": 2
                    }
                }
            }
        }
    )
    
    container_id: str = Field(..., description="ID of the container")
    resources: Dict[str, Any] = Field(..., description="Resource limits and configuration")
    usage: Optional[Dict[str, Any]] = Field(
        None,
        description="Current resource usage statistics"
    )

def _parse_memory_string(mem_str: str) -> int:
    """Parse a memory string (e.g., '512m', '2g') into bytes."""
    if not mem_str:
        raise ValueError("Memory string cannot be empty")
    
    units = {
        'b': 1,
        'k': 1024,
        'm': 1024 * 1024,
        'g': 1024 * 1024 * 1024
    }
    
    # Extract number and unit
    num_str = ''
    unit = 'b'
    
    for i, c in enumerate(mem_str.lower()):
        if c.isdigit() or c == '.':
            num_str += c
        else:
            unit = c
            if unit not in units:
                raise ValueError(f"Invalid memory unit: {unit}. Must be one of: {', '.join(units.keys())}")
            break
    
    if not num_str:
        raise ValueError("No numeric value found in memory string")
    
    try:
        num = float(num_str)
    except ValueError as e:
        raise ValueError(f"Invalid numeric value in memory string: {num_str}") from e
    
    return int(num * units[unit])

@mcp.tool(
    name="get_container_resources",
    description="Get detailed resource allocation and usage information for a container"
)
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
        extra={"container_id": params.container_id, "include_usage": params.include_usage}
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
                "cfs_quota": attrs.get("HostConfig", {}).get("CpuQuota")
            },
            "memory": {
                "limit": attrs.get("HostConfig", {}).get("Memory"),
                "reservation": attrs.get("HostConfig", {}).get("MemoryReservation"),
                "swap": attrs.get("HostConfig", {}).get("MemorySwap"),
                "swappiness": attrs.get("HostConfig", {}).get("MemorySwappiness"),
                "oom_kill_disable": attrs.get("HostConfig", {}).get("OomKillDisable")
            },
            "blkio": {
                "weight": attrs.get("HostConfig", {}).get("BlkioWeight"),
                "device_weights": attrs.get("HostConfig", {}).get("BlkioWeightDevice"),
                "device_read_bps": attrs.get("HostConfig", {}).get("BlkioDeviceReadBps"),
                "device_write_bps": attrs.get("HostConfig", {}).get("BlkioDeviceWriteBps"),
                "device_read_iops": attrs.get("HostConfig", {}).get("BlkioDeviceReadIOps"),
                "device_write_iops": attrs.get("HostConfig", {}).get("BlkioDeviceWriteIOps")
            },
            "pids": {
                "limit": attrs.get("HostConfig", {}).get("PidsLimit")
            },
            "restart_policy": attrs.get("HostConfig", {}).get("RestartPolicy")
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
                    "read": stats.get("read")
                }
            except Exception as e:
                logger.warning(
                    f"Failed to get container stats: {str(e)}",
                    extra={"container_id": params.container_id},
                    exc_info=True
                )
        
        return ToolResponse[ContainerResourcesResponse](
            success=True,
            data=ContainerResourcesResponse(
                container_id=container.id,
                resources=resources,
                usage=usage
            )
        )
        
    except NotFound as e:
        logger.error(
            f"Container not found: {params.container_id}",
            extra={"container_id": params.container_id},
            exc_info=True
        )
        return ToolResponse[ContainerResourcesResponse](
            success=False,
            error=f"Container not found: {str(e)}",
            error_code="not_found"
        )
    except APIError as e:
        logger.error(
            f"Docker API error: {str(e)}",
            extra={"container_id": params.container_id},
            exc_info=True
        )
        return ToolResponse[ContainerResourcesResponse](
            success=False,
            error=f"Docker API error: {str(e)}",
            error_code="docker_api_error"
        )
    except Exception as e:
        logger.error(
            f"Error getting container resources: {str(e)}",
            extra={"container_id": params.container_id},
            exc_info=True
        )
        return ToolResponse[ContainerResourcesResponse](
            success=False,
            error=f"Error getting container resources: {str(e)}",
            error_code="internal_error"
        )

class ResetContainerResourcesParams(BaseModel):
    """Parameters for resetting container resources."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "my-container"
            }
        }
    )
    
    container_id: str = Field(..., description="ID or name of the container to reset")

class ResetContainerResourcesResponse(BaseModel):
    """Response model for resetting container resources."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "reset_resources": ["cpu_shares", "memory_limit", "blkio_weight"]
            }
        }
    )
    
    container_id: str = Field(..., description="ID of the container")
    reset_resources: List[str] = Field(
        ...,
        description="List of resource types that were reset"
    )

@mcp.tool(
    name="reset_container_resources",
    description=(
        "Reset all resource limits for a container to their default values. "
        "This will remove any custom CPU, memory, I/O, or other resource constraints."
    )
)
async def reset_container_resources(
    params: ResetContainerResourcesParams
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
    logger.info(
        "Resetting container resources to default values",
        extra={"container_id": params.container_id}
    )
    
    try:
        client = docker.from_env()
        container = client.containers.get(params.container_id)
        
        # Get current container config
        current_config = container.attrs["HostConfig"]
        
        # Build update config with default/empty values
        update_config = {
            # Reset CPU settings
            "CpuShares": 0,  # 0 means use the default
            "CpuQuota": 0,   # 0 means use the default
            "CpuPeriod": 0,  # 0 means use the default
            "CpusetCpus": "",  # Empty means use all CPUs
            
            # Reset memory settings
            "Memory": 0,           # 0 means no limit
            "MemoryReservation": 0, # 0 means no limit
            "MemorySwap": 0,        # 0 means no limit
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
            
            # Other resource-related settings
            "CgroupParent": "",
            "DeviceRequests": None,
            "OomKillDisable": False,
            "OomScoreAdj": 0,
            "CpuCount": 0,
            "CpuPercent": 0,
            "IOMaximumIOps": 0,
            "IOMaximumBandwidth": 0,
            "Ulimits": None,
            "CpuRealtimePeriod": 0,
            "CpuRealtimeRuntime": 0,
            "CpuCfsPeriod": 0,
            "CpuCfsQuota": 0,
            "CpuQuota": 0,
            "CpuPeriod": 0,
            "CpuShares": 0,
            "CpusetCpus": "",
            "CpusetMems": "",
            "DeviceCgroupRules": None,
            "DeviceRequests": None,
            "KernelMemory": 0,
            "KernelMemoryTCP": 0,
            "MemoryReservation": 0,
            "MemorySwap": 0,
            "MemorySwappiness": None,
            "NanoCpus": 0,
            "PidsLimit": 0,
            "Ulimits": None,
            "CpuCount": 0,
            "CpuPercent": 0,
            "IOMaximumIOps": 0,
            "IOMaximumBandwidth": 0
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
                extra={
                    "container_id": params.container_id,
                    "reset_resources": reset_resources
                }
            )
        else:
            logger.info(
                f"No resource limits to reset for container {params.container_id}",
                extra={"container_id": params.container_id}
            )
        
        return ToolResponse[ResetContainerResourcesResponse](
            success=True,
            data=ResetContainerResourcesResponse(
                container_id=container.id,
                reset_resources=reset_resources
            )
        )
        
    except NotFound as e:
        logger.error(
            f"Container not found: {params.container_id}",
            extra={"container_id": params.container_id},
            exc_info=True
        )
        return ToolResponse[ResetContainerResourcesResponse](
            success=False,
            error=f"Container not found: {str(e)}",
            error_code="not_found"
        )
    except APIError as e:
        logger.error(
            f"Docker API error: {str(e)}",
            extra={"container_id": params.container_id},
            exc_info=True
        )
        return ToolResponse[ResetContainerResourcesResponse](
            success=False,
            error=f"Docker API error: {str(e)}",
            error_code="docker_api_error"
        )
    except Exception as e:
        logger.error(
            f"Error resetting container resources: {str(e)}",
            extra={"container_id": params.container_id},
            exc_info=True
        )
        return ToolResponse[ResetContainerResourcesResponse](
            success=False,
            error=f"Error resetting container resources: {str(e)}",
            error_code="internal_error"
        )

# Register tools with FastMCP
def get_tools():
    """Return a list of tools for FastMCP to register."""
    return [
        get_container_resources,
        reset_container_resources
    ]
