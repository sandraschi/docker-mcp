"""
Docker System Management for FastMCP 2.12+

This module provides comprehensive tools for managing Docker system information,
including system information, disk usage analysis, and system cleanup operations.
"""
from __future__ import annotations

import re
from typing import Any

from docker.errors import DockerException
from pydantic import BaseModel, ConfigDict, Field

from dockermcp.docker_context import check_docker_available, docker_client
from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

# ============================================================================
# Request/Response Models
# ============================================================================

class SystemInfoRequest(BaseModel):
    """Request model for get_system_info tool."""
    model_config = ConfigDict(extra='forbid')

    include_disk_usage: bool = Field(
        default=True,
        json_schema_extra={"description": "Include disk usage information in the response"}
    )
    include_swarm_info: bool = Field(
        default=False,
        json_schema_extra={"description": "Include Docker Swarm information if available"}
    )

class SystemInfoResponse(BaseModel):
    """Response model for get_system_info tool."""
    model_config = ConfigDict(extra='forbid')

    status: str = Field(..., json_schema_extra={"description": "Status of the operation ('success' or 'error')"})
    system_info: dict[str, Any] | None = Field(
        default=None,
        json_schema_extra={"description": "Docker system information"}
    )
    error: str | None = Field(
        default=None,
        json_schema_extra={"description": "Error message if operation failed"}
    )

class DiskUsageRequest(BaseModel):
    """Request model for get_disk_usage tool."""
    model_config = ConfigDict(extra='forbid')

    detailed: bool = Field(
        default=True,
        json_schema_extra={"description": "Include detailed breakdown of disk usage"}
    )

class DiskUsageResponse(BaseModel):
    """Response model for get_disk_usage tool."""
    model_config = ConfigDict(extra='forbid')

    status: str = Field(..., json_schema_extra={"description": "Status of the operation ('success' or 'error')"})
    disk_usage: dict[str, Any] | None = Field(
        default=None,
        json_schema_extra={"description": "Disk usage information"}
    )
    error: str | None = Field(
        default=None,
        json_schema_extra={"description": "Error message if operation failed"}
    )

class PruneSystemRequest(BaseModel):
    """Request model for prune_system tool."""
    model_config = ConfigDict(extra='forbid')

    prune_containers: bool = Field(
        default=True,
        json_schema_extra={"description": "Remove stopped containers"}
    )
    prune_images: bool = Field(
        default=True,
        json_schema_extra={"description": "Remove dangling images"}
    )
    prune_networks: bool = Field(
        default=True,
        json_schema_extra={"description": "Remove unused networks"}
    )
    prune_volumes: bool = Field(
        default=False,
        json_schema_extra={"description": "Remove unused volumes (potentially dangerous)"}
    )
    prune_build_cache: bool = Field(
        default=True,
        json_schema_extra={"description": "Remove build cache"}
    )

class PruneSystemResponse(BaseModel):
    """Response model for prune_system tool."""
    model_config = ConfigDict(extra='forbid')

    status: str = Field(..., json_schema_extra={"description": "Status of the operation ('success' or 'error')"})
    pruned_data: dict[str, Any] | None = Field(
        default=None,
        json_schema_extra={"description": "Information about pruned resources"}
    )
    error: str | None = Field(
        default=None,
        json_schema_extra={"description": "Error message if operation failed"}
    )

class ParseDurationRequest(BaseModel):
    """Request model for parse_duration tool."""
    model_config = ConfigDict(extra='forbid')

    duration_string: str = Field(
        ...,
        json_schema_extra={"description": "Duration string to parse (e.g., '24h', '30m', '2d')"}
    )

class ParseDurationResponse(BaseModel):
    """Response model for parse_duration tool."""
    model_config = ConfigDict(extra='forbid')

    status: str = Field(..., json_schema_extra={"description": "Status of the operation ('success' or 'error')"})
    seconds: int | None = Field(
        default=None,
        json_schema_extra={"description": "Duration converted to seconds"}
    )
    error: str | None = Field(
        default=None,
        json_schema_extra={"description": "Error message if operation failed"}
    )

