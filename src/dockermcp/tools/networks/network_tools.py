"""
Network management tools for Docker MCP.

This module provides FastMCP 2.10.1 compatible tools for managing Docker networks.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from fastmcp.tools import Tool
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

@Tool(
    name="list_networks",
    description="List all Docker networks with optional filtering"
)
async def list_networks(
    filters: Optional[Dict[str, str]] = None,
    scope: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    List all Docker networks with optional filtering and detailed information.
    
    Args:
        filters: Key/value pairs to filter networks
        scope: Filter by network scope (local, swarm)
        verbose: Include detailed information about each network
        
    Returns:
        Dictionary containing network list and metadata
    """
    try:
        # Build the command
        cmd = ['network', 'ls', '--format', 'json']
        
        # Add filters if provided
        if filters:
            for key, value in filters.items():
                cmd.extend(['--filter', f"{key}={value}"])
        
        # Execute the command
        result = run_docker_command('', cmd, format_json=True)
        
        if not result:
            return {
                "success": False,
                "error": "Failed to list networks",
                "networks": []
            }
            
        # Convert to list if single result
        if not isinstance(result, list):
            result = [result]
            
        # Format network information
        networks = []
        for net in result:
            networks.append({
                "id": net.get('ID', ''),
                "name": net.get('Name', ''),
                "driver": net.get('Driver', ''),
                "scope": net.get('Scope', ''),
                "created": net.get('CreatedAt', '')
            })
            
        if not verbose:
            return {
                "success": True,
                "networks": networks,
                "total": len(networks)
            }
            
        # Get detailed information for each network if verbose
        detailed_networks = []
        for net in networks:
            try:
                details = await inspect_network(NetworkOperationRequest(
                    network_id=net['id']
                ))
                if details.get('success', False):
                    detailed_networks.append(details.get('network', net))
                else:
                    detailed_networks.append(net)
            except Exception as e:
                detailed_networks.append(net)
                
        return {
            "success": True,
            "networks": detailed_networks,
            "total": len(detailed_networks)
        }
        
    except Exception as e:
        return handle_error(e, "list_networks")

