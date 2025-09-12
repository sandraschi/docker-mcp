"""
Container networking for Docker MCP.

This module provides tools for managing container networks, including creating,
inspecting, and removing networks, as well as connecting/disconnecting containers.
It follows FastMCP 2.12+ standards for tool registration and error handling.
"""
from __future__ import annotations

import ipaddress
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import docker
from docker.errors import DockerException, APIError, NotFound
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, ConfigDict, validator

from dockermcp.logging_config import logger

class NetworkDriver(str, Enum):
    """Supported Docker network drivers."""
    BRIDGE = "bridge"
    HOST = "host"
    OVERLAY = "overlay"
    MACVLAN = "macvlan"
    NONE = "none"

class IPAMConfig(BaseModel):
    """IP Address Management configuration for Docker networks."""
    subnet: Optional[str] = Field(
        None,
        description="Subnet in CIDR format that represents a network segment"
    )
    ip_range: Optional[str] = Field(
        None,
        description="Range of IPs from which to allocate container IPs"
    )
    gateway: Optional[str] = Field(
        None,
        description="IPv4 or IPv6 gateway for the master subnet"
    )
    aux_addresses: Optional[Dict[str, str]] = Field(
        None,
        description="Auxiliary IPv4 or IPv6 addresses used by the network driver"
    )

    @validator('subnet', 'ip_range', 'gateway')
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
    ipam: Optional[IPAMConfig] = Field(
        None,
        description="Optional custom IPAM config"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of labels to set on the network"
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
                'enum': [e.value for e in NetworkDriver],
                'default': None,
                'description': 'Filter by network driver'
            },
            'scope': {
                'type': 'string',
                'enum': ['local', 'swarm', 'global'],
                'default': None,
                'description': 'Filter by network scope'
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Filter by labels (key=value)'
            },
            'detailed': {
                'type': 'boolean',
                'default': False,
                'description': 'Include detailed information about each network'
            }
        }
    }
)
async def list_networks(
    names: List[str] = [],
    ids: List[str] = [],
    driver: Optional[str] = None,
    scope: Optional[str] = None,
    labels: Dict[str, str] = {},
    detailed: bool = False
) -> Dict[str, Any]:
    """
    List Docker networks with filtering options.
    
    This function provides a way to list all Docker networks with various filtering
    options. It can return either a summary or detailed information about each network.
    
    Args:
        names: Filter by network names
        ids: Filter by network IDs
        driver: Filter by network driver
        scope: Filter by network scope (local, swarm, global)
        labels: Filter by labels (key=value)
        detailed: Include detailed information about each network
        
    Returns:
        Dictionary with list of networks and metadata
        
    Example:
        >>> await list_networks(
        ...     driver="bridge",
        ...     detailed=True
        ... )
        {
            "status": "success",
            "networks": [
                {
                    "id": "a1b2c3d4e5f6",
                    "name": "bridge",
                    "driver": "bridge",
                    "scope": "local",
                    "ipam": {
                        "driver": "default",
                        "config": [
                            {
                                "subnet": "172.17.0.0/16",
                                "gateway": "172.17.0.1"
                            }
                        ]
                    },
                    "containers": {
                        "container1": {
                            "name": "my-container",
                            "endpoint_id": "e1d5f9f...",
                            "mac_address": "02:42:ac:11:00:02",
                            "ipv4_address": "172.17.0.2/16",
                            "ipv6_address": ""
                        }
                    },
                    "options": {
                        "com.docker.network.bridge.default_bridge": "true",
                        "com.docker.network.bridge.enable_icc": "true",
                        "com.docker.network.bridge.enable_ip_masquerade": "true",
                        "com.docker.network.bridge.host_binding_ipv4": "0.0.0.0",
                        "com.docker.network.bridge.name": "docker0",
                        "com.docker.network.driver.mtu": "1500"
                    },
                    "labels": {},
                    "created": "2023-01-01T12:00:00Z",
                    "internal": False,
                    "enable_ipv6": False,
                    "attachable": False,
                    "ingress": False
                }
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
            filters['driver'] = driver
        if scope:
            filters['scope'] = scope
        if labels:
            filters['label'] = [f"{k}={v}" for k, v in labels.items()]
        
        # Get networks
        networks = client.networks.list(filters=filters)
        
        # Prepare response
        network_list = []
        
        for network in networks:
            network_info = {
                'id': network.id,
                'name': network.name,
                'driver': network.attrs.get('Driver', ''),
                'scope': network.attrs.get('Scope', ''),
                'created': datetime.fromtimestamp(
                    network.attrs['Created'].split('.')[0],
                    tz=datetime.timezone.utc
                ).isoformat(),
                'internal': network.attrs.get('Internal', False),
                'enable_ipv6': network.attrs.get('EnableIPv6', False),
                'attachable': network.attrs.get('Attachable', False),
                'ingress': network.attrs.get('Ingress', False),
                'labels': network.attrs.get('Labels', {})
            }
            
            if detailed:
                # Add detailed information
                network_info.update({
                    'ipam': network.attrs.get('IPAM', {}),
                    'containers': network.attrs.get('Containers', {}),
                    'options': network.attrs.get('Options', {})
                })
            
            network_list.append(network_info)
        
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
                'description': 'Driver to manage the network'
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
            'ipam': {
                'type': 'object',
                'properties': {
                    'subnet': {
                        'type': 'string',
                        'description': 'Subnet in CIDR format that represents a network segment'
                    },
                    'ip_range': {
                        'type': 'string',
                        'description': 'Range of IPs from which to allocate container IPs'
                    },
                    'gateway': {
                        'type': 'string',
                        'description': 'IPv4 or IPv6 gateway for the master subnet'
                    },
                    'aux_addresses': {
                        'type': 'object',
                        'additionalProperties': {'type': 'string'},
                        'description': 'Auxiliary IPv4 or IPv6 addresses used by the network driver'
                    }
                },
                'description': 'Optional custom IPAM config'
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Map of labels to set on the network'
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
    ipam: Optional[Dict[str, Any]] = None,
    labels: Dict[str, str] = {}
) -> Dict[str, Any]:
    """
    Create a new Docker network.
    
    This function creates a new Docker network with the specified configuration.
    It supports various network drivers and IPAM configurations.
    
    Args:
        name: Name of the network
        driver: Driver to manage the network
        check_duplicate: Check for networks with duplicate names
        internal: Restrict external access to the network
        attachable: Enable manual container attachment
        ingress: Create an ingress network for the routing-mesh
        enable_ipv6: Enable IPv6 on the network
        ipam: Optional custom IPAM config
        labels: Map of labels to set on the network
        
    Returns:
        Dictionary with the created network information
        
    Example:
        >>> await create_network(
        ...     name="my-network",
        ...     driver="bridge",
        ...     ipam={
        ...         "subnet": "172.28.0.0/16",
        ...         "ip_range": "172.28.5.0/24",
        ...         "gateway": "172.28.5.254"
        ...     },
        ...     labels={"environment": "development"}
        ... )
        {
            "status": "success",
            "id": "a1b2c3d4e5f6",
            "name": "my-network",
            "driver": "bridge",
            "scope": "local",
            "ipam": {
                "driver": "default",
                "config": [
                    {
                        "subnet": "172.28.0.0/16",
                        "ip_range": "172.28.5.0/24",
                        "gateway": "172.28.5.254"
                    }
                ]
            },
            "internal": false,
            "enable_ipv6": false,
            "attachable": false,
            "ingress": false,
            "labels": {
                "environment": "development"
            },
            "created": "2023-01-01T12:00:00Z"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Prepare IPAM config
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
            ipam=ipam_config,
            labels=labels
        )
        
        # Get the created network details
        network.reload()
        
        return {
            'status': 'success',
            'id': network.id,
            'name': network.name,
            'driver': network.attrs.get('Driver', ''),
            'scope': network.attrs.get('Scope', ''),
            'ipam': network.attrs.get('IPAM', {}),
            'internal': network.attrs.get('Internal', False),
            'enable_ipv6': network.attrs.get('EnableIPv6', False),
            'attachable': network.attrs.get('Attachable', False),
            'ingress': network.attrs.get('Ingress', False),
            'labels': network.attrs.get('Labels', {}),
            'created': datetime.fromtimestamp(
                network.attrs['Created'].split('.')[0],
                tz=datetime.timezone.utc
            ).isoformat()
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
        error_msg = f"Unexpected error creating network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="remove_network",
    description="Remove a Docker network",
    parameters={
        'type': 'object',
        'properties': {
            'network_id': {
                'type': 'string',
                'description': 'ID or name of the network to remove'
            },
            'force': {
                'type': 'boolean',
                'default': False,
                'description': 'Force removal of the network even if containers are attached'
            }
        },
        'required': ['network_id']
    }
)
async def remove_network(network_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker network.
    
    This function removes a Docker network. If the network has containers attached,
    the operation will fail unless force=True is specified.
    
    Args:
        network_id: ID or name of the network to remove
        force: Force removal even if containers are attached
        
    Returns:
        Dictionary with operation status
        
    Example:
        >>> await remove_network("my-network", force=True)
        {
            "status": "success",
            "message": "Network removed successfully",
            "network_id": "a1b2c3d4e5f6"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            # Get the network
            network = client.networks.get(network_id)
            network_id = network.id
            
            # Remove the network
            network.remove(force=force)
            
            return {
                'status': 'success',
                'message': 'Network removed successfully',
                'network_id': network_id
            }
            
        except NotFound:
            return {
                'status': 'error',
                'error': f'No such network: {network_id}'
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
        error_msg = f"Unexpected error removing network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="connect_container_to_network",
    description="Connect a container to a network",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'network_id': {
                'type': 'string',
                'description': 'ID or name of the network'
            },
            'ipv4_address': {
                'type': 'string',
                'default': None,
                'description': 'IPv4 address for the container on this network'
            },
            'ipv6_address': {
                'type': 'string',
                'default': None,
                'description': 'IPv6 address for the container on this network'
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
                'description': 'Mapping of container names to aliases for this network'
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
    links: Dict[str, str] = {}
) -> Dict[str, Any]:
    """
    Connect a container to a network.
    
    This function connects a container to a Docker network with the specified
    network configuration options.
    
    Args:
        container_id: ID or name of the container
        network_id: ID or name of the network
        ipv4_address: IPv4 address for the container on this network
        ipv6_address: IPv6 address for the container on this network
        aliases: List of network-scoped aliases for the container
        links: Mapping of container names to aliases for this network
        
    Returns:
        Dictionary with operation status and connection details
        
    Example:
        >>> await connect_container_to_network(
        ...     container_id="my-container",
        ...     network_id="my-network",
        ...     ipv4_address="172.28.1.5",
        ...     aliases=["web", "app"]
        ... )
        {
            "status": "success",
            "message": "Container connected to network",
            "container_id": "a1b2c3d4e5f6",
            "network_id": "b2c3d4e5f6g7",
            "ipv4_address": "172.28.1.5",
            "aliases": ["web", "app"]
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the container and network
        try:
            container = client.containers.get(container_id)
            network = client.networks.get(network_id)
        except NotFound as e:
            resource = 'container' if 'No such container' in str(e) else 'network'
            return {
                'status': 'error',
                'error': f"{resource.capitalize()} not found: {container_id if resource == 'container' else network_id}"
            }
        
        # Prepare endpoint configuration
        endpoint_config = client.api.create_endpoint_config(
            ipv4_address=ipv4_address,
            ipv6_address=ipv6_address,
            aliases=aliases,
            links=links
        )
        
        # Connect the container to the network
        network.connect(container, endpoint_config=endpoint_config)
        
        # Get the updated network info
        container.reload()
        network_info = container.attrs['NetworkSettings']['Networks'].get(network.name, {})
        
        return {
            'status': 'success',
            'message': 'Container connected to network',
            'container_id': container.id,
            'network_id': network.id,
            'ipv4_address': network_info.get('IPAddress'),
            'ipv6_address': network_info.get('GlobalIPv6Address'),
            'aliases': network_info.get('Aliases', []),
            'network_name': network.name
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
        error_msg = f"Unexpected error connecting container to network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="disconnect_container_from_network",
    description="Disconnect a container from a network",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'network_id': {
                'type': 'string',
                'description': 'ID or name of the network'
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
    
    This function disconnects a container from a Docker network. If force=True,
    the container will be disconnected even if it's currently running.
    
    Args:
        container_id: ID or name of the container
        network_id: ID or name of the network
        force: Force disconnection even if the container is running
        
    Returns:
        Dictionary with operation status
        
    Example:
        >>> await disconnect_container_from_network(
        ...     container_id="my-container",
        ...     network_id="my-network",
        ...     force=True
        ... )
        {
            "status": "success",
            "message": "Container disconnected from network",
            "container_id": "a1b2c3d4e5f6",
            "network_id": "b2c3d4e5f6g7"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the container and network
        try:
            container = client.containers.get(container_id)
            network = client.networks.get(network_id)
        except NotFound as e:
            resource = 'container' if 'No such container' in str(e) else 'network'
            return {
                'status': 'error',
                'error': f"{resource.capitalize()} not found: {container_id if resource == 'container' else network_id}"
            }
        
        # Disconnect the container from the network
        network.disconnect(container, force=force)
        
        return {
            'status': 'success',
            'message': 'Container disconnected from network',
            'container_id': container.id,
            'network_id': network.id
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
        error_msg = f"Unexpected error disconnecting container from network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}