# ============================================================================
# Helper Functions
# ============================================================================

def format_bytes(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_names[i]}"

def parse_duration_string(duration_str: str) -> int:
    """Parse duration string into seconds."""
    duration_str = duration_str.strip().lower()

    # Match pattern like "24h", "30m", "2d", etc.
    match = re.match(r'^(\d+)([smhdw])$', duration_str)
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value, unit = match.groups()
    value = int(value)

    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }

    return value * multipliers[unit]

# ============================================================================
# Tool Implementations
# ============================================================================

@mcp.tool
@check_docker_available
async def get_system_info(
    request: SystemInfoRequest
) -> SystemInfoResponse:
    """
    Get comprehensive Docker system information.

    Args:
        request: SystemInfoRequest with options for what to include

    Returns:
        SystemInfoResponse with system information or error details
    """
    try:
        logger.info("Getting Docker system information")
        client = docker_client

        # Get basic system info
        info = client.info()
        version = client.version()

        system_data = {
            "docker_version": version.get("Version", "unknown"),
            "api_version": version.get("ApiVersion", "unknown"),
            "platform": version.get("Platform", {}).get("Name", "unknown"),
            "architecture": version.get("Arch", "unknown"),
            "kernel_version": version.get("KernelVersion", "unknown"),
            "operating_system": version.get("Os", "unknown"),
            "containers": {
                "total": info.get("Containers", 0),
                "running": info.get("ContainersRunning", 0),
                "paused": info.get("ContainersPaused", 0),
                "stopped": info.get("ContainersStopped", 0)
            },
            "images": {
                "total": info.get("Images", 0)
            },
            "memory": {
                "total": info.get("MemTotal", 0),
                "total_formatted": format_bytes(info.get("MemTotal", 0))
            },
            "cpu": {
                "cores": info.get("NCPU", 0)
            }
        }

        # Add disk usage if requested
        if request.include_disk_usage:
            try:
                df_info = client.df()
                system_data["disk_usage"] = {
                    "containers_size": df_info.get("Containers", []),
                    "images_size": df_info.get("Images", []),
                    "volumes_size": df_info.get("Volumes", []),
                    "build_cache_size": df_info.get("BuildCache", [])
                }
            except Exception as e:
                logger.warning(f"Could not get disk usage: {e}")
                system_data["disk_usage"] = {"error": str(e)}

        # Add swarm info if requested
        if request.include_swarm_info:
            try:
                swarm_attrs = client.swarm.attrs if hasattr(client, 'swarm') else None
                system_data["swarm"] = swarm_attrs
            except Exception as e:
                logger.warning(f"Could not get swarm info: {e}")
                system_data["swarm"] = {"error": str(e)}



        return SystemInfoResponse(
            status="success",
            system_info=system_data
        )

    except DockerException as e:
        error_msg = f"Docker error getting system info: {e!s}"
        logger.error(error_msg, exc_info=True)
        return SystemInfoResponse(
            status="error",
            error=error_msg
        )
    except Exception as e:
        error_msg = f"Unexpected error getting system info: {e!s}"
        logger.error(error_msg, exc_info=True)
        return SystemInfoResponse(
            status="error",
            error=error_msg
        )

