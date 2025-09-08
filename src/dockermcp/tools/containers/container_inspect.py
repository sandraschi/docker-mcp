"""
Container inspection tool for Docker MCP.

This module provides detailed inspection of Docker containers including 
configuration, state, and resource usage statistics. It is compatible with 
FastMCP 2.12+ and follows the project's coding standards.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional, List, Union, TypeVar, Type, cast
from datetime import datetime

# Pydantic models
from pydantic import BaseModel, Field, ConfigDict

# Docker SDK
import docker
from docker.models.containers import Container
from docker.errors import DockerException, APIError, NotFound

# FastMCP imports
from fastmcp.tools import tool as Tool
from fastmcp.exceptions import ToolError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Type variables
T = TypeVar('T', bound=BaseModel)

class ContainerInspectRequest(BaseModel):
    """
    Request model for container inspection.
    
    Attributes:
        container_id: ID or name of the container to inspect
        show_stats: Whether to include live resource usage statistics
        show_logs: Whether to include recent container logs
        log_tail: Number of log lines to include if show_logs is True (1-1000)
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "show_stats": True,
                "show_logs": True,
                "log_tail": 50
            }
        }
    )
    
    container_id: str = Field(
        ...,
        min_length=1,
        description="ID or name of the container to inspect"
    )
    show_stats: bool = Field(
        default=False,
        description="Include live resource usage statistics"
    )
    show_logs: bool = Field(
        default=False,
        description="Include recent logs"
    )
    log_tail: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of log lines to include if show_logs is True"
    )

