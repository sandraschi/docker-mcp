"""
Network tools package for Docker MCP.

This package provides comprehensive network management tools following
FastMCP 2.12+ standards.
"""

# Import network tools to register them with FastMCP
from .network_management import (
    NetworkConnectResponse,
    NetworkCreateResponse,
    NetworkDisconnectResponse,
    NetworkInspectResponse,
    NetworkListResponse,
    connect_container_to_network,
    create_network,
    disconnect_container_from_network,
    inspect_network,
    list_networks,
    remove_network,
)

__all__ = [
    "NetworkConnectResponse",
    "NetworkCreateResponse",
    "NetworkDisconnectResponse",
    "NetworkInspectResponse",
    "NetworkListResponse",
    "connect_container_to_network",
    "create_network",
    "disconnect_container_from_network",
    "inspect_network",
    "list_networks",
    "remove_network",
]
