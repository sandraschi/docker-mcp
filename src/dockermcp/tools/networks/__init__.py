"""
Network management tools for Docker MCP.

This module provides FastMCP 2.10.1 compatible tools for managing Docker networks.
"""
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
    'disconnect_container'
]