@mcp.tool
@check_docker_available
async def get_disk_usage(
    request: DiskUsageRequest
) -> DiskUsageResponse:
    """
    Get detailed Docker disk usage information.

    Args:
        request: DiskUsageRequest with options for detail level

    Returns:
        DiskUsageResponse with disk usage information or error details
    """
    try:
        logger.info("Getting Docker disk usage information")
        client = docker_client

        # Get disk usage data
        df_info = client.df()

        disk_data = {
            "containers": [],
            "images": [],
            "volumes": [],
            "build_cache": [],
            "summary": {
                "total_containers_size": 0,
                "total_images_size": 0,
                "total_volumes_size": 0,
                "total_build_cache_size": 0,
                "total_size": 0
            }
        }

        # Process containers
        for container in df_info.get("Containers", []):
            size_rw = container.get("SizeRw", 0) or 0
            size_root_fs = container.get("SizeRootFs", 0) or 0
            disk_data["containers"].append({
                "id": container.get("Id", "unknown")[:12],
                "name": container.get("Names", ["unknown"])[0].lstrip("/"),
                "size_rw": size_rw,
                "size_root_fs": size_root_fs,
                "size_rw_formatted": format_bytes(size_rw),
                "size_root_fs_formatted": format_bytes(size_root_fs)
            })
            disk_data["summary"]["total_containers_size"] += size_rw

        # Process images
        for image in df_info.get("Images", []):
            size = image.get("Size", 0) or 0
            shared_size = image.get("SharedSize", 0) or 0
            disk_data["images"].append({
                "id": image.get("Id", "unknown").replace("sha256:", "")[:12],
                "repository": image.get("RepoTags", ["<none>"])[0] if image.get("RepoTags") else "<none>",
                "size": size,
                "shared_size": shared_size,
                "size_formatted": format_bytes(size),
                "shared_size_formatted": format_bytes(shared_size)
            })
            disk_data["summary"]["total_images_size"] += size

        # Process volumes
        for volume in df_info.get("Volumes", []):
            usage_data = volume.get("UsageData", {}) or {}
            size = usage_data.get("Size", 0) or 0
            disk_data["volumes"].append({
                "name": volume.get("Name", "unknown"),
                "size": size,
                "size_formatted": format_bytes(size),
                "ref_count": usage_data.get("RefCount", 0)
            })
            disk_data["summary"]["total_volumes_size"] += size

        # Process build cache
        for cache in df_info.get("BuildCache", []):
            size = cache.get("Size", 0) or 0
            disk_data["build_cache"].append({
                "id": cache.get("ID", "unknown")[:12],
                "size": size,
                "size_formatted": format_bytes(size),
                "in_use": cache.get("InUse", False),
                "shared": cache.get("Shared", False)
            })
            disk_data["summary"]["total_build_cache_size"] += size

        # Calculate total
        summary = disk_data["summary"]
        summary["total_size"] = (
            summary["total_containers_size"] +
            summary["total_images_size"] +
            summary["total_volumes_size"] +
            summary["total_build_cache_size"]
        )

        # Add formatted totals
        summary["total_containers_size_formatted"] = format_bytes(summary["total_containers_size"])
        summary["total_images_size_formatted"] = format_bytes(summary["total_images_size"])
        summary["total_volumes_size_formatted"] = format_bytes(summary["total_volumes_size"])
        summary["total_build_cache_size_formatted"] = format_bytes(summary["total_build_cache_size"])
        summary["total_size_formatted"] = format_bytes(summary["total_size"])



        return DiskUsageResponse(
            status="success",
            disk_usage=disk_data
        )

    except DockerException as e:
        error_msg = f"Docker error getting disk usage: {e!s}"
        logger.error(error_msg, exc_info=True)
        return DiskUsageResponse(
            status="error",
            error=error_msg
        )
    except Exception as e:
        error_msg = f"Unexpected error getting disk usage: {e!s}"
        logger.error(error_msg, exc_info=True)
        return DiskUsageResponse(
            status="error",
            error=error_msg
        )