class ContainerInspectResponse(BaseModel):
    """
    Response model for container inspection.
    
    Attributes:
        id: Container ID
        name: Container name
        status: Current status (e.g., 'running', 'exited')
        state: Detailed state information
        config: Container configuration
        stats: Optional resource usage statistics
        logs: Optional recent container logs
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4e5f6",
                "name": "my-container",
                "status": "running",
                "state": {
                    "status": "running",
                    "running": True,
                    "paused": False,
                    "restarting": False,
                    "oom_killed": False,
                    "dead": False,
                    "pid": 1234,
                    "exit_code": 0,
                    "started_at": "2023-01-01T12:00:00Z"
                },
                "config": {
                    "image": "nginx:latest",
                    "env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
                    "cmd": ["nginx", "-g", "daemon off;"],
                    "working_dir": "/"
                },
                "stats": {
                    "cpu_percent": 1.23,
                    "memory_usage": 1024000,
                    "memory_limit": 4294967296,
                    "memory_percent": 0.24
                },
                "logs": [
                    "2023-01-01T12:00:00Z [notice] 1#1: start worker processes",
                    "2023-01-01T12:00:00Z [notice] 1#1: start worker process 10"
                ]
            }
        }
    )
    
    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    status: str = Field(..., description="Current status")
    state: Dict[str, Any] = Field(..., description="Detailed state information")
    config: Dict[str, Any] = Field(..., description="Container configuration")
    stats: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Resource usage statistics (if requested)"
    )
    logs: Optional[List[str]] = Field(
        default=None,
        description="Recent container logs (if requested)"
    )
    network_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Network settings and port mappings"
    )
    mounts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of volume mounts"
    )
    created: str = Field(..., description="ISO 8601 timestamp when container was created")
    image: str = Field(..., description="Name/ID of the container's image")
    command: str = Field(..., description="Command used to start the container")
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="User-defined key/value metadata"
    )
    ports: Dict[str, Any] = Field(
        default_factory=dict,
        description="Port mappings (published ports)"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables set in the container"
    )
    error: Optional[str] = None

@Tool.register(
    name="inspect_container",
    description="Inspect a Docker container and return detailed information"
)
async def inspect_container(request: ContainerInspectRequest) -> ContainerInspectResponse:
    """
    Inspect a Docker container and return detailed information.

    This function provides a comprehensive view of a container's configuration,
    state, and resource usage. It can optionally include live statistics and logs.

    Args:
        request: ContainerInspectRequest containing inspection parameters

    Returns:
        ContainerInspectResponse with detailed container information

    Raises:
        ToolError: If the container cannot be found or if there's an API error
        
    Example:
        ```python
        request = ContainerInspectRequest(
            container_id="my-container",
            show_stats=True,
            show_logs=True,
            log_tail=50
        )
        response = await inspect_container(request)
        ```
    """
    try:
        client = docker.from_env()
        
        try:
            container = client.containers.get(request.container_id)
        except NotFound as e:
            raise ToolError(f"Container {request.container_id} not found") from e
        except APIError as e:
            raise ToolError(f"Docker API error: {str(e)}") from e
        
        # Get basic container info
        container.reload()
        
        # Build response with required fields
        response_data = {
            "id": container.id,
            "name": container.name.lstrip('/'),  # Remove leading slash from name
            "status": container.status,
            "state": container.attrs.get("State", {}),
            "config": {
                "image": container.image.tags[0] if container.image.tags else container.image.id,
                "env": container.attrs.get("Config", {}).get("Env", []),
                "cmd": container.attrs.get("Config", {}).get("Cmd"),
                "working_dir": container.attrs.get("Config", {}).get("WorkingDir", "/")
            }
        }
        
        # Get stats if requested
        if request.show_stats:
            try:
                stats = container.stats(stream=False)
                response_data["stats"] = {
                    "cpu_percent": _calculate_cpu_percent(stats),
                    "memory_usage": stats.get("memory_stats", {}).get("usage", 0),
                    "memory_limit": stats.get("memory_stats", {}).get("limit", 0),
                    "memory_percent": _calculate_memory_percent(stats),
                    "network_io": stats.get("networks", {})
                }
            except Exception as e:
                logger.warning(f"Failed to get container stats: {str(e)}", exc_info=True)
                response_data["stats"] = {"error": f"Failed to retrieve stats: {str(e)}"}
        
        # Get logs if requested
        if request.show_logs:
            try:
                logs = container.logs(
                    tail=request.log_tail,
                    timestamps=True,
                    follow=False
                ).decode("utf-8")
                response_data["logs"] = logs.split("\n")[:-1]  # Remove last empty line
            except Exception as e:
                logger.warning(f"Failed to get container logs: {str(e)}", exc_info=True)
                response_data["logs"] = [f"Failed to retrieve logs: {str(e)}"]
        
        return ContainerInspectResponse(**response_data)
        
    except DockerException as e:
        logger.error(f"Docker error inspecting container: {str(e)}", exc_info=True)
        raise ToolError(f"Docker error: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error inspecting container: {str(e)}", exc_info=True)
        raise ToolError(f"Failed to inspect container: {str(e)}") from e

def _calculate_cpu_percent(stats: Dict[str, Any]) -> float:
    """
    Calculate CPU usage percentage from Docker stats.
    
    Args:
        stats: Docker stats dictionary from the container
        
    Returns:
        CPU usage as a percentage (0-100)
    """
    try:
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        
        cpu_usage = cpu_stats.get("cpu_usage", {})
        precpu_usage = precpu_stats.get("cpu_usage", {})
        
        cpu_delta = cpu_usage.get("total_usage", 0) - precpu_usage.get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 1) - precpu_stats.get("system_cpu_usage", 0)
        
        # Handle potential division by zero or missing data
        if system_delta <= 0 or cpu_delta < 0:
            return 0.0
            
        # Get number of CPUs, default to 1 if not available
        cpu_count = len(cpu_usage.get("percpu_usage") or [1])
        
        return min((cpu_delta / system_delta) * cpu_count * 100.0, 100.0)
        
    except Exception as e:
        logger.debug(f"Error calculating CPU percent: {str(e)}")
        return 0.0

def _calculate_memory_percent(stats: Dict[str, Any]) -> float:
    """
    Calculate memory usage percentage from Docker stats.
    
    Args:
        stats: Docker stats dictionary from the container
        
    Returns:
        Memory usage as a percentage (0-100)
    """
    try:
        memory_stats = stats.get("memory_stats", {})
        usage = memory_stats.get("usage", 0)
        limit = memory_stats.get("limit", 1)  # Avoid division by zero
        
        # Ensure we don't exceed 100% or go below 0%
        return max(0.0, min((usage / limit) * 100.0, 100.0))
        
    except Exception as e:
        logger.debug(f"Error calculating memory percent: {str(e)}")
        return 0.0

def get_tools() -> List[Tool]:
    """
    Get all tools defined in this module for registration with FastMCP.
    
    Returns:
        List of Tool instances to register
    """
    return [inspect_container]

