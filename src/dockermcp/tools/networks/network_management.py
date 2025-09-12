"""
Docker Network Management for FastMCP 2.12+

This module provides comprehensive tools for managing Docker networks including:
- Creating and removing networks
- Connecting and disconnecting containers
- Inspecting network details
- Listing and filtering networks
- Managing IPAM (IP Address Management) configurations
"""
from __future__ import annotations

import ipaddress
import json
import logging
from datetime import datetime
from enum import Enum
from ipaddress import IPv4Network, IPv6Network
from typing import Any, Dict, List, Optional, Union, Literal

import docker
from docker.errors import (
    DockerException, APIError, NotFound, 
    InvalidArgument, ContainerError
)
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, validator, HttpUrl, IPvAnyAddress, IPvAnyNetwork

from dockermcp.logging_config import logger

class NetworkDriver(str, Enum):
    """Supported Docker network drivers."""
    BRIDGE = "bridge"
    HOST = "host"
    OVERLAY = "overlay"
    MACVLAN = "macvlan"
    IPVLAN = "ipvlan"
    NONE = "none"

class IPAMConfig(BaseModel):
    """IP Address Management configuration for Docker networks."""
    subnet: Optional[Union[IPv4Network, IPv6Network]] = Field(
        None,
        description="The subnet in CIDR format (e.g., '172.28.0.0/16')"
    )
    ip_range: Optional[Union[IPv4Network, IPv6Network]] = Field(
        None,
        description="Range of IPs from which to allocate container IPs"
    )
    gateway: Optional[IPvAnyAddress] = Field(
        None,
        description="IPv4 or IPv6 gateway for the master subnet"
    )
    aux_addresses: Optional[Dict[str, IPvAnyAddress]] = Field(
        None,
        description="Auxiliary IPv4 or IPv6 addresses used by the network driver"
    )

    class Config:
        json_encoders = {
            IPv4Network: str,
            IPv6Network: str,
            ipaddress.IPv4Address: str,
            ipaddress.IPv6Address: str
        }

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
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to set on the network"
    )
    ipam: Optional[IPAMConfig] = Field(
        None,
        description="Optional custom IPAM configuration"
    )

class NetworkConnectRequest(BaseModel):
    """Request model for connecting a container to a network."""
    container: str = Field(..., description="Container ID or name")
    network: str = Field(..., description="Network ID or name")
    ipv4_address: Optional[IPvAnyAddress] = Field(
        None,
        description="IPv4 address (e.g., 172.30.100.104)"
    )
    ipv6_address: Optional[IPvAnyAddress] = Field(
        None,
        description="IPv6 address (e.g., 2001:db8:33b:100::17)"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="List of network-scoped aliases for the container"
    )
    links: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of aliases to IP addresses for linked containers"
    )
    link_local_ips: List[IPvAnyAddress] = Field(
        default_factory=list,
        description="List of link-local IP addresses"
    )
    driver_opt: Optional[Dict[str, str]] = Field(
        None,
        description="Driver options for the endpoint"
    )

class NetworkInspectResult(BaseModel):
    """Detailed information about a Docker network."""
    name: str = Field(..., description="Name of the network")
    id: str = Field(..., description="ID of the network")
    created: datetime = Field(..., description="When the network was created")
    scope: str = Field(..., description="Scope of the network (e.g., 'local', 'swarm')")
    driver: str = Field(..., description="Driver used by the network")
    enable_ipv6: bool = Field(..., description="Whether IPv6 is enabled")
    internal: bool = Field(..., description="Whether the network is internal")
    attachable: bool = Field(..., description="Whether the network is attachable")
    ingress: bool = Field(..., description="Whether this is the ingress network")
    ipam: Dict[str, Any] = Field(..., description="IPAM configuration")
    options: Dict[str, str] = Field(..., description="Driver-specific options")
    labels: Dict[str, str] = Field(..., description="Labels set on the network")
    containers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Containers connected to the network"
    )

