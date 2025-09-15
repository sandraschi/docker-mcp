"""
Network Management Tools for DockerMCP

This module provides high-level functions for managing Docker networks,
including creating, removing, and inspecting networks, as well as managing
container connections to networks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, cast

import docker
from docker.models.networks import Network
from fastmcp.exceptions import ToolError as ToolError

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp


def prune_networks() -> Dict[str, Any]:
    """
    Remove all unused networks.
    
    Returns:
        Dict containing the number of networks deleted and the list of network IDs that were removed.
    """
    try:
        client = mcp.docker_client
        result = client.networks.prune()
        
        logger.info(
            "Successfully pruned networks",
            networks_deleted=len(result.get('NetworksDeleted', [])),
            space_reclaimed=result.get('SpaceReclaimed', 0)
        )
        
        return {
            'status': 'success',
            'message': f"Successfully pruned {len(result.get('NetworksDeleted', []))} networks",
            'networks_deleted': result.get('NetworksDeleted', []),
            'space_reclaimed': result.get('SpaceReclaimed', 0)
        }
    except docker.errors.APIError as e:
        error_msg = f"Failed to prune networks: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def list_networks() -> List[Dict[str, Any]]:
    """
    List all Docker networks.
    
    Returns:
        List of dictionaries containing network information.
    """
    try:
        client = mcp.docker_client
        networks = client.networks.list()
        
        result = []
        for net in networks:
            net_info = {
                'id': net.id,
                'name': net.name,
                'driver': net.attrs.get('Driver', ''),
                'scope': net.attrs.get('Scope', ''),
                'labels': net.attrs.get('Labels', {}),
                'created': net.attrs.get('Created', ''),
                'internal': net.attrs.get('Internal', False),
                'ipam': net.attrs.get('IPAM', {})
            }
            result.append(net_info)
            
        logger.info(f"Listed {len(networks)} networks")
        return result
        
    except docker.errors.APIError as e:
        error_msg = f"Failed to list networks: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def create_network(
    name: str,
    driver: str = 'bridge',
    check_duplicate: bool = True,
    internal: bool = False,
    labels: Optional[Dict[str, str]] = None,
    enable_ipv6: bool = False,
    attachable: bool = False,
    scope: Optional[str] = None,
    ipam: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new Docker network.
    
    Args:
        name: Name of the network
        driver: Network driver (default: bridge)
        check_duplicate: Check for networks with duplicate names (default: True)
        internal: Restrict external access to the network (default: False)
        labels: Dictionary of labels to apply to the network
        enable_ipv6: Enable IPv6 on the network (default: False)
        attachable: Enable manual container attachment (default: False)
        scope: Network scope (swarm, global, local)
        ipam: IPAM configuration
        
    Returns:
        Dictionary containing the created network information
    """
    try:
        client = mcp.docker_client
        
        # Set default IPAM if not provided
        if ipam is None:
            ipam = {
                'Driver': 'default',
                'Config': [{'Subnet': '172.28.0.0/16'}]
            }
            
        network = client.networks.create(
            name=name,
            driver=driver,
            check_duplicate=check_duplicate,
            internal=internal,
            labels=labels or {},
            enable_ipv6=enable_ipv6,
            attachable=attachable,
            scope=scope,
            ipam=ipam
        )
        
        logger.info(
            f"Created network '{name}' with ID {network.id}",
            network_id=network.id,
            driver=driver,
            internal=internal
        )
        
        return {
            'status': 'success',
            'message': f"Successfully created network '{name}'",
            'network_id': network.id,
            'name': name,
            'driver': driver
        }
        
    except docker.errors.APIError as e:
        error_msg = f"Failed to create network '{name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def remove_network(network_id: str) -> Dict[str, Any]:
    """
    Remove a Docker network.
    
    Args:
        network_id: ID or name of the network to remove
        
    Returns:
        Dictionary with status and message
    """
    try:
        client = mcp.docker_client
        network = client.networks.get(network_id)
        network_name = network.name
        network.remove()
        
        logger.info(f"Removed network '{network_name}' with ID {network_id}")
        
        return {
            'status': 'success',
            'message': f"Successfully removed network '{network_name}'"
        }
        
    except docker.errors.NotFound:
        error_msg = f"Network '{network_id}' not found"
        logger.warning(error_msg)
        raise ToolError(error_msg) from None
    except docker.errors.APIError as e:
        error_msg = f"Failed to remove network '{network_id}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def connect_container_to_network(
    container_id: str,
    network_id: str,
    ipv4_address: Optional[str] = None,
    ipv6_address: Optional[str] = None,
    aliases: Optional[List[str]] = None,
    links: Optional[Dict[str, str]] = None,
    link_local_ips: Optional[List[str]] = None,
    driver_opt: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Connect a container to a network.
    
    Args:
        container_id: ID or name of the container
        network_id: ID or name of the network
        ipv4_address: IPv4 address for the container on this network
        ipv6_address: IPv6 address for the container on this network
        aliases: List of aliases for the container on this network
        links: Mapping of container names to aliases for the network
        link_local_ips: List of link-local IP addresses
        driver_opt: Driver options for the endpoint
        
    Returns:
        Dictionary with status and message
    """
    try:
        client = mcp.docker_client
        network = client.networks.get(network_id)
        container = client.containers.get(container_id)
        
        endpoint_config = client.api.create_endpoint_config(
            ipv4_address=ipv4_address,
            ipv6_address=ipv6_address,
            aliases=aliases,
            links=links,
            link_local_ips=link_local_ips,
            driver_opt=driver_opt
        )
        
        network.connect(container, endpoint_config=endpoint_config)
        
        logger.info(
            f"Connected container '{container.name}' to network '{network.name}'",
            container_id=container_id,
            network_id=network_id
        )
        
        return {
            'status': 'success',
            'message': f"Successfully connected container to network '{network.name}'"
        }
        
    except (docker.errors.NotFound, docker.errors.APIError) as e:
        error_msg = f"Failed to connect container to network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def disconnect_container_from_network(
    container_id: str,
    network_id: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Disconnect a container from a network.
    
    Args:
        container_id: ID or name of the container
        network_id: ID or name of the network
        force: Force disconnect even if the container is running (default: False)
        
    Returns:
        Dictionary with status and message
    """
    try:
        client = mcp.docker_client
        network = client.networks.get(network_id)
        container = client.containers.get(container_id)
        
        network.disconnect(container, force=force)
        
        logger.info(
            f"Disconnected container '{container.name}' from network '{network.name}'",
            container_id=container_id,
            network_id=network_id
        )
        
        return {
            'status': 'success',
            'message': f"Successfully disconnected container from network '{network.name}'"
        }
        
    except (docker.errors.NotFound, docker.errors.APIError) as e:
        error_msg = f"Failed to disconnect container from network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def get_network_stats(network_id: str) -> Dict[str, Any]:
    """
    Get statistics for a specific network.
    
    Args:
        network_id: ID or name of the network
        
    Returns:
        Dictionary containing network statistics
    """
    try:
        client = mcp.docker_client
        network = client.networks.get(network_id)
        
        # Get all containers connected to this network
        containers = network.containers
        
        stats = {
            'network_id': network.id,
            'name': network.name,
            'containers_connected': len(containers),
            'containers': []
        }
        
        # Add basic container info
        for container in containers:
            stats['containers'].append({
                'id': container.id,
                'name': container.name,
                'status': container.status
            })
        
        logger.debug(f"Retrieved stats for network '{network.name}'", **stats)
        return stats
        
    except (docker.errors.NotFound, docker.errors.APIError) as e:
        error_msg = f"Failed to get stats for network '{network_id}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e


