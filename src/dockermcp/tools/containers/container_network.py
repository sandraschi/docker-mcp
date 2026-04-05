"""
Container networking for Docker MCP.

This module provides tools for managing container networks, including creating,
inspecting, and removing networks, as well as connecting/disconnecting containers.
It follows FastMCP 2.12+ standards for tool registration and error handling.
"""
from __future__ import annotations

import ipaddress
from enum import StrEnum
from typing import Any

import docker
from docker.errors import DockerException
from fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker Network MCP")

class NetworkDriver(StrEnum):
    """Supported Docker network drivers."""
    BRIDGE = "bridge"
    HOST = "host"
    OVERLAY = "overlay"
    MACVLAN = "macvlan"
    NONE = "none"

class IPAMConfig(BaseModel):
    """IP Address Management configuration for Docker networks."""
    subnet: str | None = Field(
        None,
        description="Subnet in CIDR format that represents a network segment"
    )
    ip_range: str | None = Field(
        None,
        description="Range of IPs from which to allocate container IPs"
    )
    gateway: str | None = Field(
        None,
        description="IPv4 or IPv6 gateway for the master subnet"
    )
    aux_addresses: dict[str, str] | None = Field(
        None,
        description="Auxiliary IPv4 or IPv6 addresses used by the network driver"
    )

    @field_validator('subnet', 'ip_range', 'gateway')
    @classmethod
    def validate_ip_address(cls, v):
        if v is None:
            return v
        try:
            if '/' in v:  # It's a subnet
                ipaddress.ip_network(v, strict=False)
            else:  # It's a single IP
                ipaddress.ip_address(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid IP address or subnet: {v}") from e

class NetworkCreateRequest(BaseModel):
    """Request model for creating a new Docker network."""
    name: str = Field(..., description="Name of the network")
    driver: NetworkDriver = Field(
        default=NetworkDriver.BRIDGE,
        description="Driver to manage the Network"
    )
    check_duplicate: bool = Field(
        default=True,
        description="Check for networks with duplicate names"
    )
    internal: bool = Field(
        default=False,
        description="Restrict external access to the network"
    )
    attachable: bool = Field(
        default=False,
        description="Enable manual container attachment"
    )
    ingress: bool = Field(
        default=False,
        description="Create an ingress network which provides the routing-mesh"
    )
    enable_ipv6: bool = Field(
        default=False,
        description="Enable IPv6 on the network"
    )
    ipam: IPAMConfig | None = Field(
        None,
        description="Optional custom IPAM config"
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Map of labels to set on the network"
    )

class ListNetworksParams(BaseModel):
    """Parameters for listing Docker networks."""
    names: list[str] = Field(
        default_factory=list,
        description="Filter by network names"
    )
    ids: list[str] = Field(
        default_factory=list,
        description="Filter by network IDs"
    )
    driver: str | None = Field(
        None,
        description="Filter by network driver"
    )
    scope: str | None = Field(
        None,
        description="Filter by network scope (local, swarm, global)"
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Filter by labels (key=value)"
    )
    detailed: bool = Field(
        False,
        description="Include detailed information about each network"
    )

class NetworkResponse(BaseModel):
    """Response model for network operations."""
    id: str = Field(..., description="Network ID")
    name: str = Field(..., description="Network name")
    driver: str = Field(..., description="Network driver")
    scope: str = Field(..., description="Network scope")
    ipam: dict[str, Any] = Field(..., description="IPAM configuration")
    containers: dict[str, Any] = Field(..., description="Connected containers")
    options: dict[str, Any] = Field(..., description="Network options")
    labels: dict[str, str] = Field(..., description="Network labels")
    created: str = Field(..., description="Creation timestamp")
    internal: bool = Field(..., description="Whether network is internal")
    enable_ipv6: bool = Field(..., description="IPv6 enabled")
    attachable: bool = Field(..., description="Manual attachment allowed")
    ingress: bool = Field(..., description="Ingress network")

@mcp.tool
async def list_networks(params: ListNetworksParams) -> dict[str, Any]:
    """
    List Docker networks with filtering options.

    This function provides a way to list all Docker networks with various filtering
    options. It can return either a summary or detailed information about each network.

    Args:
        params: ListNetworksParams containing:
            - names: Filter by network names
            - ids: Filter by network IDs
            - driver: Filter by network driver
            - scope: Filter by network scope
            - labels: Filter by labels
            - detailed: Include detailed information

    Returns:
        Dictionary with list of networks and metadata

    Example:
        >>> await list_networks(
        ...     ListNetworksParams(
        ...         driver="bridge",
        ...         detailed=True
        ...     )
        ... )
        {
            "status": "success",
            "networks": [...],
            "count": 1
        }
    """
    try:
        client = docker.from_env()

        # Build filters
        filters = {}
        if params.names:
            filters['name'] = params.names
        if params.ids:
            filters['id'] = params.ids
        if params.driver:
            filters['driver'] = params.driver
        if params.scope:
            filters['scope'] = params.scope
        if params.labels:
            filters['label'] = [f"{k}={v}" for k, v in params.labels.items()]

        # Get networks
        networks = client.networks.list(filters=filters)

        # Prepare response
        result = []
        for net in networks:
            net_info = {
                'id': net.id,
                'name': net.name,
                'driver': net.attrs.get('Driver', ''),
                'scope': net.attrs.get('Scope', ''),
                'ipam': net.attrs.get('IPAM', {}),
                'containers': {},
                'options': net.attrs.get('Options', {}),
                'labels': net.attrs.get('Labels', {}),
                'created': net.attrs.get('Created', ''),
                'internal': net.attrs.get('Internal', False),
                'enable_ipv6': net.attrs.get('EnableIPv6', False),
                'attachable': net.attrs.get('Attachable', False),
                'ingress': net.attrs.get('Ingress', False)
            }

            if params.detailed:
                net_info['containers'] = net.attrs.get('Containers', {})

            result.append(net_info)

        return {
            'status': 'success',
            'networks': result,
            'count': len(result)
        }

    except DockerException as e:
        logger.error(f"Docker error listing networks: {str(e)}")
        return {
            'status': 'error',
            'message': f"Failed to list networks: {str(e)}",
            'error_type': 'docker_error'
        }
    except Exception as e:
        logger.error(f"Unexpected error listing networks: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': 'An unexpected error occurred while listing networks',
            'error_type': 'unexpected_error'
        }
