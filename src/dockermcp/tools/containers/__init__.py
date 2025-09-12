"""
Container management tools for Docker MCP.

This module provides FastMCP 2.12.0 compatible tools for managing Docker containers.
"""
from typing import List

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

# Import tools - these are decorated functions, not Tool classes
from .list_containers import list_containers
from .container_tools import (
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

# Import refactored inspection tools
from .container_inspect_v2 import inspect_container


# FastMCP 2.12+ uses decorators - tools are automatically discovered by the @Tool decorator
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
    'ContainerExecRequest',
    'ExecResult',
    'ContainerExecResponse',
    
    # Core functions
    'list_containers',
    'create_container',
    'start_container',
    'stop_container',
    'restart_container',
    'remove_container',
    'get_container_info',
    'get_container_logs',
    'manage_container_lifecycle',
    'stream_container_logs',
    'execute_in_container',
    'inspect_container',
    
    # Registration function
    'get_container_tools'
]
