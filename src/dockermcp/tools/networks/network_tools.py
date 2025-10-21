"""
Network Management Tools for DockerMCP

This module provides high-level functions for managing Docker networks,
including creating, removing, and inspecting networks, as well as managing
container connections to networks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import docker
from docker.models.networks import Network
from fastmcp.exceptions import ToolError as ToolError

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

from .models import (
    NetworkCreateRequest,
    NetworkSummary,
    NetworkListResponse,
    NetworkInspectResponse,
    NetworkOperationResponse,
    NetworkIPAMConfig
)


def prune_networks() -> NetworkOperationResponse:
    """
    Remove all unused networks.
    
    Returns:
        NetworkOperationResponse containing the result of the operation.
    """
    try:
        client = mcp.docker_client
        result = client.networks.prune()
        
        deleted_count = len(result.get('NetworksDeleted', []))
        space_reclaimed = result.get('SpaceReclaimed', 0)
        
        logger.info(
            "Successfully pruned networks",
            networks_deleted=deleted_count,
            space_reclaimed=space_reclaimed
        )
        
        return NetworkOperationResponse(
            status="success",
            message=f"Successfully pruned {deleted_count} networks",
            network_id=None,
            data={
                'networks_deleted': result.get('NetworksDeleted', []),
                'space_reclaimed': space_reclaimed
            }
        )
        
    except docker.errors.APIError as e:
        error_msg = f"Failed to prune networks: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkOperationResponse.error(
            error=error_msg,
            message="Failed to prune networks"
        )


def list_networks() -> NetworkListResponse:
    """
    List all Docker networks.
    
    Returns:
        NetworkListResponse containing the list of networks and status information.
    """
    try:
        client = mcp.docker_client
        networks = client.networks.list()
        
        network_summaries = [
            NetworkSummary.from_docker_network(net)
            for net in networks
        ]
        
        logger.info(
            "Listed networks",
            network_count=len(network_summaries)
        )
        
        return NetworkListResponse.success(
            data=network_summaries,
            message=f"Found {len(network_summaries)} networks"
        )
        
    except docker.errors.APIError as e:
        error_msg = f"Failed to list networks: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkListResponse.error(
            error=error_msg,
            message="Failed to list networks"
        )


def create_network(
    params: NetworkCreateRequest
) -> NetworkOperationResponse:
    """
    Create a new Docker network.
    
    Args:
        params: NetworkCreateRequest containing network configuration
        
    Returns:
        NetworkOperationResponse containing the result of the operation
    """
    try:
        client = mcp.docker_client
        
        # Convert Pydantic model to dict for docker-py
        network_data = params.model_dump(exclude_none=True)
        
        # Create the network
        network = client.networks.create(**network_data)
        
        logger.info(
            f"Created network '{params.name}' with ID {network.id}",
            network_id=network.id,
            driver=params.driver,
            internal=params.internal
        )
        
        return NetworkOperationResponse.success(
            network_id=network.id,
            message=f"Successfully created network '{params.name}'",
            data={
                'name': params.name,
                'driver': params.driver,
                'internal': params.internal
            }
        )
        
    except docker.errors.APIError as e:
        error_msg = f"Failed to create network '{params.name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkOperationResponse.error(
            error=error_msg,
            message=f"Failed to create network '{params.name}'"
        )


def remove_network(network_id: str) -> NetworkOperationResponse:
    """
    Remove a Docker network.
    
    Args:
        network_id: ID or name of the network to remove
        
    Returns:
        NetworkOperationResponse with the result of the operation
    """
    try:
        client = mcp.docker_client
        network = client.networks.get(network_id)
        network_name = network.name
        network.remove()
        
        logger.info(
            "Removed network",
            network_id=network_id,
            network_name=network_name
        )
        
        return NetworkOperationResponse.success(
            network_id=network_id,
            message=f"Successfully removed network '{network_name}'",
            data={
                'name': network_name
            }
        )
        
    except docker.errors.NotFound as e:
        error_msg = f"Network '{network_id}' not found: {str(e)}"
        logger.warning(error_msg)
        return NetworkOperationResponse.error(
            error=error_msg,
            network_id=network_id,
            message=f"Network '{network_id}' not found"
        )
        
    except docker.errors.APIError as e:
        error_msg = f"Failed to remove network '{network_id}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkOperationResponse.error(
            error=error_msg,
            network_id=network_id,
            message=f"Failed to remove network"
        )


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


def inspect_network(network_id: str) -> NetworkInspectResponse:
    """
    Get detailed information about a specific network.
    
    Args:
        network_id: ID or name of the network
        
    Returns:
        NetworkInspectResponse containing detailed network information
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
        
        logger.debug(
            "Inspected network",
            network_id=network_id,
            network_name=network.name
        )
        
        return NetworkInspectResponse.success(
            data=result,
            message=f"Successfully inspected network '{network.name}'"
        )
        
    except docker.errors.NotFound as e:
        error_msg = f"Network '{network_id}' not found: {str(e)}"
        logger.warning(error_msg)
        return NetworkInspectResponse.error(
            error=error_msg,
            message=f"Network '{network_id}' not found"
        )
        
    except docker.errors.APIError as e:
        error_msg = f"Failed to inspect network '{network_id}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkInspectResponse.error(
            error=error_msg,
            message=f"Failed to inspect network"
        )
