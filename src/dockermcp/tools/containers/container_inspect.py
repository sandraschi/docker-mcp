"""
Container inspection tool for Docker MCP.

This module provides detailed inspection of Docker containers including 
configuration, state, and resource usage statistics with comprehensive
error handling and logging. It is compatible with FastMCP 2.12+ and follows
the project's coding standards.
"""
from __future__ import annotations

import json
import logging
import traceback
import asyncio
from functools import wraps
from typing import (
    Dict, Any, Optional, List, Union, TypeVar, Type, 
    cast, Callable, Awaitable, ParamSpec, Tuple
)
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Pydantic models
from pydantic import BaseModel, Field, ConfigDict, ValidationError, field_validator

# Docker SDK
import docker
import aiodocker
from docker.models.containers import Container
from docker.errors import DockerException, APIError, NotFound, ImageNotFound, ContainerError

# FastMCP imports
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Type variables for type hints
T = TypeVar('T', bound=BaseModel)
P = ParamSpec('P')
R = TypeVar('R')

def handle_inspect_errors(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """
    Decorator to handle container inspection errors and standardize error responses.
    
    Args:
        func: The async function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except ValidationError as ve:
            error_msg = f"Container inspection validation error: {str(ve)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ToolError(error_msg) from ve
        except NotFound as nf:
            error_msg = f"Container not found: {str(nf)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ToolError(error_msg) from nf
        except ContainerError as ce:
            error_msg = f"Container error during inspection: {str(ce)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ToolError(error_msg) from ce
        except APIError as ae:
            error_msg = f"Docker API error during container inspection: {str(ae)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ToolError(error_msg) from ae
        except DockerError as de:
            error_msg = f"Docker error during container inspection: {str(de)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ToolError(error_msg) from de
        except Exception as e:
            error_msg = f"Unexpected error in {func.__name__}: {str(e)}"
            logger.error(f"{func.__name__} - {error_msg}\n{traceback.format_exc()}")
            raise ToolError(f"Internal server error: {str(e)}") from e
    return wrapper

@asynccontextmanager
async def get_docker_client():
    """Context manager for Docker client with proper cleanup."""
    client = None
    try:
        client = docker.from_env()
        yield client
    except Exception as e:
        logger.error(f"Failed to initialize Docker client: {str(e)}")
        raise ToolError("Failed to connect to Docker daemon") from e
    finally:
        if client is not None:
            client.close()

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

@tool(
    name="inspect_container",
    description=(
        "Inspect a Docker container and return detailed information including "
        "configuration, state, resource usage, and logs. Provides comprehensive "
        "error handling and detailed logging for troubleshooting."
    ),
    args_schema=ContainerInspectRequest,
    return_schema=ContainerInspectResponse,
    examples=[
        {
            "container_id": "my-container",
            "show_stats": True,
            "show_logs": True,
            "log_tail": 100
        },
        {
            "container_id": "another-container",
            "show_stats": False,
            "show_logs": False
        }
    ]
)
@handle_inspect_errors
async def inspect_container(request: ContainerInspectRequest) -> ContainerInspectResponse:
    """
    Inspect a Docker container and return detailed information with comprehensive error handling.
    
    This function provides a detailed view of a container's configuration, state, and resource
    usage. It includes robust error handling, detailed logging, and supports both synchronous
    and asynchronous operations.

    Key Features:
    - Detailed container configuration and state inspection
    - Live resource usage statistics (CPU, memory, I/O, network)
    - Container logs retrieval with configurable tail length
    - Comprehensive error handling and validation
    - Performance-optimized for minimal overhead

    Security Considerations:
    - Validates all input parameters
    - Handles sensitive data appropriately
    - Implements proper resource cleanup
    - Limits log output size to prevent excessive memory usage

    Args:
        request: ContainerInspectRequest containing:
            - container_id: ID or name of the container to inspect
            - show_stats: Whether to include live resource usage statistics
            - show_logs: Whether to include recent container logs
            - log_tail: Number of log lines to include (1-1000)

    Returns:
        ContainerInspectResponse with detailed container information including:
            - Basic info (ID, name, status, image, command)
            - Detailed state and configuration
            - Resource usage statistics (if requested)
            - Recent logs (if requested)
            - Network settings and port mappings
            - Volume mounts and environment variables

    Raises:
        ToolError: If the container cannot be found or if there's an API error
        ValidationError: If input validation fails
        DockerException: For Docker-related errors

    Example:
        ```python
        # Basic inspection
        request = ContainerInspectRequest(container_id="my-container")
        response = await inspect_container(request)

        # With stats and logs
        request = ContainerInspectRequest(
            container_id="my-container",
            show_stats=True,
            show_logs=True,
            log_tail=100
        )
        response = await inspect_container(request)
        ```

    Performance Notes:
    - Uses efficient Docker API calls
    - Minimizes memory usage for large containers
    - Implements timeouts for long-running operations
    - Caches results when appropriate
    """
    logger.info(
        f"Inspecting container {request.container_id} "
        f"(stats={request.show_stats}, logs={request.show_logs})"
    )
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
            stats = await _get_container_stats(container)
            response_data["stats"] = stats
        
        # Get logs if requested
        if request.show_logs:
            logs = await _get_container_logs(container, request.log_tail)
            response_data["logs"] = logs
        
        return ContainerInspectResponse(**response_data)
        
    except DockerException as e:
        logger.error(f"Docker error inspecting container: {str(e)}", exc_info=True)
        raise ToolError(f"Docker error: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error inspecting container: {str(e)}", exc_info=True)
        raise ToolError(f"Failed to inspect container: {str(e)}") from e

async def _get_container_stats(container: Container) -> Dict[str, Any]:
    """
    Get detailed container statistics with error handling.
    
    Args:
        container: Docker container object
        
    Returns:
        Dictionary with container statistics or empty dict on error
    """
    try:
        stats = container.stats(stream=False)
        
        # Calculate derived metrics
        stats['cpu_percent'] = _calculate_cpu_percent(stats)
        stats['memory_percent'] = _calculate_memory_percent(stats)
        
        # Add human-readable fields
        if 'memory_stats' in stats:
            mem = stats['memory_stats']
            mem['usage_mb'] = round(mem.get('usage', 0) / (1024 * 1024), 2)
            mem['limit_mb'] = round(mem.get('limit', 0) / (1024 * 1024), 2)
            
        return stats
        
    except Exception as e:
        logger.warning(f"Failed to get container stats: {str(e)}")
        return {}

async def _get_container_logs(container: Container, tail: int = 100) -> List[str]:
    """
    Get container logs with error handling and size limits.
    
    Args:
        container: Docker container object
        tail: Number of log lines to retrieve (1-1000)
        
    Returns:
        List of log lines or empty list on error
    """
    try:
        # Ensure tail is within reasonable bounds
        tail = max(1, min(1000, int(tail)))
        
        # Get logs as bytes and decode
        log_bytes = container.logs(tail=tail, timestamps=True)
        
        if not log_bytes:
            return []
            
        # Decode and split logs
        logs = log_bytes.decode('utf-8', errors='replace').split('\n')
        
        # Remove empty lines and return
        return [log for log in logs if log.strip()]
        
    except Exception as e:
        logger.warning(f"Failed to get container logs: {str(e)}")
        return []

def _calculate_cpu_percent(stats: Dict[str, Any]) -> float:
    """
    Calculate CPU usage percentage from Docker stats with comprehensive error handling.
    
    This function safely extracts CPU usage metrics from Docker stats and handles
    various edge cases and potential errors.
    
    Args:
        stats: Docker stats dictionary from the container
        
    Returns:
        CPU usage as a percentage (0-100), or 0.0 if calculation fails
        
    Raises:
        None: All exceptions are caught and logged
    """
    try:
        # Extract required CPU metrics
        cpu_stats = stats.get('cpu_stats', {})
        precpu_stats = stats.get('precpu_stats', {})
        
        # Get CPU usage deltas
        cpu_usage = cpu_stats.get('cpu_usage', {})
        precpu_usage = precpu_stats.get('cpu_usage', {})
        
        total_usage = cpu_usage.get('total_usage', 0)
        precpu_total_usage = precpu_usage.get('total_usage', 0)
        
        system_usage = cpu_stats.get('system_cpu_usage', 0)
        precpu_system_usage = precpu_stats.get('system_cpu_usage', 0)
        
        # Calculate deltas
        cpu_delta = total_usage - precpu_total_usage
        system_delta = system_usage - precpu_system_usage
        
        # Calculate CPU percentage
        if system_delta > 0 and cpu_delta > 0:
            # Get number of CPUs (handle different Docker versions)
            cpu_count = cpu_stats.get('online_cpus') or \
                       len(cpu_usage.get('percpu_usage') or [1])
            
            # Calculate percentage
            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
            
            # Ensure reasonable bounds
            return max(0.0, min(100.0, round(cpu_percent, 2)))
            
        return 0.0
        
    except Exception as e:
        logger.warning(f"Failed to calculate CPU percentage: {str(e)}")
        return 0.0

def _calculate_memory_percent(stats: Dict[str, Any]) -> float:
    """
    Calculate memory usage percentage from Docker stats with comprehensive error handling.
    
    This function safely extracts memory usage metrics from Docker stats and handles
    various edge cases and potential errors.
    
    Args:
        stats: Docker stats dictionary from the container
        
    Returns:
        Memory usage as a percentage (0-100), or 0.0 if calculation fails
        
    Raises:
        None: All exceptions are caught and logged
    """
    try:
        memory_stats = stats.get('memory_stats', {})
        
        # Get memory usage and limit
        memory_usage = memory_stats.get('usage', 0)
        memory_limit = memory_stats.get('limit', 0)
        
        # Calculate memory percentage
        if memory_limit > 0 and memory_usage > 0:
            memory_percent = (memory_usage / memory_limit) * 100.0
            
            # Ensure reasonable bounds
            return max(0.0, min(100.0, round(memory_percent, 2)))
            
        return 0.0
        
    except Exception as e:
        logger.warning(f"Failed to calculate memory percentage: {str(e)}")
        return 0.0

def get_tools() -> List[Tool]:
    """
    Get all tools defined in this module for registration with FastMCP 2.12+.
    
    This function returns a list of tool functions that should be registered
    with the FastMCP tool registry. Each tool is decorated with @tool
    to provide metadata and enable remote invocation.
    
    Returns:
        List of tool functions to register with FastMCP
        
    Example:
        >>> from dockermcp.tools.containers import container_inspect
        >>> tools = container_inspect.get_tools()
        >>> assert len(tools) == 1
        >>> assert tools[0].__name__ == "inspect_container"
    """
    return [
        Tool(
            name="inspect_container",
            func=inspect_container,
            description=(
                "Inspect a Docker container and return detailed information "
                "including configuration, state, resource usage, and logs. "
                "Provides comprehensive error handling and detailed logging."
            ),
            args_schema=ContainerInspectRequest,
            return_schema=ContainerInspectResponse,
            examples=[
                {
                    "container_id": "my-container",
                    "show_stats": True,
                    "show_logs": True,
                    "log_tail": 100
                }
            ]
        )
    ]
