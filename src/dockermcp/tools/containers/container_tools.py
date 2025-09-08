"""
Container Tools Facade for Docker MCP

This module provides a unified interface to container management functionality,
re-exporting tools from specialized modules for backward compatibility.

This is the recommended entry point for most container-related operations.
For advanced use cases, you can import directly from the specialized modules:

- `container_lifecycle.py`: Container lifecycle operations (create, start, stop, etc.)
- `container_logs.py`: Container log management
- `container_exec.py`: Command execution in containers
- `container_inspect.py`: Container inspection and monitoring
- `container_models.py`: Shared data models and request/response types

All functions in this module are registered as FastMCP tools and can be called
remotely via the FastMCP API.
"""
from __future__ import annotations

import logging
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, TypeVar, Union, cast

# Configure logging before other imports
from dockermcp.logging_config import logger, configure_logging
configure_logging()

# Import FastMCP components
from fastmcp.tools import tool
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError

# Import all container models and types for re-export
from .container_models import *

# Import tool implementations from specialized modules with clear aliases
# This makes it clear which functions are being re-exported
from .container_lifecycle import (
    list_containers as _list_containers,
    create_container as _create_container,
    start_container as _start_container,
    stop_container as _stop_container,
    restart_container as _restart_container,
    remove_container as _remove_container,
    prune_containers as _prune_containers,
    manage_container_lifecycle as _manage_container_lifecycle,
)

from .container_logs import (
    get_container_logs as _get_container_logs,
    stream_container_logs as _stream_container_logs,
)

from .container_exec import (
    execute_in_container as _execute_in_container,
    exec_command as _exec_command,
)

from .container_inspect import (
    inspect_container as _inspect_container,
    container_stats as _container_stats,
    container_top as _container_top,
)

# Import container manager and utilities
from .container_utils import (
    create_response,
    handle_error,
    container_mgr,
    run_docker_command,
)

# Type variables for generics
T = TypeVar('T', bound=BaseModel)
ContainerT = TypeVar('ContainerT', bound=BaseModel)

# Module-level logger
logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# Type variables for request/response models
T = TypeVar('T', bound=BaseModel)

# Tool Registration Helpers
# -----------------------------------------------------------------------------

# Tool registration helpers removed - using direct @Tool decorators in FastMCP 2.11.3+

# Container Tools Metadata
# -----------------------------------------------------------------------------

# Removed get_container_tools - get_tools_metadata not available in FastMCP 2.11.3+

# Container Lifecycle Tools
# -----------------------------------------------------------------------------

@tool(
    name="list_containers",
    description="List containers with optional filtering",
    args_schema=ListContainersRequest,
    return_schema=List[ContainerInfo]
)
async def list_containers(request: ListContainersRequest) -> List[ContainerInfo]:
    """
    List containers with optional filtering.
    
    This endpoint provides a way to list all containers on the Docker host with various
    filtering options. It's useful for discovering and monitoring containers.
    
    Args:
        request: ListContainersRequest object containing:
            - all (bool): If True, shows all containers (default shows just running)
            - limit (int): Maximum number of containers to return
            - size (bool): Return container size information
            - filters (Dict[str, Any]): Filter containers based on conditions.
              Common filters include:
                - name: Container name
                - status: One of 'created', 'restarting', 'running', 'removing',
                         'paused', 'exited', or 'dead'
                - label: Format either 'key' or 'key=value'
                - before: Only containers created before a container ID or name
                - since: Only containers created since a container ID or name
                - ancestor: Filter by image name or ID
                
    Returns:
        List[ContainerInfo]: A list of ContainerInfo objects containing:
            - id (str): The container ID
            - names (List[str]): The container names
            - image (str): The image used by the container
            - image_id (str): The ID of the container's image
            - command (str): The command used when starting the container
            - created (int): When the container was created (Unix timestamp)
            - state (str): The container's current state
            - status (str): The container's current status
            - ports (List[Port]): List of exposed ports
            - labels (Dict[str, str]): User-defined container labels
            - size_rw (int, optional): Size of files that have been created or changed
            - size_root_fs (int, optional): Total size of all files in the container
            - host_config (Dict[str, Any], optional): The container's host configuration
            - network_settings (Dict[str, Any], optional): Network settings
            - mounts (List[Dict[str, Any]], optional): Mount points in the container
    
    Raises:
        ToolError: If there's an error communicating with the Docker daemon
        
    Example:
        >>> request = ListContainersRequest(
        ...     all=True,
        ...     filters={"status": ["running"]}
        ... )
        >>> containers = await list_containers(request)
        >>> for container in containers:
        ...     print(f"{container.id[:12]} {container.names[0]} {container.status}")
    """
    try:
        return await _list_containers(request)
    except Exception as e:
        error_msg = f"Failed to list containers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

