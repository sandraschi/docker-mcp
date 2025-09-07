"""
Network management tools for Docker MCP.

This module provides FastMCP 2.11.3 compatible tools for managing Docker networks.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError
from dockermcp.logging_config import logger, configure_logging
from dockermcp.utils import run_docker_command
from dockermcp.tools.networks.network_models import (
    NetworkInfo, NetworkResponse, NetworkListResponse,
    CreateNetworkRequest, NetworkOperationRequest,
    ConnectContainerRequest, DisconnectContainerRequest,
    PruneNetworksRequest, PruneNetworksResponse,
    NetworkInspectRequest, NetworkStatsRequest,
    NetworkConnectivityTestRequest, NetworkDriver,
    NetworkStatus, NetworkScope, IPAMConfig, IPAMPoolConfig,
    EndpointSettings, EndpointIPAMConfig
)

configure_logging()

def handle_error(error: Exception, context: str = "") -> Dict[str, Any]:
    """Handle errors consistently across all tools."""
    error_msg = f"Error in {context}: {str(error)}" if context else f"Error: {str(error)}"
    return {
        "success": False,
        "error": error_msg,
        "error_type": error.__class__.__name__
    }

# Default network configuration for new networks
DEFAULT_NETWORK_CONFIG = {
    "driver": "bridge",
    "enable_ipv6": False,
    "internal": False,
    "attachable": False,
    "ingress": False,
    "ipam": {
        "driver": "default",
        "config": [{"subnet": "172.28.0.0/16"}]
    }
}

@Tool.register(
    name="list_networks",
    description="List all Docker networks with optional filtering"
)
async def list_networks(
    filters: Optional[Dict[str, str]] = None,
    scope: Optional[str] = None,
    driver: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    List all Docker networks with optional filtering.
    
    Args:
        filters: Dictionary of filter key/value pairs
        scope: Filter by network scope (local, swarm, etc.)
        driver: Filter by network driver
        verbose: Include detailed network information
        
    Returns:
        Dictionary containing list of networks and their details
    """
    try:
        if filters is None:
            filters = {}
            
        if scope:
            filters['scope'] = scope
        if driver:
            filters['driver'] = driver
            
        # Build the docker command
        cmd = ["network", "ls", "--format", "json"]
        
        # Add filters
        for key, value in filters.items():
            cmd.extend(['--filter', f'{key}={value}'])
            
        # Execute the command
        result = await run_docker_command('', cmd, format_json=True)
        
        if not result or not isinstance(result, list):
            return {
                'success': False,
                'error': 'Failed to list networks',
                'networks': [],
                'count': 0
            }
            
        # Format the output
        networks = []
        for net in result:
            networks.append({
                'id': net.get('ID', ''),
                'name': net.get('Name', ''),
                'driver': net.get('Driver', ''),
                'scope': net.get('Scope', ''),
                'created': net.get('CreatedAt', '')
            })
            
        return {
            'success': True,
            'networks': networks,
            'count': len(networks),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return handle_error(e, "listing networks")

@Tool.register(
    name="create_network",
    description="Create a new Docker network with advanced configuration"
)
async def create_network(
    request: CreateNetworkRequest
) -> Dict[str, Any]:
    """
    Create a new Docker network with advanced configuration options.
    
    Supports:
    - Custom IPAM configuration
    - IPv6 networking
    - Network encryption (for overlay networks)
    - Custom MTU settings
    - Network labels and options
    
    Args:
        request: CreateNetworkRequest with network configuration
        
    Returns:
        Dictionary containing the created network details
    """
    try:
        # Build the docker command
        cmd = ["network", "create"]
        
        # Add network options
        if request.driver:
            cmd.extend(["--driver", request.driver])
            
        if request.internal:
            cmd.append("--internal")
            
        if request.attachable:
            cmd.append("--attachable")
            
        if request.ingress:
            cmd.append("--ingress")
            
        if request.enable_ipv6:
            cmd.append("--ipv6")
            
        if hasattr(request, 'labels') and request.labels:
            for key, value in request.labels.items():
                cmd.extend(["--label", f"{key}={value}"])
                
        if hasattr(request, 'options') and request.options:
            for key, value in request.options.items():
                cmd.extend(["--opt", f"{key}={value}"])
                
        # Add IPAM configuration if provided
        if hasattr(request, 'ipam') and request.ipam:
            if hasattr(request.ipam, 'driver') and request.ipam.driver:
                cmd.extend(["--ipam-driver", request.ipam.driver])
                
            if hasattr(request.ipam, 'config') and request.ipam.config:
                for ipam_config in request.ipam.config:
                    if hasattr(ipam_config, 'subnet') and ipam_config.subnet:
                        cmd.extend(["--subnet", ipam_config.subnet])
                    if hasattr(ipam_config, 'ip_range') and ipam_config.ip_range:
                        cmd.extend(["--ip-range", ipam_config.ip_range])
                    if hasattr(ipam_config, 'gateway') and ipam_config.gateway:
                        cmd.extend(["--gateway", ipam_config.gateway])
        
        # Add network name
        cmd.append(request.name)
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': result.stderr or f'Failed to create network {request.name}',
                'network_name': request.name
            }
            
        # Get the created network details
        inspect_cmd = ["network", "inspect", request.name]
        inspect_result = await run_docker_command('', inspect_cmd, format_json=True)
        
        if not inspect_result or not isinstance(inspect_result, list):
            return {
                'success': False,
                'error': f'Failed to inspect created network {request.name}',
                'network_name': request.name
            }
            
        return {
            'success': True,
            'message': f'Network {request.name} created successfully',
            'network': inspect_result[0],
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return handle_error(e, f'creating network {getattr(request, "name", "")}')

@Tool.register(
    name="inspect_network",
    description="Inspect a Docker network"
)
async def inspect_network(
    request: NetworkInspectRequest
) -> Dict[str, Any]:
    """
    Get detailed information about a specific Docker network.
    
    Args:
        request: NetworkInspectRequest with network ID or name
        
    Returns:
        Dictionary containing network details
    """
    try:
        if not request.network_id:
            return {
                'success': False,
                'error': 'Network ID or name is required',
                'network_id': ''
            }
            
        # Build the docker command
        cmd = ["network", "inspect", request.network_id]
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=True)
        
        if not result or not isinstance(result, list):
            return {
                'success': False,
                'error': f'Network {request.network_id} not found',
                'network_id': request.network_id
            }
            
        return {
            'success': True,
            'network': result[0],
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return handle_error(e, f'inspecting network {getattr(request, "network_id", "")}')

@Tool.register(
    name="remove_network",
    description="Remove a Docker network"
)
async def remove_network(
    request: NetworkOperationRequest
) -> Dict[str, Any]:
    """
    Remove a Docker network.
    
    Args:
        request: NetworkOperationRequest with network ID or name
        
    Returns:
        Dictionary containing operation status
    """
    try:
        if not request.network_id:
            return {
                'success': False,
                'error': 'Network ID or name is required',
                'network_id': ''
            }
            
        # Build the docker command
        cmd = ["network", "rm", request.network_id]
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': result.stderr or f'Failed to remove network {request.network_id}',
                'network_id': request.network_id
            }
            
        return {
            'success': True,
            'message': f'Network {request.network_id} removed successfully',
            'network_id': request.network_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return handle_error(e, f'removing network {getattr(request, "network_id", "")}')

@Tool.register(
    name="connect_container",
    description="Connect a container to a network"
)
async def connect_container(
    request: ConnectContainerRequest
) -> Dict[str, Any]:
    """
    Connect a container to a network.
    
    Args:
        request: ConnectContainerRequest with container and network details
        
    Returns:
        Dictionary containing operation status
    """
    try:
        if not request.container_id or not request.network_id:
            return {
                'success': False,
                'error': 'Both container_id and network_id are required',
                'container_id': request.container_id,
                'network_id': request.network_id
            }
            
        # Build the docker command
        cmd = ["network", "connect"]
        
        # Add IP address if provided
        if request.ip_address:
            cmd.extend(["--ip", request.ip_address])
            
        # Add alias if provided
        if request.alias:
            cmd.extend(["--alias", request.alias])
            
        # Add network name and container ID
        cmd.extend([request.network_id, request.container_id])
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': result.stderr or f'Failed to connect container {request.container_id} to network {request.network_id}',
                'container_id': request.container_id,
                'network_id': request.network_id
            }
            
        return {
            'success': True,
            'message': f'Container {request.container_id} connected to network {request.network_id} successfully',
            'container_id': request.container_id,
            'network_id': request.network_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return handle_error(e, f'connecting container {getattr(request, "container_id", "")} to network {getattr(request, "network_id", "")}')

@Tool.register(
    name="disconnect_container",
    description="Disconnect a container from a network"
)
async def disconnect_container(
    request: DisconnectContainerRequest
) -> Dict[str, Any]:
    """
    Disconnect a container from a network.
    
    Args:
        request: DisconnectContainerRequest with container and network details
        
    Returns:
        Dictionary containing operation status
    """
    try:
        if not request.container_id or not request.network_id:
            return {
                'success': False,
                'error': 'Both container_id and network_id are required',
                'container_id': request.container_id,
                'network_id': request.network_id
            }
            
        # Build the docker command
        cmd = ["network", "disconnect", request.network_id, request.container_id]
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': result.stderr or f'Failed to disconnect container {request.container_id} from network {request.network_id}',
                'container_id': request.container_id,
                'network_id': request.network_id
            }
            
        return {
            'success': True,
            'message': f'Container {request.container_id} disconnected from network {request.network_id} successfully',
            'container_id': request.container_id,
            'network_id': request.network_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return handle_error(e, f'disconnecting container {getattr(request, "container_id", "")} from network {getattr(request, "network_id", "")}')

@Tool.register(
    name="prune_networks",
    description="Remove all unused networks"
)
async def prune_networks(
    request: PruneNetworksRequest
) -> Dict[str, Any]:
    """
    Remove all unused networks.
    
    Args:
        request: PruneNetworksRequest with optional filters
        
    Returns:
        Dictionary containing prune results
    """
    try:
        # Build the docker command
        cmd = ["network", "prune", "--force"]
        
        # Add filters if provided
        if hasattr(request, 'filters') and request.filters:
            for key, value in request.filters.items():
                cmd.extend(['--filter', f'{key}={value}'])
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=True)
        
        if not result or not isinstance(result, dict):
            return {
                'success': False,
                'error': 'Failed to prune networks',
                'networks_pruned': [],
                'space_reclaimed': 0
            }
            
        return {
            'success': True,
            'networks_pruned': result.get('NetworksDeleted', []),
            'space_reclaimed': result.get('SpaceReclaimed', 0),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return handle_error(e, 'pruning networks')