@Tool(
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
    """
    try:
        # Validate network configuration
        if not request.name:
            raise ValueError("Network name is required")
            
        if request.driver == NetworkDriver.OVERLAY and request.scope == NetworkScope.LOCAL:
            raise ValueError("Overlay networks require swarm scope")
            
        # Initialize network manager
        import docker
        network_mgr = NetworkManager(docker_client=docker.from_env())
        
        # Create network using the manager
        network = await network_mgr.create_network(
            name=request.name,
            driver=request.driver,
            check_duplicate=request.check_duplicate,
            internal=request.internal,
            attachable=request.attachable,
            ingress=request.ingress,
            ipam=request.ipam.dict() if request.ipam else None,
            enable_ipv6=request.enable_ipv6,
            options=request.options,
            labels=request.labels,
            scope=request.scope.value,
            mtu=request.mtu,
            encrypted=request.encrypted
        )
        
        # Verify network was created
        if not network or "Id" not in network:
            raise RuntimeError("Failed to create network: No ID returned")
            
        return NetworkResponse(
            success=True,
            message=f"Network '{request.name}' created successfully",
            network=network
        ).dict()
        
    except Exception as e:
        error_msg = f"Failed to create network '{getattr(request, 'name', '')}': {str(e)}"
        return NetworkResponse(
            success=False,
            message=error_msg,
            error=str(e)
        ).dict()

@Tool(
    name="inspect_network",
    description="Inspect a Docker network with detailed information"
)
async def inspect_network(
    request: NetworkOperationRequest
) -> Dict[str, Any]:
    """
    Get detailed information about a specific Docker network.
    
    Args:
        network_id: ID or name of the network to inspect
        
    Returns:
        Dictionary containing network details and configuration
    """
    try:
        if not request.network_id:
            raise ValueError("Network ID is required")
            
        # Execute the inspect command
        result = run_docker_command(
            'network',
            ['inspect', request.network_id],
            format_json=True
        )
        
        if not result:
            return {
                "success": False,
                "error": f"Network '{request.network_id}' not found",
                "network_id": request.network_id
            }
            
        # Get the first network if result is a list
        network = result[0] if isinstance(result, list) else result
        
        # Get connected containers
        containers = []
        if 'Containers' in network and network['Containers']:
            for container_id, container_info in network['Containers'].items():
                containers.append({
                    'id': container_id,
                    'name': container_info.get('Name', ''),
                    'endpoint_id': container_info.get('EndpointID', ''),
                    'mac_address': container_info.get('MacAddress', ''),
                    'ipv4_address': container_info.get('IPv4Address', ''),
                    'ipv6_address': container_info.get('IPv6Address', '')
                })
        
        # Format the response
        response = {
            "success": True,
            "network": {
                "id": network.get('Id', ''),
                "name": network.get('Name', ''),
                "created": network.get('Created', ''),
                "scope": network.get('Scope', ''),
                "driver": network.get('Driver', ''),
                "enable_ipv6": network.get('EnableIPv6', False),
                "internal": network.get('Internal', False),
                "attachable": network.get('Attachable', False),
                "ingress": network.get('Ingress', False),
                "ipam": network.get('IPAM', {}),
                "options": network.get('Options', {}),
                "labels": network.get('Labels', {}),
                "containers": containers
            },
            "network_id": request.network_id
        }
        
        return response
        
    except Exception as e:
        return handle_error(e, f"inspect_network({request.network_id})")

@Tool(
    name="prune_networks",
    description="Remove unused Docker networks"
)
async def prune_networks(
    request: PruneNetworksRequest = None
) -> Dict[str, Any]:
    """
    Remove all unused Docker networks.
    
    Args:
        filters: Key/value pairs to filter networks for pruning
        until: Only remove networks created before this timestamp
        
    Returns:
        Dictionary containing list of pruned networks and space reclaimed
    """
    try:
        # Initialize request if None
        if request is None:
            request = PruneNetworksRequest()
            
        # Build the command
        cmd = ['prune', '--force']
        
        # Add filters if provided
        if request.filters:
            for key, value in request.filters.items():
                if key == 'until' and not request.until:
                    request.until = value
                else:
                    cmd.extend(['--filter', f"{key}={value}"])
                    
        # Add until filter if specified
        if request.until:
            cmd.extend(['--filter', f"until={request.until}"])
            
        # Execute the prune command
        result = run_docker_command('network', cmd, format_json=True)
        
        if not result:
            return {
                "success": False,
                "error": "Failed to prune networks",
                "networks_deleted": [],
                "space_reclaimed": 0
            }
            
        return {
            "success": True,
            "networks_deleted": result.get("NetworksDeleted", []),
            "space_reclaimed": result.get("SpaceReclaimed", 0),
            "message": f"Successfully pruned {len(result.get('NetworksDeleted', []))} networks"
        }
        
    except Exception as e:
        return handle_error(e, "prune_networks")

@Tool(
    name="remove_network",
    description="Remove a Docker network"
)
async def remove_network(
    request: NetworkOperationRequest
) -> Dict[str, Any]:
    """
    Remove a Docker network by ID or name.
    
    Args:
        network_id: ID or name of the network to remove
        force: Force removal even if in use (use with caution)
        
    Returns:
        Dictionary containing operation status
    """
    try:
        if not request.network_id:
            raise ValueError("Network ID is required")
            
        # Build the command
        cmd = ['rm']
        
        # Add force flag if specified
        if getattr(request, 'force', False):
            cmd.append('--force')
            
        # Add network ID
        cmd.append(request.network_id)
        
        # Execute the remove command
        result = run_docker_command('network', cmd, format_json=False)
        
        if result.returncode != 0:
            # Check if network is in use
            if "is in use" in (result.stderr or ""):
                return {
                    "success": False,
                    "error": f"Network '{request.network_id}' is in use. Use force=True to remove anyway.",
                    "network_id": request.network_id
                }
            return {
                "success": False,
                "error": result.stderr or f"Failed to remove network '{request.network_id}'",
                "network_id": request.network_id
            }
            
        return {
            "success": True,
            "message": f"Network '{request.network_id}' removed successfully",
            "network_id": request.network_id
        }
        
    except Exception as e:
        return handle_error(e, f"remove_network({request.network_id})")

@Tool(
    name="connect_container",
    description="Connect a container to a network with advanced options"
)
async def connect_container(
    request: ConnectContainerRequest
) -> Dict[str, Any]:
    """
    Connect a container to a network with advanced configuration options.
    
    Supports:
    - Custom IP address assignment
    - Network aliases
    - Link-local IPs
    - Endpoint configuration
    """
    try:
        if not request.network_id or not request.container_id:
            raise ValueError("Network ID and Container ID are required")
            
        # Build the connect command
        cmd = ['connect']
        
        # Add IP address if specified
        if request.ipv4_address or request.ipv6_address:
            if request.ipv4_address:
                cmd.extend(['--ip', request.ipv4_address])
            if request.ipv6_address:
                cmd.extend(['--ip6', request.ipv6_address])
                
        # Add aliases if specified
        if request.aliases:
            for alias in request.aliases:
                cmd.extend(['--alias', alias])
                
        # Add network and container
        cmd.extend([request.network_id, request.container_id])
        
        # Execute the connect command
        result = run_docker_command('network', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"Failed to connect container to network '{request.network_id}'",
                "network_id": request.network_id,
                "container_id": request.container_id
            }
            
        return {
            "success": True,
            "message": f"Container '{request.container_id}' connected to network '{request.network_id}'",
            "network_id": request.network_id,
            "container_id": request.container_id
        }
        
    except Exception as e:
        return handle_error(e, f"connect_container({request.container_id} to {request.network_id})")

@Tool(
    name="disconnect_container",
    description="Disconnect a container from a network"
)
async def disconnect_container(
    request: DisconnectContainerRequest
) -> Dict[str, Any]:
    """
    Disconnect a container from a network.
    
    Args:
        network_id: ID or name of the network
        container_id: ID or name of the container
        force: Force disconnect even if container is running
        
    Returns:
        Dictionary containing operation status
    """
    try:
        if not request.network_id or not request.container_id:
            raise ValueError("Network ID and Container ID are required")
            
        # Build the disconnect command
        cmd = ['disconnect']
        
        # Add force flag if specified
        if getattr(request, 'force', False):
            cmd.append('--force')
            
        # Add network and container
        cmd.extend([request.network_id, request.container_id])
        
        # Execute the disconnect command
        result = run_docker_command('network', cmd, format_json=False)
        
        if result.returncode != 0:
            # Check if container is not connected to the network
            if "is not connected to network" in (result.stderr or ""):
                return {
                    "success": False,
                    "error": f"Container '{request.container_id}' is not connected to network '{request.network_id}'",
                    "network_id": request.network_id,
                    "container_id": request.container_id
                }
                
            return {
                "success": False,
                "error": result.stderr or f"Failed to disconnect container from network '{request.network_id}'",
                "network_id": request.network_id,
                "container_id": request.container_id
            }
            
        return {
            "success": True,
            "message": f"Container '{request.container_id}' disconnected from network '{request.network_id}'",
            "network_id": request.network_id,
            "container_id": request.container_id
        }
        
    except Exception as e:
        return handle_error(e, f"disconnect_container({request.container_id} from {request.network_id})")

@Tool(
    name="create_network",
    description="Create a new Docker network"
)
async def create_network(
    request: CreateNetworkRequest
) -> Dict[str, Any]:
    """
    Create a new Docker network with the specified configuration.
    
    Args:
        name: Name of the network
        driver: Network driver to use (bridge, overlay, etc.)
        check_duplicate: Check for networks with duplicate names
        internal: Create an internal network (no external access)
        attachable: Enable manual container attachment
        ipam: IP Address Management configuration
        labels: Labels to set on the network
        
    Returns:
        Dictionary containing the created network details
    """
    try:
        if not request.name:
            raise ValueError("Network name is required")
            
        # Build the create command
        cmd = ['create']
        
        # Add driver if specified
        if request.driver:
            cmd.extend(['--driver', request.driver])
            
        # Add flags if specified
        if getattr(request, 'check_duplicate', True):
            cmd.append('--check-duplicate')
            
        if getattr(request, 'internal', False):
            cmd.append('--internal')
            
        if getattr(request, 'attachable', False):
            cmd.append('--attachable')
            
        # Add IPAM options if specified
        if hasattr(request, 'ipam') and request.ipam:
            if request.ipam.driver:
                cmd.extend(['--ipam-driver', request.ipam.driver])
                
            if request.ipam.options:
                for key, value in request.ipam.options.items():
                    cmd.extend(['--ipam-opt', f"{key}={value}"])
                    
            if request.ipam.config:
                for config in request.ipam.config:
                    if config.subnet:
                        cmd.extend(['--subnet', config.subnet])
                    if config.ip_range:
                        cmd.extend(['--ip-range', config.ip_range])
                    if config.gateway:
                        cmd.extend(['--gateway', config.gateway])
                        
        # Add labels if specified
        if hasattr(request, 'labels') and request.labels:
            for key, value in request.labels.items():
                cmd.extend(['--label', f"{key}={value}"])
                
        # Add the network name
        cmd.append(request.name)
        
        # Execute the create command
        result = run_docker_command('network', cmd, format_json=True)
        
        if not result:
            return {
                "success": False,
                "error": f"Failed to create network '{request.name}'",
                "network_name": request.name
            }
            
        return {
            "success": True,
            "message": f"Network '{request.name}' created successfully",
            "network": result,
            "network_id": result.get('Id', ''),
            "network_name": request.name
        }
        
    except Exception as e:
        return handle_error(e, f"create_network({request.name})")

@Tool(
    name="inspect_network",
    description="Get detailed information about a network"
)
async def inspect_network(
    request: NetworkOperationRequest
) -> Dict[str, Any]:
    """Get detailed information about a specific network."""
    try:
        # Execute the inspect command to get network details
        result = run_docker_command(
            'network',
            ['inspect', request.network_id],
            format_json=True
        )
        
        if not result:
            return {
                "success": False,
                "error": f"Network '{request.network_id}' not found",
                "network_id": request.network_id
            }
            
        # Get the first network if result is a list
        network = result[0] if isinstance(result, list) else result
        
        return {
            "success": True,
            "message": f"Network '{request.network_id}' inspected successfully",
            "network": network,
            "network_id": request.network_id
        }
        
    except Exception as e:
        return handle_error(e, f"inspect_network({request.network_id})")

@Tool(
    name="list_containers_on_network",
    description="List all containers connected to a specific network"
)
async def list_containers_on_network(
    request: NetworkOperationRequest
) -> Dict[str, Any]:
    """
    List all containers connected to a specific Docker network.
    
    Args:
        network_id: ID or name of the network
        
    Returns:
        List of containers connected to the network with their details
    """
    try:
        if not request.network_id:
            raise ValueError("Network ID is required")
            
        # Execute the inspect command to get network details
        result = run_docker_command(
            'network',
            ['inspect', request.network_id],
            format_json=True
        )
        
        if not result:
            return {
                "success": False,
                "error": f"Network '{request.network_id}' not found",
                "network_id": request.network_id,
                "containers": []
            }
            
        # Get the first network if result is a list
        network = result[0] if isinstance(result, list) else result
        
        # Extract container information
        containers = []
        if 'Containers' in network and network['Containers']:
            for container_id, container_info in network['Containers'].items():
                containers.append({
                    'id': container_id,
                    'name': container_info.get('Name', ''),
                    'endpoint_id': container_info.get('EndpointID', ''),
                    'mac_address': container_info.get('MacAddress', ''),
                    'ipv4_address': container_info.get('IPv4Address', ''),
                    'ipv6_address': container_info.get('IPv6Address', '')
                })
        
        return {
            "success": True,
            "message": f"Found {len(containers)} containers on network '{request.network_id}'",
            "network_id": request.network_id,
            "containers": containers
        }
        
    except Exception as e:
        return handle_error(e, f"list_containers_on_network({request.network_id})")

@Tool(
    name="prune_networks",
    description="Remove unused Docker networks"
)
async def prune_networks(
    request: PruneNetworksRequest
) -> Dict[str, Any]:
    """
    Remove all unused Docker networks.
    
    Args:
        filters: Key/value pairs to filter networks for pruning
        until: Only remove networks created before this timestamp
        
    Returns:
        Dictionary containing list of pruned networks and space reclaimed
    """
    try:
        # Apply filters
        filters = request.filters or {}
        if request.until:
            filters["until"] = request.until
            
        # Prune unused networks
        result = await network_mgr.prune_networks(filters=filters)
        
        return PruneNetworksResponse(
            networks_deleted=result.get("NetworksDeleted", []),
            space_reclaimed=result.get("SpaceReclaimed", 0)
        ).dict()
        
    except Exception as e:
        return PruneNetworksResponse(
            networks_deleted=[],
            space_reclaimed=0,
            success=False,
            error=f"Failed to prune networks: {str(e)}"
        ).dict()

@Tool(
    name="remove_network",
    description="Remove a Docker network"
)
async def remove_network(
    request: NetworkOperationRequest
) -> Dict[str, Any]:
    """
    Remove a Docker network by ID or name.
    
    Args:
        network_id: ID or name of the network to remove
        force: Force removal even if in use (use with caution)
        
    Returns:
        Dictionary containing operation status
    """
    try:
        # Check if network exists and is not in use
        network = await network_mgr.inspect_network(request.network_id)
        if not network:
            raise ValueError(f"Network '{request.network_id}' not found")
            
        # Check if network is in use
        containers = await network_mgr.list_containers_on_network(request.network_id)
        if containers and not getattr(request, 'force', False):
            return NetworkResponse(
                success=False,
                message=f"Network '{request.network_id}' is in use by {len(containers)} containers. Use force=True to remove anyway.",
                error="Network in use"
            ).dict()
        
        # Remove the network
        await network_mgr.remove_network(
            network_id=request.network_id,
            force=getattr(request, 'force', False)
        )
        
        return NetworkResponse(
            success=True,
            message=f"Network '{request.network_id}' removed successfully"
        ).dict()
        
    except Exception as e:
        return NetworkResponse(
            success=False,
            message=f"Failed to remove network '{request.network_id}': {str(e)}",
            error=str(e)
        ).dict()

@Tool(
    name="connect_container",
    description="Connect a container to a network with advanced options"
)
async def connect_container(
    request: ConnectContainerRequest
) -> Dict[str, Any]:
    """
    Connect a container to a network with advanced configuration options.
    
    Supports:
    - Custom IP address assignment
    - Network aliases
    - Link-local IPs
    - Endpoint configuration
    """
    try:
        # Prepare endpoint configuration
        endpoint_config = {}
        
        # Add basic endpoint settings if provided
        if request.endpoint_config:
            endpoint_config = request.endpoint_config.dict(exclude_none=True)
        
        # Add IP addresses if specified
        if request.ipv4_address or request.ipv6_address:
            if "IPAMConfig" not in endpoint_config:
                endpoint_config["IPAMConfig"] = {}
            
            if request.ipv4_address:
                endpoint_config["IPAMConfig"]["IPv4Address"] = request.ipv4_address
            if request.ipv6_address:
                endpoint_config["IPAMConfig"]["IPv6Address"] = request.ipv6_address
        
        # Add aliases if specified
        if request.aliases:
            endpoint_config["Aliases"] = request.aliases
        
        # Connect the container
        await network_mgr.connect_container(
            network_id=request.network_id,
            container_id=request.container_id,
            endpoint_config=endpoint_config or None
        )
        
        return NetworkResponse(
            success=True,
            message=f"Container '{request.container_id}' connected to network '{request.network_id}'"
        ).dict()
        
    except Exception as e:
        return NetworkResponse(
            success=False,
            message=f"Failed to connect container to network: {str(e)}",
            error=str(e)
        ).dict()

@Tool(
    name="disconnect_container",
    description="Disconnect a container from a network"
)
async def disconnect_container(
    request: DisconnectContainerRequest
) -> Dict[str, Any]:
    """
    Disconnect a container from a network.
    
    Args:
        network_id: ID or name of the network
        container_id: ID or name of the container
        force: Force disconnect even if container is running
        
    Returns:
        Dictionary containing operation status
    """
    try:
        # Check if container is connected to the network
        containers = await network_mgr.list_containers_on_network(request.network_id)
        container = next((c for c in containers if c["Id"] == request.container_id or 
                         request.container_id in c.get("Names", [])), None)
        
        if not container:
            return NetworkResponse(
                success=False,
                message=f"Container '{request.container_id}' is not connected to network '{request.network_id}'",
                error="Container not connected"
            ).dict()
        
        # Disconnect the container
        await network_mgr.disconnect_container(
            network_id=request.network_id,
            container_id=request.container_id,
            force=request.force
        )
        
        return NetworkResponse(
            success=True,
            message=f"Container '{request.container_id}' disconnected from network '{request.network_id}'"
        ).dict()
        
    except Exception as e:
        return NetworkResponse(
            success=False,
            message=f"Failed to disconnect container: {str(e)}",
            error=str(e)
        ).dict()

@Tool(
    name="get_network_stats",
    description="Get statistics for a Docker network"
)
async def get_network_stats(
    request: NetworkStatsRequest
) -> Dict[str, Any]:
    """
    Get statistics for a specific Docker network.
    
    Args:
        network_id: ID or name of the network
        
    Returns:
        Dictionary containing network statistics
    """
    try:
        if not request.network_id:
            raise ValueError("Network ID is required")
            
        # First, get the network details
        network_info = run_docker_command(
            'network',
            ['inspect', request.network_id],
            format_json=True
        )
        
        if not network_info:
            return {
                "success": False,
                "error": f"Network '{request.network_id}' not found",
                "network_id": request.network_id
            }
            
        # Get the first network if result is a list
        network = network_info[0] if isinstance(network_info, list) else network_info
        
        # Get container statistics
        stats = {
            "network_id": request.network_id,
            "network_name": network.get('Name', ''),
            "driver": network.get('Driver', ''),
            "scope": network.get('Scope', ''),
            "ipam": network.get('IPAM', {}),
            "containers": {},
            "interfaces": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get container details if available
        if 'Containers' in network and network['Containers']:
            for container_id, container_info in network['Containers'].items():
                container_name = container_info.get('Name', '')
                
                # Get container stats
                container_stats = run_docker_command(
                    'container',
                    ['stats', '--no-stream', '--format', 'json', container_id],
                    format_json=True
                )
                
                if container_stats and isinstance(container_stats, list):
                    stats['containers'][container_id] = {
                        'name': container_name,
                        'stats': container_stats[0]
                    }
                
                # Get network interface details
                if 'EndpointID' in container_info:
                    endpoint_id = container_info['EndpointID']
                    stats['interfaces'][endpoint_id] = {
                        'container_id': container_id,
                        'container_name': container_name,
                        'mac_address': container_info.get('MacAddress', ''),
                        'ipv4_address': container_info.get('IPv4Address', ''),
                        'ipv6_address': container_info.get('IPv6Address', '')
                    }
        
        return {
            "success": True,
            "message": f"Statistics for network '{request.network_id}'",
            "network_id": request.network_id,
            "stats": stats
        }
        
    except Exception as e:
        return handle_error(e, f"get_network_stats({request.network_id})")

@Tool(
    name="test_network_connectivity",
    description="Test network connectivity between containers"
)
async def test_network_connectivity(
    request: NetworkConnectivityTestRequest
) -> Dict[str, Any]:
    """
    Test network connectivity between containers or to external hosts.
    
    Args:
        source: Source container ID or name
        target: Target container ID, name, or IP address
        protocol: Protocol to test (tcp, udp, icmp)
        port: Port number (required for tcp/udp)
        timeout: Test timeout in seconds
        
    Returns:
        Dictionary containing test results
    """
    try:
        if not request.source or not request.target:
            raise ValueError("Source and target must be specified")
            
        # Validate request
        if request.protocol in ["tcp", "udp"] and not request.port:
            raise ValueError(f"Port is required for {request.protocol.upper()} tests")
            
        # Prepare test command based on protocol
        if request.protocol == "icmp":
            cmd = ["exec", "-i", request.source, "ping", "-c", "1", "-W", str(request.timeout or 5), request.target]
        elif request.protocol == "tcp":
            # Use netcat for TCP connectivity test
            cmd = ["exec", "-i", request.source, "sh", "-c", 
                  f"nc -z -w {request.timeout or 5} {request.target} {request.port}"]
        elif request.protocol == "udp":
            # Use netcat for UDP connectivity test
            cmd = ["exec", "-i", request.source, "sh", "-c", 
                  f"nc -z -u -w {request.timeout or 5} {request.target} {request.port}"]
        else:
            raise ValueError(f"Unsupported protocol: {request.protocol}")
        
        # Execute the connectivity test
        start_time = datetime.utcnow()
        result = run_docker_command("container", cmd, format_json=False, check=False)
        end_time = datetime.utcnow()
        
        # Calculate duration
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Determine test result
        success = result.returncode == 0
        
        return {
            "success": success,
            "source": request.source,
            "target": request.target,
            "protocol": request.protocol,
            "port": request.port,
            "timestamp": end_time.isoformat(),
            "duration_ms": duration_ms,
            "result": {
                "exit_code": result.returncode,
                "output": result.stdout or "",
                "error": result.stderr or ""
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Connectivity test failed: {str(e)}",
            "source": getattr(request, 'source', ''),
            "target": getattr(request, 'target', ''),
            "protocol": getattr(request, 'protocol', ''),
            "port": getattr(request, 'port', None)
        }