@tool(
    name="create_container",
    description="Create a new container with the specified configuration",
    args_schema=ContainerLifecycleRequest,
    return_schema=ContainerResponse
)
async def create_container(request: ContainerLifecycleRequest) -> ContainerResponse:
    """
    Create a new container.
    
    Args:
        request: ContainerLifecycleRequest with container configuration
            - image: Name of the image to use
            - command: Command to run in the container
            - environment: Environment variables
            - ports: Port mappings
            - volumes: Volume mounts
            - network_mode: Network mode (bridge, host, none)
            - name: Optional container name
            
    Returns:
        ContainerResponse with operation result including:
        - success: Boolean indicating success/failure
        - container_id: ID of the created container
        - warnings: Any warnings from container creation
        - error: Error message if creation failed
    """
    try:
        return await _create_container(request)
    except Exception as e:
        logger.error(f"Error creating container: {str(e)}")
        raise ToolError(f"Failed to create container: {str(e)}")

@tool(
    name="start_container",
    description="Start a stopped container with the specified configuration",
    args_schema=StartContainerRequest,
    return_schema=ContainerResponse
)
async def start_container(request: StartContainerRequest) -> ContainerResponse:
    """
    Start a stopped container.
    
    Args:
        request: StartContainerRequest with:
            - container_id: ID or name of the container to start
            - detach_keys: Override the key sequence for detaching a container
            
    Returns:
        ContainerResponse with operation result including:
        - success: Boolean indicating success/failure
        - container_id: ID of the container
        - warnings: Any warnings from the start operation
        - error: Error message if start failed
    """
    try:
        return await _start_container(request)
    except Exception as e:
        logger.error(f"Error starting container: {str(e)}")
        raise ToolError(f"Failed to start container: {str(e)}")

@tool(
    name="stop_container",
    description="Stop a running container with the specified configuration",
    args_schema=StopContainerRequest,
    return_schema=ContainerResponse
)
async def stop_container(request: StopContainerRequest) -> ContainerResponse:
    """
    Stop a running container.
    
    Args:
        request: StopContainerRequest with:
            - container_id: ID or name of the container to stop
            - timeout: Timeout in seconds to wait before killing the container
            
    Returns:
        ContainerResponse with operation result including:
        - success: Boolean indicating success/failure
        - container_id: ID of the container
        - warnings: Any warnings from the stop operation
        - error: Error message if stop failed
    """
    try:
        return await _stop_container(request)
    except Exception as e:
        logger.error(f"Error stopping container: {str(e)}")
        raise ToolError(f"Failed to stop container: {str(e)}")

@tool(
    name="restart_container",
    description="Restart a container with the specified configuration",
    args_schema=ContainerLifecycleRequest,
    return_schema=ContainerResponse
)
async def restart_container(request: ContainerLifecycleRequest) -> ContainerResponse:
    """
    Restart a container.
    
    Args:
        request: ContainerLifecycleRequest with:
            - container_id: ID or name of the container to restart
            - timeout: Timeout in seconds to wait before killing the container
            
    Returns:
        ContainerResponse with operation result including:
        - success: Boolean indicating success/failure
        - container_id: ID of the container
        - warnings: Any warnings from the restart operation
        - error: Error message if restart failed
    """
    try:
        return await _restart_container(request)
    except Exception as e:
        logger.error(f"Error restarting container: {str(e)}")
        raise ToolError(f"Failed to restart container: {str(e)}")

