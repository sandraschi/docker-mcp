"""
Container inspection tool for Docker MCP.

This module provides detailed inspection of Docker containers including 
configuration, state, and resource usage statistics with comprehensive
error handling and logging. It follows FastMCP 2.12+ standards.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List, TypeVar, Generic, Type

import docker
from docker.errors import DockerException, APIError, NotFound
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, ConfigDict

# Import logger directly to avoid circular imports
logger = logging.getLogger(__name__)

# Type variable for generic response
T = TypeVar('T')

# Constants
DEFAULT_LOG_TAIL = 100
MAX_LOG_LINES = 1000

def _calculate_cpu_percent(stats: Dict[str, Any]) -> float:
    """Calculate CPU usage percentage from Docker stats."""
    try:
        cpu_stats = stats.get('cpu_stats', {})
        precpu_stats = stats.get('precpu_stats', {})
        
        cpu_usage = cpu_stats.get('cpu_usage', {})
        precpu_usage = precpu_stats.get('cpu_usage', {})
        
        cpu_delta = cpu_usage.get('total_usage', 0) - precpu_usage.get('total_usage', 0)
        system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu_stats.get('system_cpu_usage', 0)
        
        if system_delta > 0 and cpu_delta > 0:
            return (cpu_delta / system_delta) * 100.0 * len(cpu_usage.get('percpu_usage', [1]))
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    
    return 0.0

def _calculate_memory_usage(stats: Dict[str, Any]) -> Dict[str, int]:
    """Calculate memory usage from Docker stats."""
    try:
        memory_stats = stats.get('memory_stats', {})
        usage = memory_stats.get('usage', 0)
        limit = memory_stats.get('limit', 1)  # Avoid division by zero
        
        return {
            'usage': usage,
            'limit': limit,
            'percent': (usage / limit) * 100.0 if limit > 0 else 0.0
        }
    except (KeyError, TypeError, ZeroDivisionError):
        return {'usage': 0, 'limit': 0, 'percent': 0.0}

def _get_network_io(stats: Dict[str, Any]) -> Dict[str, int]:
    """Extract network I/O statistics from container stats."""
    try:
        networks = stats.get('networks', {})
        rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
        tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())
        return {'rx_bytes': rx_bytes, 'tx_bytes': tx_bytes}
    except (AttributeError, TypeError):
        return {'rx_bytes': 0, 'tx_bytes': 0}

# Define response models first to avoid circular imports
class BaseResponse(BaseModel, Generic[T]):
    status: str = Field(..., description="Status of the operation (success/error)")
    message: Optional[str] = Field(None, description="Human-readable message")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if operation failed")

class ContainerInspectRequest(BaseModel):
    """Request model for container inspection."""
    container_id: str = Field(..., description="ID or name of the container to inspect")
    show_stats: bool = Field(False, description="Whether to include resource usage statistics")
    show_logs: bool = Field(False, description="Whether to include container logs")
    log_tail: int = Field(
        DEFAULT_LOG_TAIL,
        ge=1,
        le=MAX_LOG_LINES,
        description=f"Number of log lines to include (1-{MAX_LOG_LINES})"
    )


class ContainerInspectResponse(BaseModel):
    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Container image")
    status: str = Field(..., description="Container status")
    state: Dict[str, Any] = Field(..., description="Container state details")
    created: str = Field(..., description="Creation timestamp")
    config: Dict[str, Any] = Field(..., description="Container configuration")
    host_config: Dict[str, Any] = Field(..., description="Host configuration")
    network_settings: Dict[str, Any] = Field(..., description="Network settings")
    mounts: List[Dict[str, Any]] = Field(..., description="Volume mounts")
    environment: Dict[str, str] = Field(..., description="Environment variables")
    labels: Dict[str, str] = Field(..., description="Container labels")
    
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
        }
    )

async def _inspect_container_impl(request: ContainerInspectRequest) -> Dict[str, Any]:
    """
    Inspect a Docker container and return detailed information.
    
    Args:
        request: ContainerInspectRequest instance containing container ID and inspection options
        
    Returns:
        Dictionary containing container information, status, and optionally logs and stats
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get container by ID or name
        container = client.containers.get(request.container_id)
        
        # Get container attributes
        attrs = container.attrs
        
        # Prepare basic response
        response = {
            "id": attrs["Id"],
            "name": attrs["Name"].lstrip('/'),  # Remove leading slash from name
            "image": attrs["Config"]["Image"],
            "status": attrs["State"]["Status"],
            "state": attrs["State"],
            "created": attrs["Created"],
            "config": attrs["Config"],
            "host_config": attrs["HostConfig"],
            "network_settings": attrs["NetworkSettings"],
            "mounts": attrs.get("Mounts", []),
            "environment": {},
            "labels": attrs["Config"].get("Labels", {})
        }
        
        # Parse environment variables
        if "Env" in attrs["Config"]:
            for env_var in attrs["Config"]["Env"]:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    response["environment"][key] = value
        
        # Include stats if requested
        if request.show_stats:
            try:
                stats = next(container.stats(stream=False, decode=True))
                response["stats"] = {
                    "cpu_percent": _calculate_cpu_percent(stats),
                    "memory_usage": _calculate_memory_usage(stats),
                    "network_io": _get_network_io(stats)
                }
            except Exception as e:
                logger.warning(f"Failed to get container stats: {e}")
                response["stats"] = None
        
        # Include logs if requested
        if request.show_logs:
            try:
                logs = container.logs(
                    tail=request.log_tail,
                    timestamps=False,
                    stderr=True,
                    stdout=True
                ).decode("utf-8")
                response["logs"] = logs.splitlines()
            except Exception as e:
                logger.warning(f"Failed to get container logs: {e}")
                response["logs"] = None
                
        return response
        
    except NotFound as e:
        error_msg = f"Container not found: {request.container_id}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "container_id": request.container_id
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "container_id": request.container_id
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": "Docker daemon not available",
            "error": str(e),
            "container_id": request.container_id
        }
        
    except Exception as e:
        error_msg = f"Error inspecting container {request.container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "container_id": request.container_id
        }

# Public interface function
async def inspect_container(params: ContainerInspectRequest) -> Dict[str, Any]:
    """Public interface for container inspection."""
    return await _inspect_container_impl(params)

# Alias for compatibility with container_management.py
ContainerInspectParams = ContainerInspectRequest
