"""
Docker Compose Tools for DockerMCP.

This module provides FastMCP 2.12.0+ compatible tools for managing Docker Compose applications.
Tools are automatically discovered using the @Tool decorator.
"""
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolException

# Import models and tools
from .compose_models import *
from .compose_tools import (
    compose_up,
    compose_down,
    compose_build,
    compose_logs,
    compose_ps,
    compose_config,
    compose_exec,
    compose_run
)

__all__ = [
    # Models
    'ComposeProject',
    'ComposeService',
    'ComposeVolume',
    'ComposeNetwork',
    'ComposeConfig',
    'ComposeUpRequest',
    'ComposeDownRequest',
    'ComposeBuildRequest',
    'ComposeLogsRequest',
    'ComposePsRequest',
    'ComposeResponse',
    
    # Tools
    'get_tools',
    'compose_up',
    'compose_down',
    'compose_build',
    'compose_logs',
    'compose_ps',
    'compose_config',
    'compose_exec',
    'compose_run',
]