@mcp.tool
@check_docker_available
async def prune_system(
    request: PruneSystemRequest
) -> PruneSystemResponse:
    """
    Prune unused Docker system resources.

    Args:
        request: PruneSystemRequest with options for what to prune

    Returns:
        PruneSystemResponse with information about pruned resources
    """
    try:
        logger.info("Starting Docker system prune operation")
        client = docker_client

        pruned_data = {
            "containers_pruned": [],
            "images_pruned": [],
            "networks_pruned": [],
            "volumes_pruned": [],
            "build_cache_pruned": [],
            "total_space_reclaimed": 0
        }

        # Prune containers
        if request.prune_containers:
            try:
                result = client.containers.prune()
                pruned_data["containers_pruned"] = result.get("ContainersDeleted", [])
                pruned_data["total_space_reclaimed"] += result.get("SpaceReclaimed", 0)
                logger.info(f"Pruned {len(pruned_data['containers_pruned'])} containers")
            except Exception as e:
                logger.warning(f"Failed to prune containers: {e}")

        # Prune images
        if request.prune_images:
            try:
                result = client.images.prune(filters={"dangling": True})
                pruned_data["images_pruned"] = result.get("ImagesDeleted", [])
                pruned_data["total_space_reclaimed"] += result.get("SpaceReclaimed", 0)
                logger.info(f"Pruned {len(pruned_data['images_pruned'])} images")
            except Exception as e:
                logger.warning(f"Failed to prune images: {e}")

        # Prune networks
        if request.prune_networks:
            try:
                result = client.networks.prune()
                pruned_data["networks_pruned"] = result.get("NetworksDeleted", [])
                logger.info(f"Pruned {len(pruned_data['networks_pruned'])} networks")
            except Exception as e:
                logger.warning(f"Failed to prune networks: {e}")

        # Prune volumes (optional, potentially dangerous)
        if request.prune_volumes:
            try:
                result = client.volumes.prune()
                pruned_data["volumes_pruned"] = result.get("VolumesDeleted", [])
                pruned_data["total_space_reclaimed"] += result.get("SpaceReclaimed", 0)
                logger.info(f"Pruned {len(pruned_data['volumes_pruned'])} volumes")
            except Exception as e:
                logger.warning(f"Failed to prune volumes: {e}")

        # Prune build cache
        if request.prune_build_cache:
            try:
                # Build cache pruning via low-level API
                result = client.api.prune_builds()
                pruned_data["build_cache_pruned"] = result.get("CachesDeleted", [])
                pruned_data["total_space_reclaimed"] += result.get("SpaceReclaimed", 0)
                logger.info("Pruned build cache")
            except Exception as e:
                logger.warning(f"Failed to prune build cache: {e}")

        # Format the space reclaimed
        pruned_data["total_space_reclaimed_formatted"] = format_bytes(
            pruned_data["total_space_reclaimed"]
        )



        return PruneSystemResponse(
            status="success",
            pruned_data=pruned_data
        )

    except DockerException as e:
        error_msg = f"Docker error during system prune: {e!s}"
        logger.error(error_msg, exc_info=True)
        return PruneSystemResponse(
            status="error",
            error=error_msg
        )
    except Exception as e:
        error_msg = f"Unexpected error during system prune: {e!s}"
        logger.error(error_msg, exc_info=True)
        return PruneSystemResponse(
            status="error",
            error=error_msg
        )

@mcp.tool
async def parse_duration(
    request: ParseDurationRequest
) -> ParseDurationResponse:
    """
    Parse a duration string into seconds.

    Args:
        request: ParseDurationRequest with duration string to parse

    Returns:
        ParseDurationResponse with parsed duration in seconds
    """
    try:
        logger.info(f"Parsing duration string: {request.duration_string}")

        seconds = parse_duration_string(request.duration_string)

        return ParseDurationResponse(
            status="success",
            seconds=seconds
        )

    except ValueError as e:
        error_msg = f"Invalid duration format: {e!s}"
        logger.error(error_msg)
        return ParseDurationResponse(
            status="error",
            error=error_msg
        )
    except Exception as e:
        error_msg = f"Unexpected error parsing duration: {e!s}"
        logger.error(error_msg, exc_info=True)
        return ParseDurationResponse(
            status="error",
            error=error_msg
        )

# ============================================================================
# Module exports
# ============================================================================

__all__ = [
    "DiskUsageRequest",
    "DiskUsageResponse",
    "ParseDurationRequest",
    "ParseDurationResponse",
    "PruneSystemRequest",
    "PruneSystemResponse",
    "SystemInfoRequest",
    "SystemInfoResponse",
    "get_disk_usage",
    "get_system_info",
    "parse_duration",
    "prune_system"
]