def inspect_network(network_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific network.
    
    Args:
        network_id: ID or name of the network
        
    Returns:
        Dictionary containing detailed network information
    """
    try:
        client = mcp.docker_client
        network = client.networks.get(network_id)
        
        # Get the raw network attributes
        attrs = network.attrs
        
        # Format the response
        result = {
            'id': attrs.get('Id'),
            'name': attrs.get('Name'),
            'created': attrs.get('Created'),
            'scope': attrs.get('Scope'),
            'driver': attrs.get('Driver'),
            'enable_ipv6': attrs.get('EnableIPv6', False),
            'internal': attrs.get('Internal', False),
            'attachable': attrs.get('Attachable', False),
            'ingress': attrs.get('Ingress', False),
            'ipam': attrs.get('IPAM', {}),
            'options': attrs.get('Options', {}),
            'labels': attrs.get('Labels', {}),
            'containers': {},
            'peers': attrs.get('Peers', []),
            'services': attrs.get('Services', {})
        }
        
        # Add container information if available
        if 'Containers' in attrs:
            for container_id, container_info in attrs['Containers'].items():
                result['containers'][container_id] = {
                    'name': container_info.get('Name', ''),
                    'endpoint_id': container_info.get('EndpointID', ''),
                    'mac_address': container_info.get('MacAddress', ''),
                    'ipv4_address': container_info.get('IPv4Address', ''),
                    'ipv6_address': container_info.get('IPv6Address', '')
                }
        
        logger.debug(f"Inspected network '{network.name}'", network_id=network_id)
        return result
        
    except (docker.errors.NotFound, docker.errors.APIError) as e:
        error_msg = f"Failed to inspect network '{network_id}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