@tool(
    name="remove_container",
    description="Remove a container with the specified configuration",
    args_schema=ContainerLifecycleRequest,
    return_schema=ContainerResponse
)
async def remove_container(request: ContainerLifecycleRequest) -> ContainerResponse:
    """
    Remove a container.
    
    Args:
        request: ContainerLifecycleRequest with:
            - container_id: ID or name of the container to remove
            - force: Force removal of a running container
            - remove_volumes: Remove anonymous volumes associated with the container
            - link: Remove the specified link
            
    Returns:
        ContainerResponse with operation result including:
        - success: Boolean indicating success/failure
        - container_id: ID of the removed container
        - error: Error message if removal failed
    """
    try:
        return await _remove_container(request)
    except Exception as e:
        logger.error(f"Error removing container: {str(e)}")
        raise ToolError(f"Failed to remove container: {str(e)}")

@tool(
    name="prune_containers",
    description="Remove all stopped containers with the specified configuration",
    args_schema=PruneContainersRequest,
    return_schema=PruneContainersResponse
)
async def prune_containers(request: PruneContainersRequest) -> PruneContainersResponse:
    """
    Remove all stopped containers.
    
    Args:
        request: PruneContainersRequest with filter options
        
    Returns:
        PruneContainersResponse with results of the operation
    """
    from .container_lifecycle import prune_containers as _prune_containers
    return await _prune_containers(request)

# Container Logs Tools
# -----------------------------------------------------------------------------

@tool(
    name="get_container_logs",
    description="Get logs from a container with the specified configuration",
    args_schema=ContainerLogsRequest,
    return_schema=ContainerLogsResponse
)
async def get_container_logs(request: ContainerLogsRequest) -> ContainerLogsResponse:
    """
    Get logs from a container.
    
    Args:
        request: ContainerLogsRequest with log retrieval parameters
        
    Returns:
        ContainerLogsResponse with log entries
    """
    from .container_logs import get_container_logs as _get_container_logs
    return await _get_container_logs(request)

@tool(
    name="stream_container_logs",
    description="Stream logs from a container in real-time with the specified configuration",
    args_schema=ContainerLogsRequest,
    return_schema=AsyncGenerator[LogEntry, None]
)
async def stream_container_logs(request: ContainerLogsRequest) -> AsyncGenerator[LogEntry, None]:
    """
    Stream logs from a container in real-time.
    
    Args:
        request: ContainerLogsRequest with stream parameters
        
    Yields:
        LogEntry objects as they are received
    """
    from .container_logs import stream_container_logs as _stream_container_logs
    async for entry in _stream_container_logs(request):
        yield entry

# Container Execution Tools
# -----------------------------------------------------------------------------

@tool(
    name="execute_in_container",
    description="Execute a command in a running container with the specified configuration",
    args_schema=ContainerExecRequest,
    return_schema=ContainerExecResponse
)
async def execute_in_container(request: ContainerExecRequest) -> ContainerExecResponse:
    """
    Execute a command in a running container.
    
    Args:
        request: ContainerExecRequest with command and execution parameters
        
    Returns:
        ContainerExecResponse with command execution results
    """
    from .container_exec import execute_in_container as _execute_in_container
    return await _execute_in_container(request)

@tool(
    name="exec_command",
    description="Execute a command in a running container (legacy interface) with the specified configuration",
    args_schema=ExecCommandRequest,
    return_schema=ExecCommandResponse
)
async def exec_command(request: ExecCommandRequest) -> ExecCommandResponse:
    """
    Execute a command in a running container (legacy interface).
    
    Args:
        request: ExecCommandRequest with command and parameters
        
    Returns:
        ExecCommandResponse with command execution results
    """
    from .container_exec import exec_command as _exec_command
    return await _exec_command(request)

# Container Inspection Tools
# -----------------------------------------------------------------------------