@Tool(
    name="list_networks",
    description="List Docker networks",
    parameters={
        'type': 'object',
        'properties': {
            'names': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': [],
                'description': 'Filter by network names'
            },
            'ids': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': [],
                'description': 'Filter by network IDs'
            },
            'driver': {
                'type': 'string',
                'default': None,
                'description': 'Filter by driver name (e.g., "bridge", "overlay")'
            },
            'type': {
                'type': 'string',
                'enum': ['custom', 'builtin', 'all'],
                'default': 'all',
                'description': 'Type of networks to list'
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Filter by labels (e.g., {"com.example.key": "value"})'
            }
        }
    }
)
async def list_networks(
    names: List[str] = [],
    ids: List[str] = [],
    driver: Optional[str] = None,
    type: str = 'all',
    labels: Dict[str, str] = {}
) -> Dict[str, Any]:
    """
    List Docker networks with filtering options.
    
    This function lists all Docker networks, with optional filtering by name,
    ID, driver, or labels.
    
    Args:
        names: Filter by network names
        ids: Filter by network IDs
        driver: Filter by driver name (e.g., "bridge", "overlay")
        type: Type of networks to list ('custom', 'builtin', or 'all')
        labels: Filter by labels
        
    Returns:
        Dictionary with list of networks and metadata
        
    Example:
        >>> await list_networks(
        ...     driver="bridge",
        ...     labels={"environment": "production"}
        ... )
        {
            "status": "success",
            "networks": [
                {
                    "id": "7d86d31b1478...",
                    "name": "bridge",
                    "driver": "bridge",
                    "scope": "local",
                    "ipam": {"Driver": "default", "Config": [{"Subnet": "172.17.0.0/16"}]},
                    "containers": {},
                    "options": {
                        "com.docker.network.bridge.default_bridge": "true",
                        ...
                    },
                    "labels": {"environment": "production"}
                },
                ...
            ],
            "count": 1
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Build filters
        filters = {}
        
        if names:
            filters['name'] = names
        if ids:
            filters['id'] = ids
        if driver:
            filters['driver'] = [driver]
        if labels:
            filters['label'] = [f"{k}={v}" for k, v in labels.items()]
        
        # Get networks
        networks = client.networks.list(filters=filters)
        
        # Filter by type if needed
        if type != 'all':
            is_builtin = type == 'builtin'
            networks = [net for net in networks if net.attrs.get('Ingress') == is_builtin]
        
        # Prepare response
        network_list = []
        
        for network in networks:
            try:
                # Get detailed information
                network.reload()
                
                network_info = {
                    'id': network.id,
                    'name': network.name,
                    'driver': network.attrs.get('Driver', ''),
                    'scope': network.attrs.get('Scope', ''),
                    'ipam': network.attrs.get('IPAM', {}),
                    'containers': network.attrs.get('Containers', {}),
                    'options': network.attrs.get('Options', {}),
                    'labels': network.attrs.get('Labels', {})
                }
                
                network_list.append(network_info)
                
            except Exception as e:
                logger.warning(f"Error processing network {network.id}: {str(e)}")
                continue
        
        return {
            'status': 'success',
            'networks': network_list,
            'count': len(network_list)
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error listing networks: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="create_network",
    description="Create a new Docker network",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Name of the network'
            },
            'driver': {
                'type': 'string',
                'enum': [e.value for e in NetworkDriver],
                'default': 'bridge',
                'description': 'Driver to manage the Network'
            },
            'check_duplicate': {
                'type': 'boolean',
                'default': True,
                'description': 'Check for networks with duplicate names'
            },
            'internal': {
                'type': 'boolean',
                'default': False,
                'description': 'Restrict external access to the network'
            },
            'attachable': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable manual container attachment'
            },
            'ingress': {
                'type': 'boolean',
                'default': False,
                'description': 'Create an ingress network which provides the routing-mesh'
            },
            'enable_ipv6': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable IPv6 on the network'
            },
            'options': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Driver-specific options'
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Labels to set on the network'
            },
            'ipam': {
                'type': 'object',
                'properties': {
                    'subnet': {'type': 'string', 'format': 'ipv4-cidr', 'description': 'Subnet in CIDR format'},
                    'ip_range': {'type': 'string', 'format': 'ipv4-cidr', 'description': 'IP range for container IPs'},
                    'gateway': {'type': 'string', 'format': 'ipv4', 'description': 'IPv4 gateway'},
                    'aux_addresses': {
                        'type': 'object',
                        'additionalProperties': {'type': 'string', 'format': 'ipv4'},
                        'description': 'Auxiliary IPv4 addresses'
                    }
                },
                'description': 'IPAM configuration'
            }
        },
        'required': ['name']
    }
)
async def create_network(
    name: str,
    driver: str = 'bridge',
    check_duplicate: bool = True,
    internal: bool = False,
    attachable: bool = False,
    ingress: bool = False,
    enable_ipv6: bool = False,
    options: Dict[str, str] = {},
    labels: Dict[str, str] = {},
    ipam: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new Docker network.
    
    This function creates a new Docker network with the specified configuration.
    
    Args:
        name: Name of the network
        driver: Driver to manage the Network
        check_duplicate: Check for networks with duplicate names
        internal: Restrict external access to the network
        attachable: Enable manual container attachment
        ingress: Create an ingress network which provides the routing-mesh
        enable_ipv6: Enable IPv6 on the network
        options: Driver-specific options
        labels: Labels to set on the network
        ipam: IPAM configuration
        
    Returns:
        Dictionary with the created network information
        
    Example:
        >>> await create_network(
        ...     name="my-network",
        ...     driver="bridge",
        ...     ipam={
        ...         'subnet': '172.28.0.0/16',
        ...         'gateway': '172.28.5.1'
        ...     },
        ...     labels={"environment": "development"}
        ... )
        {
            "status": "success",
            "network": {
                "id": "7d86d31b1478...",
                "name": "my-network",
                "driver": "bridge",
                "scope": "local",
                "ipam": {
                    "Driver": "default",
                    "Config": [{"Subnet": "172.28.0.0/16", "Gateway": "172.28.5.1"}]
                },
                "containers": {},
                "options": {},
                "labels": {"environment": "development"}
            }
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Prepare IPAM configuration
        ipam_config = None
        if ipam:
            ipam_config = docker.types.IPAMConfig(
                pool_configs=[
                    docker.types.IPAMPool(
                        subnet=ipam.get('subnet'),
                        iprange=ipam.get('ip_range'),
                        gateway=ipam.get('gateway'),
                        aux_addresses=ipam.get('aux_addresses', {})
                    )
                ]
            )
        
        # Create the network
        network = client.networks.create(
            name=name,
            driver=driver,
            check_duplicate=check_duplicate,
            internal=internal,
            attachable=attachable,
            ingress=ingress,
            enable_ipv6=enable_ipv6,
            options=options,
            labels=labels,
            ipam=ipam_config
        )
        
        # Get the created network details
        network.reload()
        
        return {
            'status': 'success',
            'network': {
                'id': network.id,
                'name': network.name,
                'driver': network.attrs.get('Driver', ''),
                'scope': network.attrs.get('Scope', ''),
                'ipam': network.attrs.get('IPAM', {}),
                'containers': network.attrs.get('Containers', {}),
                'options': network.attrs.get('Options', {}),
                'labels': network.attrs.get('Labels', {})
            }
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'name': name
        }
        
    except Exception as e:
        error_msg = f"Unexpected error creating network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'name': name
        }

@Tool(
    name="remove_network",
    description="Remove a Docker network",
    parameters={
        'type': 'object',
        'properties': {
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name'
            }
        },
        'required': ['network_id']
    }
)
async def remove_network(network_id: str) -> Dict[str, Any]:
    """
    Remove a Docker network.
    
    This function removes a Docker network by its ID or name.
    
    Args:
        network_id: Network ID or name
        
    Returns:
        Dictionary with the removal result
        
    Example:
        >>> await remove_network("my-network")
        {
            "status": "success",
            "message": "Network removed successfully",
            "network_id": "7d86d31b1478..."
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the network
        try:
            network = client.networks.get(network_id)
        except NotFound:
            return {
                'status': 'error',
                'error': f'Network not found: {network_id}'
            }
        
        # Remove the network
        network.remove()
        
        return {
            'status': 'success',
            'message': 'Network removed successfully',
            'network_id': network_id
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'network_id': network_id
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'network_id': network_id
        }
        
    except Exception as e:
        error_msg = f"Unexpected error removing network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'network_id': network_id
        }

