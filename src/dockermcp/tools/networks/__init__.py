"""
Network management tools for Docker MCP.

This module provides FastMCP 2.12.0 compatible tools for managing Docker networks.
"""
from typing import List
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError

# Import models
from .network_models import (
    NetworkInfo,
    NetworkResponse,
    NetworkListResponse,
    CreateNetworkRequest,
    NetworkOperationRequest,
    ConnectContainerRequest,
    DisconnectContainerRequest
)

# Import tools
from .network_tools import (
    list_networks,
    create_network,
    inspect_network,
    remove_network,
    connect_container,
    disconnect_container
)

# Tool registration
def get_tools() -> List[callable]:
    """
    Get all network management tools for registration with FastMCP 2.12+.
    
    Returns:
        List of @tool-decorated functions for all network management operations
    """
    return [
        list_networks,
        create_network,
        inspect_network,
        remove_network,
        connect_container,
        disconnect_container
    ]

# Export public API
__all__ = [
    # Models
    'NetworkInfo',
    'NetworkResponse',
    'NetworkListResponse',
    'CreateNetworkRequest',
    'NetworkOperationRequest',
    'ConnectContainerRequest',
    'DisconnectContainerRequest',
    
    # Tools
    'list_networks',
    'create_network',
    'inspect_network',
    'remove_network',
    'connect_container',
    'disconnect_container',
    
    # Tool registration
    'get_tools'
]