@tool(
    name="inspect_container",
    description="Inspect a container with the specified configuration",
    args_schema=InspectContainerRequest,
    return_schema=ContainerInspectResponse
)
async def inspect_container(request: InspectContainerRequest) -> ContainerInspectResponse:
    """
    Inspect a container.
    
    Args:
        request: InspectContainerRequest with container ID and options
        
    Returns:
        ContainerInspectResponse with detailed container information
    """
    from .container_inspect import inspect_container as _inspect_container
    return await _inspect_container(request)

@tool(
    name="container_stats",
    description="Get container resource usage statistics with the specified configuration",
    args_schema=ContainerStatsRequest,
    return_schema=ContainerStatsResponse
)
async def container_stats(request: ContainerStatsRequest) -> ContainerStatsResponse:
    """
    Get container resource usage statistics.
    
    Args:
        request: ContainerStatsRequest with container ID and options
        
    Returns:
        ContainerStatsResponse with resource usage statistics
    """
    from .container_inspect import container_stats as _container_stats
    return await _container_stats(request)

@tool(
    name="container_top",
    description="Display the running processes of a container with the specified configuration",
    args_schema=ContainerTopRequest,
    return_schema=ContainerTopResponse
)
async def container_top(request: ContainerTopRequest) -> ContainerTopResponse:
    """
    Display the running processes of a container.
    
    Args:
        request: ContainerTopRequest with container ID and options
        
    Returns:
        ContainerTopResponse with process information
    """
    from .container_inspect import container_top as _container_top
    return await _container_top(request)

def get_tools() -> list:
    """
    Get all tools defined in this module for registration with FastMCP 2.12+.
    
    This function returns a list of tool functions that should be registered
    with the FastMCP tool registry. Each tool is decorated with @tool
    to provide metadata and enable remote invocation.
    
    Returns:
        List of tool functions to register with FastMCP
        
    Example:
        >>> from fastmcp.tools import tool
        >>> @tool()
        ... def my_tool():
        ...     pass
        >>> get_tools()
        [<function my_tool at 0x...>]
    """
    return [
        # Container lifecycle tools
        list_containers,
        create_container,
        start_container,
        stop_container,
        restart_container,
        remove_container,
        prune_containers,
        
        # Log tools
        get_container_logs,
        stream_container_logs,
        
        # Execution tools
        execute_in_container,
        exec_command,
        
        # Inspection tools
        inspect_container,
        container_stats,
        container_top,
    ]

# Public API
# -----------------------------------------------------------------------------
# This section defines the public interface of the module. Only symbols listed
# in __all__ will be available when importing from this module.

__all__ = [
    # Functions
    'get_tools',
    # Container Lifecycle Management
    'list_containers',
    'create_container',
    'start_container',
    'stop_container',
    'restart_container',
    'remove_container',
    'prune_containers',
    
    # Log Management
    'get_container_logs',
    'stream_container_logs',
    
    # Command Execution
    'execute_in_container',
    'exec_command',
    
    # Inspection and Monitoring
    'inspect_container',
    'container_stats',
    'container_top',
    
    # Models and Types
    'ContainerInfo',
    'ContainerLifecycleRequest',
    'ContainerLifecycleResponse',
    'ContainerLogsRequest',
    'ContainerLogsResponse',
    'ContainerExecRequest',
    'ContainerExecResponse',
    'ContainerInspectRequest',
    'ContainerInspectResponse',
    'ContainerStatsRequest',
    'ContainerStatsResponse',
    'ContainerTopRequest',
    'ContainerTopResponse',
    'ListContainersRequest',
    'StartContainerRequest',
    'StopContainerRequest',
    'PruneContainersRequest',
    'ExecCommandRequest',
    'InspectContainerRequest',
    
    # Utility functions
    'create_response',
    'handle_error',
    'container_mgr',
    'run_docker_command',
    
    # Container lifecycle functions
    'list_containers',
    'create_container',
    'start_container',
    'stop_container',
    'restart_container',
    'remove_container',
    'prune_containers',
    'manage_container_lifecycle',
    
    # Log functions
    'get_container_logs',
    'stream_container_logs',
    
    # Exec functions
    'execute_in_container',
    'exec_command',
    
    # Inspection functions
    'inspect_container',
    'container_stats',
    'container_top',
]


