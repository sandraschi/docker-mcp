"""
Container management tools for Docker MCP.

This module provides FastMCP 2.12+ compatible tools for managing Docker containers.
"""
from typing import List
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError

# Import models
from .container_models import (
    ContainerInfo,
    ContainerResponse,
    ListContainersRequest,
    ContainerOperationRequest,
    CreateContainerRequest,
    StartContainerRequest,
    StopContainerRequest,
    RestartContainerRequest,
    RemoveContainerRequest,
    GetContainerLogsRequest,
    ContainerAction,
    ContainerLifecycleRequest,
    ContainerLifecycleResponse,
    LogStreamType,
    ContainerLogsRequest,
    LogEntry,
    ContainerLogsResponse,
    ExecStreamType,
    ExecUser,
    ContainerExecRequest,
    ExecResult,
    ContainerExecResponse
)

# Import tools
from .container_tools import (
    list_containers,
    get_container_info,
    create_container,
    start_container,
    stop_container,
    restart_container,
    remove_container,
    get_container_logs
)

# Import new container tools
from .container_lifecycle import manage_container_lifecycle
from .container_logs import stream_container_logs
from .container_exec import execute_in_container

# Tool registration
def get_tools() -> List[callable]:
    """
    Get all container management tools for registration with FastMCP 2.12+.
    
    Returns:
        List of @tool-decorated functions for all container management operations
    """
    return [
        list_containers,
        get_container_info,
        create_container,
        start_container,
        stop_container,
        restart_container,
        remove_container,
        get_container_logs,
        manage_container_lifecycle,
        stream_container_logs,
        execute_in_container
    ]

# Export public API
__all__ = [
    # Models
    'ContainerInfo',
    'ContainerResponse',
    'ListContainersRequest',
    'ContainerOperationRequest',
    'CreateContainerRequest',
    'StartContainerRequest',
    'StopContainerRequest',
    'RestartContainerRequest',
    'RemoveContainerRequest',
    'GetContainerLogsRequest',
    'ContainerAction',
    'ContainerLifecycleRequest',
    'ContainerLifecycleResponse',
    'LogStreamType',
    'ContainerLogsRequest',
    'LogEntry',
    'ContainerLogsResponse',
    'ExecStreamType',
    'ExecUser',
    'ExecResult',
    'ContainerExecResponse',
    
    # Tool functions
    'list_containers',
    'get_container_info',
    'create_container',
    'start_container',
    'stop_container',
    'restart_container',
    'remove_container',
    'get_container_logs',
    'manage_container_lifecycle',
    'stream_container_logs',
    'execute_in_container',
    
    # Tool registration
    'get_tools'
]