@Tool(
    name="connect_container_to_network",
    description="Connect a container to a network",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'Container ID or name'
            },
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name'
            },
            'ipv4_address': {
                'type': 'string',
                'format': 'ipv4',
                'default': None,
                'description': 'IPv4 address (e.g., 172.30.100.104)'
            },
            'ipv6_address': {
                'type': 'string',
                'format': 'ipv6',
                'default': None,
                'description': 'IPv6 address (e.g., 2001:db8:33b:100::17)'
            },
            'aliases': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': [],
                'description': 'List of network-scoped aliases for the container'
            },
            'links': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Mapping of aliases to IP addresses for linked containers'
            },
            'link_local_ips': {
                'type': 'array',
                'items': {'type': 'string', 'format': 'ip'},
                'default': [],
                'description': 'List of link-local IP addresses'
            },
            'driver_opt': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Driver options for the endpoint'
            }
        },
        'required': ['container_id', 'network_id']
    }
)
async def connect_container_to_network(
    container_id: str,
    network_id: str,
    ipv4_address: Optional[str] = None,
    ipv6_address: Optional[str] = None,
    aliases: List[str] = [],
    links: Dict[str, str] = {},
    link_local_ips: List[str] = [],
    driver_opt: Dict[str, str] = {}
) -> Dict[str, Any]:
    """
    Connect a container to a network.
    
    This function connects a container to a Docker network with the specified
    network configuration.
    
    Args:
        container_id: Container ID or name
        network_id: Network ID or name
        ipv4_address: IPv4 address (e.g., 172.30.100.104)
        ipv6_address: IPv6 address (e.g., 2001:db8:33b:100::17)
        aliases: List of network-scoped aliases for the container
        links: Mapping of aliases to IP addresses for linked containers
        link_local_ips: List of link-local IP addresses
        driver_opt: Driver options for the endpoint
        
    Returns:
        Dictionary with the connection result
        
    Example:
        >>> await connect_container_to_network(
        ...     container_id="my-container",
        ...     network_id="my-network",
        ...     ipv4_address="172.30.100.104",
        ...     aliases=["web", "app"]
        ... )
        {
            "status": "success",
            "message": "Container connected to network successfully",
            "container_id": "my-container",
            "network_id": "my-network"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the network
        try:
            network = client.networks.get(network_id)
        except NotFound:
            return {
                'status': 'error',
                'error': f'Network not found: {network_id}'
            }
        
        # Connect the container to the network
        network.connect(
            container=container_id,
            ipv4_address=ipv4_address,
            ipv6_address=ipv6_address,
            aliases=aliases,
            links=links,
            link_local_ips=link_local_ips,
            driver_opt=driver_opt
        )
        
        return {
            'status': 'success',
            'message': 'Container connected to network successfully',
            'container_id': container_id,
            'network_id': network_id
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'container_id': container_id,
            'network_id': network_id
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'container_id': container_id,
            'network_id': network_id
        }
        
    except Exception as e:
        error_msg = f"Unexpected error connecting container to network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'container_id': container_id,
            'network_id': network_id
        }

@Tool(
    name="disconnect_container_from_network",
    description="Disconnect a container from a network",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'Container ID or name'
            },
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name'
            },
            'force': {
                'type': 'boolean',
                'default': False,
                'description': 'Force the container to disconnect from the network'
            }
        },
        'required': ['container_id', 'network_id']
    }
)
async def disconnect_container_from_network(
    container_id: str,
    network_id: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Disconnect a container from a network.
    
    This function disconnects a container from a Docker network.
    
    Args:
        container_id: Container ID or name
        network_id: Network ID or name
        force: Force the container to disconnect from the network
        
    Returns:
        Dictionary with the disconnection result
        
    Example:
        >>> await disconnect_container_from_network(
        ...     container_id="my-container",
        ...     network_id="my-network"
        ... )
        {
            "status": "success",
            "message": "Container disconnected from network successfully",
            "container_id": "my-container",
            "network_id": "my-network"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the network
        try:
            network = client.networks.get(network_id)
        except NotFound:
            return {
                'status': 'error',
                'error': f'Network not found: {network_id}'
            }
        
        # Disconnect the container from the network
        network.disconnect(container_id, force=force)
        
        return {
            'status': 'success',
            'message': 'Container disconnected from network successfully',
            'container_id': container_id,
            'network_id': network_id
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'container_id': container_id,
            'network_id': network_id
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'container_id': container_id,
            'network_id': network_id
        }
        
    except Exception as e:
        error_msg = f"Unexpected error disconnecting container from network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'container_id': container_id,
            'network_id': network_id
        }

@Tool(
    name="inspect_network",
    description="Inspect a Docker network",
    parameters={
        'type': 'object',
        'properties': {
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name'
            },
            'verbose': {
                'type': 'boolean',
                'default': False,
                'description': 'Show detailed information about the network''s endpoints'
            },
            'scope': {
                'type': 'string',
                'default': 'local',
                'enum': ['local', 'swarm'],
                'description': 'Filter the network by scope'
            }
        },
        'required': ['network_id']
    }
)
async def inspect_network(
    network_id: str,
    verbose: bool = False,
    scope: str = 'local'
) -> Dict[str, Any]:
    """
    Inspect a Docker network.
    
    This function retrieves detailed information about a Docker network.
    
    Args:
        network_id: Network ID or name
        verbose: Show detailed information about the network's endpoints
        scope: Filter the network by scope ('local' or 'swarm')
        
    Returns:
        Dictionary with the network details
        
    Example:
        >>> await inspect_network("my-network", verbose=True)
        {
            "status": "success",
            "network": {
                "name": "my-network",
                "id": "7d86d31b1478...",
                "created": "2023-01-01T12:00:00Z",
                "scope": "local",
                "driver": "bridge",
                "enable_ipv6": false,
                "internal": false,
                "attachable": false,
                "ingress": false,
                "ipam": {
                    "driver": "default",
                    "config": [
                        {
                            "subnet": "172.28.0.0/16",
                            "gateway": "172.28.5.1"
                        }
                    ]
                },
                "options": {},
                "labels": {"environment": "development"},
                "containers": {
                    "container1": {
                        "name": "web",
                        "endpoint_id": "...",
                        "mac_address": "02:42:ac:1c:00:02",
                        "ipv4_address": "172.28.0.2/16",
                        "ipv6_address": ""
                    }
                }
            }
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the network
        try:
            network = client.networks.get(network_id)
        except NotFound:
            return {
                'status': 'error',
                'error': f'Network not found: {network_id}'
            }
        
        # Filter by scope if needed
        if scope and network.attrs.get('Scope') != scope:
            return {
                'status': 'error',
                'error': f'Network {network_id} is not in the {scope} scope'
            }
        
        # Get detailed information
        network.reload()
        
        # Prepare the response
        result = {
            'name': network.name,
            'id': network.id,
            'created': datetime.fromtimestamp(network.attrs['Created']).isoformat(),
            'scope': network.attrs.get('Scope', ''),
            'driver': network.attrs.get('Driver', ''),
            'enable_ipv6': network.attrs.get('EnableIPv6', False),
            'internal': network.attrs.get('Internal', False),
            'attachable': network.attrs.get('Attachable', False),
            'ingress': network.attrs.get('Ingress', False),
            'ipam': network.attrs.get('IPAM', {}),
            'options': network.attrs.get('Options', {}),
            'labels': network.attrs.get('Labels', {})
        }
        
        # Add containers if verbose is True
        if verbose:
            result['containers'] = network.attrs.get('Containers', {})
        
        return {
            'status': 'success',
            'network': result
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'network_id': network_id
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'network_id': network_id
        }
        
    except Exception as e:
        error_msg = f"Unexpected error inspecting network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'network_id': network_id
        }
