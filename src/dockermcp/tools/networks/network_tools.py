"""
Network management tools for Docker MCP.

This module provides FastMCP 2.12 compatible tools for managing Docker networks.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, cast

# FastMCP 2.12 imports
from fastmcp.tools import tool, Tool

# Import custom exceptions
from ..containers.container_models import ContainerError

# Local imports
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

from dockermcp.logging_config import logger

# Get a child logger for this module
logger = logger.getChild('network_tools')

def handle_error(error: Exception, context: str = "") -> Dict[str, Any]:
    """Handle errors consistently across all tools."""
    error_message = f"{context}: {str(error)}" if context else str(error)
    logger.error(error_message, exc_info=True)
    return {
        "status": "error",
        "message": error_message,
        "error_type": error.__class__.__name__,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@tool(
    name="prune_networks",
    description="Remove unused Docker networks",
    parameters={
        'type': 'object',
        'properties': {
            'filters': {
                'type': 'object',
                'description': 'Filters to process on the prune list',
                'additionalProperties': {'type': 'string'},
                'default': {}
            },
            'until': {
                'type': 'string',
                'description': 'Only remove networks created before this timestamp',
                'format': 'date-time',
                'default': None
            },
            'force': {
                'type': 'boolean',
                'description': 'Force removal of networks even if in use',
                'default': False
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds for the operation',
                'minimum': 1,
                'maximum': 300,
                'default': 30
            }
        },
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'PruneNetworksResult',
        'properties': {
            'networks_deleted': {'type': 'array', 'items': {'type': 'string'}},
            'space_reclaimed': {'type': 'integer'},
            'success': {'type': 'boolean'},
            'message': {'type': 'string'},
            'timestamp': {'type': 'string'}
        },
        'required': ['networks_deleted', 'space_reclaimed', 'success', 'message', 'timestamp']
    }
)
async def prune_networks(
    filters: Optional[Dict[str, str]] = None,
    until: Optional[str] = None,
    force: bool = False,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Remove unused Docker networks.

    This function prunes unused Docker networks, with options to filter by labels,
    creation time, and other attributes. It can also force removal of networks
    that are in use (with caution).

    Args:
        filters: Key/value pairs to filter networks for pruning.
            Common filters include:
            - 'label' (e.g., {'label': ['maintainer=devops']})
            - 'until' (e.g., {'until': '24h'})
            - 'name' (e.g., {'name': 'my-network'})
        until: Only remove networks created before this timestamp.
            Can be a timestamp (e.g., '2023-01-01T00:00:00Z') or a duration (e.g., '24h')
        force: If True, removes networks even if they are in use by containers.
            Use with caution as this may disrupt running containers.
        timeout: Maximum time in seconds to wait for the operation to complete.

    Returns:
        Dictionary containing:
        - networks_deleted: List of deleted network IDs
        - space_reclaimed: Disk space reclaimed in bytes
        - success: Boolean indicating if the operation was successful
        - message: Status message
        - timestamp: ISO 8601 timestamp of when the operation completed

    Raises:
        ContainerError: If the operation fails or times out
        ValueError: If input validation fails
    """
    start_time = time.time()
    logger.info(
        "Pruning unused networks (filters: %s, until: %s, force: %s, timeout: %ds)",
        filters, until, force, timeout
    )

    try:
        # Input validation
        if not isinstance(timeout, int) or timeout < 1 or timeout > 300:
            error_msg = f"timeout must be an integer between 1 and 300, got {timeout}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if until and not isinstance(until, str):
            error_msg = f"until must be a string, got {type(until).__name__}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if filters and not isinstance(filters, dict):
            error_msg = f"filters must be a dictionary, got {type(filters).__name__}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Build the prune command
        cmd = ["network", "prune"]
        
        # Add force flag if specified
        if force:
            cmd.append("--force")
        
        # Add filters if specified
        if filters:
            for key, value in filters.items():
                cmd.extend(["--filter", f"{key}={value}"])
        
        # Add until filter if specified
        if until:
            cmd.extend(["--filter", f"until={until}"])
        
        # Add JSON output format
        cmd.extend(["--format", "{{json .}}"])
        
        # Execute the prune command with timeout
        logger.debug("Executing Docker command: %s", " ".join(cmd))
        
        try:
            result = await run_docker_command(
                '',
                cmd,
                format_json=True,
                timeout=timeout
            )
            
            # Parse the result
            if not result:
                logger.warning("No networks were pruned")
                result = {"NetworksDeleted": None, "SpaceReclaimed": 0}
            
            # Ensure we have the expected fields
            networks_deleted = result.get("NetworksDeleted") or []
            space_reclaimed = int(result.get("SpaceReclaimed", 0))
            
            # Log the result
            logger.info(
                "Successfully pruned %d networks, reclaimed %d bytes",
                len(networks_deleted), space_reclaimed
            )
            
            return {
                'networks_deleted': networks_deleted,
                'space_reclaimed': space_reclaimed,
                'success': True,
                'message': f"Successfully pruned {len(networks_deleted)} networks",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except asyncio.TimeoutError as e:
            error_msg = f"Network prune operation timed out after {timeout} seconds"
            logger.error(error_msg)
            raise ContainerError(error_msg) from e
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse network prune output: {str(e)}"
            logger.exception(error_msg)
            raise ContainerError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Failed to prune networks: {str(e)}"
            logger.exception(
                "Unexpected error during network prune",
                exc_info=True,
                extra={
                    'filters': filters,
                    'until': until,
                    'force': force,
                    'timeout': timeout,
                    'elapsed_seconds': time.time() - start_time
                }
            )
            raise ContainerError(error_msg) from e
            
    except ContainerError:
        raise  # Re-raise ContainerError as is
        
    except Exception as e:
        error_msg = f"Unexpected error in prune_networks: {str(e)}"
        logger.exception(
            error_msg,
            extra={
                'exception_type': type(e).__name__,
                'elapsed_seconds': time.time() - start_time
            }
        )
        raise ContainerError(error_msg) from e

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

# Network listing tool with filtering options
@tool(
    name="list_networks",
    description="List all Docker networks with optional filtering",
    parameters={
        'type': 'object',
        'properties': {
            'filters': {
                'type': 'object',
                'description': 'Filter networks by key/value pairs',
                'additionalProperties': {'type': 'string'},
                'default': {}
            },
            'scope': {
                'type': 'string',
                'description': 'Filter by network scope (local, swarm, etc.)',
                'enum': ['local', 'swarm', None],
                'default': None
            },
            'driver': {
                'type': 'string',
                'description': 'Filter by network driver (e.g., bridge, overlay, host, none)',
                'default': None
            },
            'verbose': {
                'type': 'boolean',
                'description': 'Include detailed network information',
                'default': False
            }
        },
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'ListNetworksResult',
        'properties': {
            'networks': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'name': {'type': 'string'},
                        'driver': {'type': 'string'},
                        'scope': {'type': 'string'},
                        'ipam': {'type': 'object'},
                        'containers': {'type': 'object'},
                        'options': {'type': 'object'},
                        'labels': {'type': 'object'},
                        'created': {'type': 'string', 'format': 'date-time'}
                    }
                },
                'description': 'List of network objects with their configurations'
            },
            'count': {
                'type': 'integer',
                'description': 'Total number of networks returned'
            },
            'success': {
                'type': 'boolean',
                'description': 'Whether the operation was successful'
            },
            'message': {
                'type': 'string',
                'description': 'Status message'
            },
            'timestamp': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the operation completed'
            }
        }
    }
)
async def list_networks(
    filters: Optional[Dict[str, str]] = None,
    scope: Optional[str] = None,
    driver: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    List all Docker networks with optional filtering.
    
    This function lists all Docker networks, with options to filter by various criteria
    and format the output.
    
    Args:
        filters: Dictionary of filter key/value pairs
        scope: Filter by network scope (local, swarm, etc.)
        driver: Filter by network driver
        verbose: Include detailed network information
        
    Returns:
        Dictionary containing list of networks and their details
        
    Raises:
        ContainerError: If the operation fails
    """
    try:
        logger.info("Listing Docker networks with filters: %s, scope: %s, driver: %s", 
                   filters, scope, driver)
        
        if filters is None:
            filters = {}
            
        if scope:
            filters['scope'] = scope
        if driver:
            filters['driver'] = driver
            
        # Build the docker command
        cmd = ["network", "ls", "--format", "{{json .}}"]
        
        # Add filters
        for key, value in filters.items():
            if value is not None:  # Only add non-None filters
                cmd.extend(['--filter', f'{key}={value}'])
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=False)
        
        if result.returncode != 0:
            error_msg = f"Failed to list networks: {result.stderr or 'Unknown error'}"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        # Parse the result
        networks = []
        if result.stdout:
            try:
                # Parse each line as a separate JSON object
                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    net = json.loads(line)
                    networks.append({
                        'id': net.get('ID', ''),
                        'name': net.get('Name', ''),
                        'driver': net.get('Driver', ''),
                        'scope': net.get('Scope', ''),
                        'created': net.get('CreatedAt', '')
                    })
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse network list: %s", str(e))
                networks = []
        
        response = {
            'networks': networks,
            'count': len(networks),
            'success': True,
            'message': f"Successfully listed {len(networks)} networks",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Successfully listed %d networks", len(networks))
        return response
        
    except ContainerError:
        raise  # Re-raise ContainerError as is
    except asyncio.TimeoutError as e:
        error_msg = "Timeout while listing networks"
        logger.error(error_msg)
        raise ContainerError(error_msg) from e
    except Exception as e:
        return handle_error(e, "listing networks")

@tool(
    name="create_network",
    description="Create a new Docker network with advanced configuration options",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Name of the network to create',
                'minLength': 2,
                'maxLength': 255,
                'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'
            },
            'driver': {
                'type': 'string',
                'description': 'Network driver to use (e.g., bridge, overlay, host, none)',
                'default': 'bridge',
                'enum': ['bridge', 'overlay', 'host', 'macvlan', 'none']
            },
            'internal': {
                'type': 'boolean',
                'description': 'Restrict external access to the network',
                'default': False
            },
            'attachable': {
                'type': 'boolean',
                'description': 'Enable manual container attachment',
                'default': False
            },
            'ingress': {
                'type': 'boolean',
                'description': 'Create swarm routing-mesh network',
                'default': False
            },
            'enable_ipv6': {
                'type': 'boolean',
                'description': 'Enable IPv6 networking',
                'default': False
            },
            'labels': {
                'type': 'object',
                'description': 'Arbitrary key/value metadata',
                'additionalProperties': {'type': 'string'},
                'default': {}
            },
            'options': {
                'type': 'object',
                'description': 'Network-specific options',
                'additionalProperties': {'type': 'string'},
                'default': {}
            },
            'ipam': {
                'type': 'object',
                'description': 'IP Address Management configuration',
                'properties': {
                    'driver': {
                        'type': 'string',
                        'description': 'IPAM driver to use',
                        'default': 'default'
                    },
                    'config': {
                        'type': 'array',
                        'description': 'List of IPAM configuration options',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'subnet': {'type': 'string', 'format': 'ipv4-cidr'},
                                'ip_range': {'type': 'string', 'format': 'ipv4-cidr'},
                                'gateway': {'type': 'string', 'format': 'ipv4'},
                                'aux_addresses': {
                                    'type': 'object',
                                    'additionalProperties': {'type': 'string', 'format': 'ipv4'}
                                }
                            }
                        }
                    },
                    'options': {
                        'type': 'object',
                        'additionalProperties': {'type': 'string'}
                    }
                },
                'default': {}
            }
        },
        'required': ['name'],
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'CreateNetworkResult',
        'properties': {
            'id': {
                'type': 'string',
                'description': 'The ID of the created network'
            },
            'name': {
                'type': 'string',
                'description': 'The name of the created network'
            },
            'driver': {
                'type': 'string',
                'description': 'The network driver used',
                'enum': ['bridge', 'overlay', 'host', 'macvlan', 'none']
            },
            'scope': {
                'type': 'string',
                'description': 'The scope of the network (e.g., local, swarm)'
            },
            'ipam': {
                'type': 'object',
                'description': 'IP Address Management configuration',
                'properties': {
                    'driver': {'type': 'string'},
                    'config': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'subnet': {'type': 'string', 'format': 'ipv4-cidr'},
                                'ip_range': {'type': 'string', 'format': 'ipv4-cidr'},
                                'gateway': {'type': 'string', 'format': 'ipv4'},
                                'aux_addresses': {'type': 'object'}
                            }
                        }
                    },
                    'options': {'type': 'object'}
                }
            },
            'options': {
                'type': 'object',
                'description': 'Network-specific options',
                'additionalProperties': {'type': 'string'}
            },
            'labels': {
                'type': 'object',
                'description': 'User-defined key/value metadata',
                'additionalProperties': {'type': 'string'}
            },
            'created': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the network was created'
            },
            'internal': {
                'type': 'boolean',
                'description': 'Whether the network restricts external access'
            },
            'attachable': {
                'type': 'boolean',
                'description': 'Whether manual container attachment is enabled'
            },
            'ingress': {
                'type': 'boolean',
                'description': 'Whether this is a swarm routing-mesh network'
            },
            'enable_ipv6': {
                'type': 'boolean',
                'description': 'Whether IPv6 networking is enabled'
            },
            'success': {
                'type': 'boolean',
                'description': 'Whether the network creation was successful'
            },
            'message': {
                'type': 'string',
                'description': 'Status message about the operation'
            },
            'timestamp': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the operation completed'
            }
        },
        'required': [
            'id', 'name', 'driver', 'scope', 'ipam', 'options', 
            'labels', 'created', 'success', 'message', 'timestamp'
        ]
    }
)
async def create_network(
    name: str,
    driver: str = "bridge",
    internal: bool = False,
    attachable: bool = False,
    ingress: bool = False,
    enable_ipv6: bool = False,
    labels: Optional[Dict[str, str]] = None,
    options: Optional[Dict[str, str]] = None,
    ipam: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new Docker network with advanced configuration options.

    This function creates a Docker network with the specified configuration, including
    custom IPAM settings, IPv6 support, and network options.

    Args:
        name: Name of the network to create
        driver: Network driver to use (e.g., bridge, overlay, host, none)
        internal: If True, restricts external access to the network
        attachable: If True, enables manual container attachment
        ingress: If True, creates a swarm routing-mesh network
        enable_ipv6: If True, enables IPv6 networking
        labels: Key/value pairs for network labels
        options: Network-specific options
        ipam: IP Address Management configuration
            - driver: IPAM driver to use
            - config: List of IPAM configuration options
            - options: IPAM driver options

    Returns:
        Dictionary containing the created network details

    Raises:
        ContainerError: If network creation fails
    """
    try:
        logger.info("Creating network '%s' with driver '%s'", name, driver)
        
        # Initialize default values
        labels = labels or {}
        options = options or {}
        ipam = ipam or {}
        
        # Build the docker command
        cmd = ["network", "create"]
        
        # Add network options
        cmd.extend(["--driver", driver])
        
        if internal:
            cmd.append("--internal")
        if attachable:
            cmd.append("--attachable")
        if ingress:
            cmd.append("--ingress")
        if enable_ipv6:
            cmd.append("--ipv6")
        
        # Add labels
        for key, value in labels.items():
            cmd.extend(["--label", f"{key}={value}"])
        
        # Add network options
        for key, value in options.items():
            cmd.extend(["--opt", f"{key}={value}"])
        
        # Add IPAM configuration if provided
        ipam_driver = ipam.get('driver')
        if ipam_driver:
            cmd.extend(["--ipam-driver", ipam_driver])
        
        ipam_configs = ipam.get('config', [])
        for config in ipam_configs:
            if 'subnet' in config:
                cmd.extend(["--subnet", config['subnet']])
            if 'ip_range' in config:
                cmd.extend(["--ip-range", config['ip_range']])
            if 'gateway' in config:
                cmd.extend(["--gateway", config['gateway']])
        
        # Add IPAM options
        ipam_opts = ipam.get('options', {})
        for key, value in ipam_opts.items():
            cmd.extend(["--ipam-opt", f"{key}={value}"])
        
        # Add network name
        cmd.append(name)
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=False)
        
        if result.returncode != 0:
            error_msg = result.stderr or f"Failed to create network '{name}'"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        # Get the created network details
        inspect_cmd = ["network", "inspect", name]
        inspect_result = await run_docker_command('', inspect_cmd, format_json=True)
        
        if not inspect_result or not isinstance(inspect_result, list):
            error_msg = f"Network '{name}' created but failed to inspect it"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        network_info = inspect_result[0]
        logger.info("Successfully created network '%s' (ID: %s)", name, network_info.get('Id', 'unknown'))
        
        # Format the response
        return {
            'id': network_info.get('Id', ''),
            'name': network_info.get('Name', name),
            'driver': network_info.get('Driver', driver),
            'scope': network_info.get('Scope', 'local'),
            'ipam': network_info.get('IPAM', {}),
            'options': network_info.get('Options', {}),
            'labels': network_info.get('Labels', labels or {}),
            'internal': network_info.get('Internal', internal),
            'attachable': network_info.get('Attachable', attachable),
            'ingress': network_info.get('Ingress', ingress),
            'enable_ipv6': network_info.get('EnableIPv6', enable_ipv6),
            'success': True,
            'message': f"Successfully created network '{name}'",
            'created': network_info.get('Created', datetime.now(timezone.utc).isoformat())
        }
        
    except ContainerError:
        raise  # Re-raise ContainerError as is
    except Exception as e:
        error_msg = f"Unexpected error creating network '{name}': {str(e)}"
        logger.exception(error_msg)
        raise ContainerError(error_msg) from e

@tool(
    name="inspect_network",
    description="Get detailed information about a specific Docker network",
    parameters={
        'type': 'object',
        'properties': {
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name to inspect',
                'minLength': 1,
                'maxLength': 64
            },
            'verbose': {
                'type': 'boolean',
                'description': 'Include detailed network information',
                'default': False
            },
            'scope': {
                'type': 'string',
                'description': 'Filter by network scope (local, swarm, etc.)',
                'enum': ['local', 'swarm', None],
                'default': None
            }
        },
        'required': ['network_id'],
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'InspectNetworkResult',
        'properties': {
            'id': {
                'type': 'string',
                'description': 'The ID of the network',
                'minLength': 64,
                'maxLength': 64
            },
            'name': {
                'type': 'string',
                'description': 'The name of the network',
                'minLength': 2,
                'maxLength': 255
            },
            'driver': {
                'type': 'string',
                'description': 'The network driver used',
                'enum': ['bridge', 'overlay', 'host', 'macvlan', 'none']
            },
            'scope': {
                'type': 'string',
                'description': 'The scope of the network',
                'enum': ['local', 'swarm']
            },
            'ipam': {
                'type': 'object',
                'description': 'IP Address Management configuration',
                'properties': {
                    'driver': {'type': 'string'},
                    'config': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'subnet': {'type': 'string', 'format': 'ipv4-cidr'},
                                'ip_range': {'type': 'string', 'format': 'ipv4-cidr'},
                                'gateway': {'type': 'string', 'format': 'ipv4'},
                                'aux_addresses': {'type': 'object'}
                            }
                        }
                    },
                    'options': {'type': 'object'}
                }
            },
            'containers': {
                'type': 'object',
                'description': 'Containers connected to the network',
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'endpoint_id': {'type': 'string'},
                        'mac_address': {'type': 'string', 'format': 'mac-address'},
                        'ipv4_address': {'type': 'string', 'format': 'ipv4'},
                        'ipv6_address': {'type': 'string', 'format': 'ipv6'}
                    }
                }
            },
            'options': {
                'type': 'object',
                'description': 'Network-specific options',
                'additionalProperties': {'type': 'string'}
            },
            'labels': {
                'type': 'object',
                'description': 'User-defined key/value metadata',
                'additionalProperties': {'type': 'string'}
            },
            'created': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the network was created'
            },
            'internal': {
                'type': 'boolean',
                'description': 'Whether the network restricts external access'
            },
            'enable_ipv6': {
                'type': 'boolean',
                'description': 'Whether IPv6 networking is enabled'
            },
            'attachable': {
                'type': 'boolean',
                'description': 'Whether manual container attachment is enabled'
            },
            'ingress': {
                'type': 'boolean',
                'description': 'Whether this is a swarm routing-mesh network'
            },
            'success': {
                'type': 'boolean',
                'description': 'Whether the inspection was successful'
            },
            'message': {
                'type': 'string',
                'description': 'Status message about the operation'
            },
            'timestamp': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the operation completed'
            }
        },
        'required': [
            'id', 'name', 'driver', 'scope', 'ipam', 'containers', 
            'options', 'labels', 'created', 'internal', 'enable_ipv6',
            'attachable', 'ingress', 'success', 'message', 'timestamp'
        ]
    }
)
async def inspect_network(
    network_id: str,
    verbose: bool = False,
    scope: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific Docker network.

    This function retrieves detailed information about a Docker network,
    including its configuration, connected containers, and IPAM settings.

    Args:
        network_id: The ID or name of the network to inspect
        verbose: If True, includes additional detailed information
        scope: Optional scope filter (local, swarm, etc.)

    Returns:
        Dictionary containing the network details

    Raises:
        ContainerError: If network inspection fails or network is not found
    """
    try:
        logger.info("Inspecting network '%s' (verbose: %s, scope: %s)", 
                   network_id, verbose, scope or 'any')
        
        if not network_id:
            error_msg = "Network ID or name is required"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        # Build the docker command
        cmd = ["network", "inspect", network_id]
        
        # Add scope filter if provided
        if scope:
            cmd.extend(["--scope", scope])
        
        # Execute the command
        result = await run_docker_command('', cmd, format_json=True)
        
        if not result or not isinstance(result, list):
            error_msg = f"Network '{network_id}' not found"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        network_info = result[0]
        
        # Format the response
        response = {
            'id': network_info.get('Id', ''),
            'name': network_info.get('Name', network_id),
            'driver': network_info.get('Driver', ''),
            'scope': network_info.get('Scope', 'local'),
            'ipam': network_info.get('IPAM', {}),
            'containers': {},
            'options': network_info.get('Options', {}),
            'labels': network_info.get('Labels', {}),
            'created': network_info.get('Created', ''),
            'internal': network_info.get('Internal', False),
            'enable_ipv6': network_info.get('EnableIPv6', False),
            'attachable': network_info.get('Attachable', False),
            'ingress': network_info.get('Ingress', False)
        }
        
        # Add container information if verbose mode is enabled
        if verbose and 'Containers' in network_info:
            for container_id, container_info in network_info['Containers'].items():
                response['containers'][container_id] = {
                    'name': container_info.get('Name', ''),
                    'endpoint_id': container_info.get('EndpointID', ''),
                    'mac_address': container_info.get('MacAddress', ''),
                    'ipv4_address': container_info.get('IPv4Address', ''),
                    'ipv6_address': container_info.get('IPv6Address', '')
                }
        
        logger.info("Successfully inspected network '%s' (ID: %s)", 
                   response['name'], response['id'])
        
        return response
        
    except ContainerError:
        raise  # Re-raise ContainerError as is
    except Exception as e:
        error_msg = f"Unexpected error inspecting network '{network_id}': {str(e)}"
        logger.exception(error_msg)
        raise ContainerError(error_msg) from e

@tool(
    name="remove_network",
    description="Remove a Docker network by ID or name",
    parameters={
        'type': 'object',
        'properties': {
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name to remove',
                'minLength': 1,
                'maxLength': 64
            },
            'force': {
                'type': 'boolean',
                'description': 'Force removal even if network is in use',
                'default': False
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds for network removal',
                'minimum': 1,
                'default': 30
            }
        },
        'required': ['network_id'],
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'RemoveNetworkResult',
        'properties': {
            'id': {
                'type': 'string',
                'description': 'The ID of the removed network',
                'minLength': 64,
                'maxLength': 64
            },
            'name': {
                'type': 'string',
                'description': 'The name of the removed network',
                'minLength': 2,
                'maxLength': 255
            },
            'success': {
                'type': 'boolean',
                'description': 'Whether the network was successfully removed'
            },
            'message': {
                'type': 'string',
                'description': 'Status message about the removal operation'
            },
            'timestamp': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the network was removed'
            },
            'force_removed': {
                'type': 'boolean',
                'description': 'Whether the network was force removed',
                'default': False
            },
            'containers_disconnected': {
                'type': 'integer',
                'description': 'Number of containers that were disconnected',
                'minimum': 0
            },
            'network_driver': {
                'type': 'string',
                'description': 'The driver used by the removed network',
                'enum': ['bridge', 'overlay', 'host', 'macvlan', 'none']
            },
            'scope': {
                'type': 'string',
                'description': 'The scope of the removed network',
                'enum': ['local', 'swarm']
            },
            'created': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the network was created'
            },
            'labels': {
                'type': 'object',
                'description': 'Labels that were applied to the network',
                'additionalProperties': {'type': 'string'}
            }
        },
        'required': [
            'id', 'name', 'success', 'message', 'timestamp', 'force_removed',
            'network_driver', 'scope', 'created'
        ]
    }
)
async def remove_network(
    network_id: str,
    force: bool = False,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Remove a Docker network by ID or name.

    This function removes a Docker network, with options to force removal
    and set a timeout for the operation.

    Args:
        network_id: The ID or name of the network to remove
        force: If True, removes the network even if it's in use
        timeout: Timeout in seconds for the removal operation

    Returns:
        Dictionary containing the removal status and details

    Raises:
        ContainerError: If network removal fails or network is not found
    """
    try:
        logger.info("Removing network '%s' (force: %s, timeout: %ds)", 
                   network_id, force, timeout)
        
        if not network_id:
            error_msg = "Network ID or name is required"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        # First, get network details for the response
        inspect_cmd = ["network", "inspect", network_id, "--format", "{{json .}}"]
        inspect_result = await run_docker_command('', inspect_cmd, format_json=True)
        
        if not inspect_result or not isinstance(inspect_result, list) or not inspect_result[0]:
            error_msg = f"Network '{network_id}' not found"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        network_info = inspect_result[0]
        network_name = network_info.get('Name', network_id)
        network_id = network_info.get('Id', network_id)
        
        # Build the remove command
        cmd = ["network", "rm"]
        
        if force:
            cmd.append("--force")
        
        cmd.append(network_id)
        
        # Execute the command with timeout
        result = await run_docker_command('', cmd, format_json=False, timeout=timeout)
        
        if result.returncode != 0:
            error_msg = result.stderr or f"Failed to remove network '{network_id}'"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        logger.info("Successfully removed network '%s' (ID: %s)", 
                   network_name, network_id)
        
        return {
            'id': network_id,
            'name': network_name,
            'success': True,
            'message': f"Successfully removed network '{network_name}'",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except asyncio.TimeoutError:
        error_msg = f"Timeout ({timeout}s) while removing network '{network_id}'"
        logger.error(error_msg)
        raise ContainerError(error_msg)
    except ContainerError:
        raise  # Re-raise ContainerError as is
    except Exception as e:
        error_msg = f"Unexpected error removing network '{network_id}': {str(e)}"
        logger.exception(error_msg)
        raise ContainerError(error_msg) from e

@tool(
    name="connect_container_to_network",
    description="Connect a container to a Docker network with advanced configuration options",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'Container ID or name to connect to the network',
                'minLength': 1,
                'maxLength': 64,
                'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
            },
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name to connect the container to',
                'minLength': 1,
                'maxLength': 64,
                'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
            },
            'ipv4_address': {
                'type': 'string',
                'description': 'IPv4 address for the container on this network',
                'format': 'ipv4',
                'default': None
            },
            'ipv6_address': {
                'type': 'string',
                'description': 'IPv6 address for the container on this network',
                'format': 'ipv6',
                'default': None
            },
            'aliases': {
                'type': 'array',
                'description': 'List of network-scoped aliases for the container',
                'items': {
                    'type': 'string',
                    'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$',
                    'maxLength': 64
                },
                'default': []
            },
            'links': {
                'type': 'array',
                'description': 'List of container names to link to in the form container_name:alias',
                'items': {
                    'type': 'string',
                    'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]*(:[a-zA-Z0-9][a-zA-Z0-9_.-]*)?$',
                    'maxLength': 128
                },
                'default': []
            },
            'link_local_ips': {
                'type': 'array',
                'description': 'List of link-local IP addresses',
                'items': {
                    'type': 'string',
                    'format': 'ip',
                    'pattern': r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|^[0-9a-fA-F:]+$'
                },
                'default': []
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds for the operation',
                'minimum': 1,
                'maximum': 300,
                'default': 30
            }
        },
        'required': ['container_id', 'network_id'],
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'ConnectContainerToNetworkResult',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'The ID of the container that was connected',
                'minLength': 64,
                'maxLength': 64
            },
            'container_name': {
                'type': 'string',
                'description': 'The name of the container that was connected'
            },
            'network_id': {
                'type': 'string',
                'description': 'The ID of the network the container was connected to',
                'minLength': 64,
                'maxLength': 64
            },
            'network_name': {
                'type': 'string',
                'description': 'The name of the network the container was connected to'
            },
            'success': {
                'type': 'boolean',
                'description': 'Whether the connection was successful'
            },
            'message': {
                'type': 'string',
                'description': 'Status message about the connection operation'
            },
            'endpoint_config': {
                'type': 'object',
                'description': 'Endpoint configuration details',
                'properties': {
                    'ipv4_address': {
                        'type': 'string',
                        'format': 'ipv4',
                        'description': 'IPv4 address assigned to the container on this network'
                    },
                    'ipv6_address': {
                        'type': 'string',
                        'format': 'ipv6',
                        'description': 'IPv6 address assigned to the container on this network'
                    },
                    'aliases': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Network-scoped aliases for the container'
                    },
                    'links': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Container links in the form container_name:alias'
                    },
                    'link_local_ips': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'ip'},
                        'description': 'Link-local IP addresses assigned to the container'
                    },
                    'mac_address': {
                        'type': 'string',
                        'format': 'mac-address',
                        'description': 'MAC address assigned to the container on this network'
                    },
                    'endpoint_id': {
                        'type': 'string',
                        'description': 'ID of the network endpoint'
                    }
                }
            },
            'network_info': {
                'type': 'object',
                'description': 'Information about the connected network',
                'properties': {
                    'driver': {'type': 'string'},
                    'scope': {'type': 'string'},
                    'ipam': {'type': 'object'},
                    'options': {'type': 'object'},
                    'internal': {'type': 'boolean'},
                    'enable_ipv6': {'type': 'boolean'},
                    'attachable': {'type': 'boolean'},
                    'ingress': {'type': 'boolean'}
                }
            },
            'timestamp': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the connection was made'
            },
            'warnings': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Any warnings that occurred during the connection'
            }
        },
        'required': [
            'container_id', 'network_id', 'network_name', 'success', 'message',
            'endpoint_config', 'timestamp'
        ]
    }
)
async def connect_container_to_network(
    container_id: str,
    network_id: str,
    ipv4_address: Optional[str] = None,
    ipv6_address: Optional[str] = None,
    aliases: Optional[List[str]] = None,
    links: Optional[List[str]] = None,
    link_local_ips: Optional[List[str]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Connect a container to a Docker network with advanced configuration options.

    This function connects a container to a Docker network with various networking
    options including IP addressing, aliases, and container links.

    Args:
        container_id: Container ID or name to connect to the network
        network_id: Network ID or name to connect the container to
        ipv4_address: IPv4 address for the container on this network
        ipv6_address: IPv6 address for the container on this network
        aliases: List of network-scoped aliases for the container
        links: List of container names to link to in the form container_name:alias
        link_local_ips: List of link-local IP addresses
        timeout: Timeout in seconds for the operation (default: 30)

    Returns:
        Dictionary containing the connection details and status

    Raises:
        ContainerError: If the connection fails or if the container/network is not found
    """
    start_time = time.time()
    logger.info(
        "Connecting container '%s' to network '%s' with options: ipv4=%s, ipv6=%s, aliases=%s, links=%s, link_local_ips=%s",
        container_id,
        network_id,
        ipv4_address,
        ipv6_address,
        aliases,
        links,
        link_local_ips
    )
    
    try:
        # Initialize default values
        aliases = aliases or []
        links = links or []
        link_local_ips = link_local_ips or []
        
        # Validate inputs
        if not container_id or not container_id.strip():
            raise ValueError("Container ID cannot be empty")
        if not network_id or not network_id.strip():
            raise ValueError("Network ID cannot be empty")
        
        # Validate container exists
        container_cmd = ["container", "inspect", "--format", "{{.Id}}", container_id]
        container_result = await run_docker_command('', container_cmd, format_json=False)
        
        if container_result.returncode != 0:
            error_msg = f"Container '{container_id}' not found"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        # Validate network exists and get its ID
        network_cmd = ["network", "inspect", "--format", "{{.Id}}", network_id]
        network_result = await run_docker_command('', network_cmd, format_json=False)
        
        if network_result.returncode != 0:
            error_msg = f"Network '{network_id}' not found"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        # Build the docker command
        cmd = ["network", "connect"]
        
        # Add IP address configuration
        if ipv4_address:
            cmd.extend(["--ip", ipv4_address])
        if ipv6_address:
            cmd.extend(["--ip6", ipv6_address])
        
        # Add network aliases
        for alias in aliases:
            if alias:  # Skip empty aliases
                cmd.extend(["--alias", alias])
        
        # Add container links
        for link in links:
            if link:  # Skip empty links
                cmd.extend(["--link", link])
        
        # Add link-local IPs
        for ip in link_local_ips:
            if ip:  # Skip empty IPs
                cmd.extend(["--link-local-ip", ip])
        
        # Add network and container IDs
        cmd.extend([network_id, container_id])
        
        logger.debug("Executing Docker command: %s", " ".join(cmd))
        
        # Execute the command with timeout
        result = await run_docker_command('', cmd, format_json=False, timeout=timeout)
        
        if result.returncode != 0:
            error_msg = result.stderr or f"Failed to connect container '{container_id}' to network '{network_id}'"
            logger.error("Command failed with code %d: %s", result.returncode, error_msg)
            raise ContainerError(error_msg)
        
        # Get network details for the response
        logger.debug("Fetching network details for: %s", network_id)
        inspect_cmd = ["network", "inspect", network_id, "--format", "{{json .}}"]
        inspect_result = await run_docker_command('', inspect_cmd, format_json=True, timeout=timeout)
        
        if not inspect_result or not isinstance(inspect_result, list) or not inspect_result[0]:
            error_msg = f"Network '{network_id}' not found after connection"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        network_info = inspect_result[0]
        network_name = network_info.get('Name', network_id)
        
        # Build endpoint configuration for response
        endpoint_config = {
            'IPAMConfig': {},
            'Links': links,
            'Aliases': aliases
        }
        
        if ipv4_address:
            endpoint_config['IPAMConfig']['IPv4Address'] = ipv4_address
        if ipv6_address:
            endpoint_config['IPAMConfig']['IPv6Address'] = ipv6_address
        if link_local_ips:
            endpoint_config['IPAMConfig']['LinkLocalIPs'] = link_local_ips
        
        response = {
            'container_id': container_id,
            'network_id': network_info.get('Id', network_id),
            'network_name': network_name,
            'success': True,
            'message': f"Successfully connected container '{container_id}' to network '{network_name}'",
            'endpoint_config': endpoint_config,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            "Successfully connected container '%s' to network '%s' in %.2f seconds",
            container_id,
            network_name,
            time.time() - start_time
        )
        
        return response
        
    except asyncio.TimeoutError as e:
        error_msg = f"Timeout after {timeout} seconds while connecting container '{container_id}' to network '{network_id}'"
        logger.error(error_msg)
        raise ContainerError(error_msg) from e

@tool(
    name="disconnect_container_from_network",
    description="Disconnect a container from a Docker network with optional force flag",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'Container ID or name to disconnect from the network',
                'minLength': 1,
                'maxLength': 64,
                'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
            },
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name to disconnect the container from',
                'minLength': 1,
                'maxLength': 64,
                'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
            },
            'force': {
                'type': 'boolean',
                'description': 'Force the container to disconnect from the network',
                'default': False
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds for the operation',
                'minimum': 1,
                'maximum': 300,
                'default': 30
            }
        },
        'required': ['container_id', 'network_id'],
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'DisconnectContainerFromNetworkResult',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'The ID of the container that was disconnected',
                'minLength': 64,
                'maxLength': 64
            },
            'container_name': {
                'type': 'string',
                'description': 'The name of the container that was disconnected'
            },
            'network_id': {
                'type': 'string',
                'description': 'The ID of the network the container was disconnected from',
                'minLength': 64,
                'maxLength': 64
            },
            'network_name': {
                'type': 'string',
                'description': 'The name of the network the container was disconnected from'
            },
            'success': {
                'type': 'boolean',
                'description': 'Whether the disconnection was successful'
            },
            'message': {
                'type': 'string',
                'description': 'Status message about the disconnection operation'
            },
            'force_disconnected': {
                'type': 'boolean',
                'description': 'Whether the disconnection was forced',
                'default': False
            },
            'endpoint_removed': {
                'type': 'boolean',
                'description': 'Whether the network endpoint was removed',
                'default': True
            },
            'ip_addresses_released': {
                'type': 'array',
                'items': {'type': 'string', 'format': 'ip'},
                'description': 'List of IP addresses that were released'
            },
            'network_info': {
                'type': 'object',
                'description': 'Information about the network post-disconnection',
                'properties': {
                    'driver': {'type': 'string'},
                    'scope': {'type': 'string'},
                    'containers_remaining': {
                        'type': 'integer',
                        'description': 'Number of containers still connected to the network',
                        'minimum': 0
                    },
                    'ipam': {'type': 'object'},
                    'options': {'type': 'object'}
                }
            },
            'timestamp': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the disconnection occurred'
            },
            'warnings': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Any warnings that occurred during the disconnection'
            }
        },
        'required': [
            'container_id', 'network_id', 'network_name', 'success', 'message',
            'force_disconnected', 'endpoint_removed', 'timestamp'
        ]
    }
)
async def disconnect_container_from_network(
    container_id: str,
    network_id: str,
    force: bool = False,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Disconnect a container from a Docker network with optional force flag.

    This function disconnects a container from a Docker network. The operation can be forced
    if the container is running and the network is required for its operation.

    Args:
        container_id: Container ID or name to disconnect from the network
        network_id: Network ID or name to disconnect the container from
        force: Force the container to disconnect from the network
        timeout: Timeout in seconds for the operation (default: 30)

    Returns:
        Dictionary containing the disconnection status and details:
        - container_id: The ID of the container
        - network_id: The ID of the network
        - network_name: The name of the network
        - success: Boolean indicating if the operation was successful
        - message: Status message
        - timestamp: ISO 8601 timestamp of when the operation completed

    Raises:
        ContainerError: If disconnection fails or if the container/network is not found
    """
    start_time = time.time()
    logger.info(
        "Disconnecting container '%s' from network '%s' (force: %s, timeout: %ds)",
        container_id,
        network_id,
        force,
        timeout
    )
    
    try:
        # Validate inputs
        if not container_id or not container_id.strip():
            error_msg = "Container ID cannot be empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not network_id or not network_id.strip():
            error_msg = "Network ID cannot be empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Verify the network exists and get its details
        logger.debug("Fetching network details for: %s", network_id)
        inspect_cmd = ["network", "inspect", network_id, "--format", "{{json .}}"]
        inspect_result = await run_docker_command('', inspect_cmd, format_json=True, timeout=timeout)
        
        if not inspect_result or not isinstance(inspect_result, list) or not inspect_result[0]:
            error_msg = f"Network '{network_id}' not found"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        network_info = inspect_result[0]
        network_name = network_info.get('Name', network_id)
        network_id = network_info.get('Id', network_id)  # Use the actual ID from Docker
        
        # Build the docker command
        cmd = ["network", "disconnect"]
        
        if force:
            cmd.append("--force")
        
        cmd.extend([network_id, container_id])
        
        logger.debug("Executing Docker command: %s", " ".join(cmd))
        
        # Execute the command with timeout
        result = await run_docker_command('', cmd, format_json=False, timeout=timeout)
        
        if result.returncode != 0:
            error_msg = result.stderr or f"Failed to disconnect container '{container_id}' from network '{network_name}'"
            logger.error("Command failed with code %d: %s", result.returncode, error_msg)
            raise ContainerError(error_msg)
        
        response = {
            'container_id': container_id,
            'network_id': network_id,
            'network_name': network_name,
            'success': True,
            'message': f"Successfully disconnected container '{container_id}' from network '{network_name}'",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            "Successfully disconnected container '%s' from network '%s' in %.2f seconds",
            container_id,
            network_name,
            time.time() - start_time
        )
        
        return response
        
    except asyncio.TimeoutError as e:
        error_msg = f"Timeout after {timeout} seconds while disconnecting container '{container_id}' from network '{network_id}'"
        logger.error(error_msg)
        raise ContainerError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse network information: {str(e)}"
        logger.exception(error_msg)
        raise ContainerError(error_msg) from e
    except ContainerError as e:
        raise ContainerError(f"Failed to disconnect container '{container_id}' from network '{network_id}': {str(e)}") from e
    except Exception as e:
        error_msg = f"Unexpected error disconnecting container '{container_id}' from network '{network_id}': {str(e)}"
        logger.exception(error_msg)
        raise ContainerError(error_msg) from e


@tool(
    name="get_network_stats",
    description="Retrieve detailed statistics and information for a Docker network",
    parameters={
        'type': 'object',
        'properties': {
            'network_id': {
                'type': 'string',
                'description': 'Network ID or name to get statistics for',
                'minLength': 1,
                'maxLength': 64,
                'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
            },
            'verbose': {
                'type': 'boolean',
                'description': 'Include detailed statistics for each container (may increase response time)',
                'default': False
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds for the operation',
                'minimum': 1,
                'maximum': 300,
                'default': 30
            }
        },
        'required': ['network_id'],
        'additionalProperties': False
    },
    output_schema={
        'type': 'object',
        'title': 'NetworkStatsResult',
        'properties': {
            'network_id': {
                'type': 'string',
                'description': 'The ID of the network',
                'minLength': 64,
                'maxLength': 64
            },
            'network_name': {
                'type': 'string',
                'description': 'The name of the network',
                'minLength': 2,
                'maxLength': 255
            },
            'driver': {
                'type': 'string',
                'description': 'The network driver in use',
                'enum': ['bridge', 'overlay', 'host', 'macvlan', 'none']
            },
            'scope': {
                'type': 'string',
                'description': 'The scope of the network',
                'enum': ['local', 'swarm']
            },
            'created': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the network was created'
            },
            'ipam': {
                'type': 'object',
                'description': 'IP Address Management configuration',
                'properties': {
                    'driver': {
                        'type': 'string',
                        'description': 'IPAM driver in use',
                        'default': 'default'
                    },
                    'options': {
                        'type': 'object',
                        'description': 'Driver-specific options',
                        'additionalProperties': {'type': 'string'}
                    },
                    'config': {
                        'type': 'array',
                        'description': 'List of IPAM configuration blocks',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'subnet': {
                                    'type': 'string',
                                    'format': 'ipv4-cidr',
                                    'description': 'Subnet in CIDR format (e.g., 172.18.0.0/16)'
                                },
                                'gateway': {
                                    'type': 'string',
                                    'format': 'ipv4',
                                    'description': 'Default gateway for the subnet'
                                },
                                'ip_range': {
                                    'type': 'string',
                                    'format': 'ipv4-cidr',
                                    'description': 'Range of IPs from which to allocate container IPs'
                                },
                                'auxiliary_addresses': {
                                    'type': 'object',
                                    'description': 'Auxiliary IPv4 or IPv6 addresses used by the network driver',
                                    'additionalProperties': {'type': 'string'}
                                }
                            }
                        }
                    }
                }
            },
            'internal': {
                'type': 'boolean',
                'description': 'Whether the network is internal (no external access)'
            },
            'enable_ipv6': {
                'type': 'boolean',
                'description': 'Whether IPv6 is enabled on the network'
            },
            'attachable': {
                'type': 'boolean',
                'description': 'Whether manual container attachment is enabled'
            },
            'ingress': {
                'type': 'boolean',
                'description': 'Whether the network is an ingress network for swarm mode'
            },
            'options': {
                'type': 'object',
                'description': 'Driver-specific options',
                'additionalProperties': {'type': ['string', 'number', 'boolean']}
            },
            'labels': {
                'type': 'object',
                'description': 'Labels set on the network',
                'additionalProperties': {'type': 'string'}
            },
            'containers': {
                'type': 'array',
                'description': 'List of containers connected to the network',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {
                            'type': 'string',
                            'description': 'ID of the container',
                            'minLength': 64,
                            'maxLength': 64
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Name of the container'
                        },
                        'endpoint_id': {
                            'type': 'string',
                            'description': 'ID of the network endpoint',
                            'minLength': 64,
                            'maxLength': 64
                        },
                        'mac_address': {
                            'type': 'string',
                            'format': 'mac-address',
                            'description': 'MAC address of the container on this network'
                        },
                        'ipv4_address': {
                            'type': 'string',
                            'format': 'ipv4',
                            'description': 'IPv4 address of the container on this network'
                        },
                        'ipv6_address': {
                            'type': 'string',
                            'format': 'ipv6',
                            'description': 'IPv6 address of the container on this network'
                        },
                        'ip_prefix_length': {
                            'type': 'integer',
                            'description': 'IPv4 network prefix length',
                            'minimum': 0,
                            'maximum': 32
                        },
                        'ipv6_prefix_length': {
                            'type': 'integer',
                            'description': 'IPv6 network prefix length',
                            'minimum': 0,
                            'maximum': 128
                        },
                        'aliases': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Network-scoped aliases for the container'
                        },
                        'stats': {
                            'type': 'object',
                            'description': 'Network statistics for the container',
                            'properties': {
                                'rx_bytes': {
                                    'type': 'integer',
                                    'description': 'Total bytes received',
                                    'minimum': 0
                                },
                                'rx_packets': {
                                    'type': 'integer',
                                    'description': 'Total packets received',
                                    'minimum': 0
                                },
                                'rx_errors': {
                                    'type': 'integer',
                                    'description': 'Total receive errors',
                                    'minimum': 0
                                },
                                'rx_dropped': {
                                    'type': 'integer',
                                    'description': 'Total receive packets dropped',
                                    'minimum': 0
                                },
                                'tx_bytes': {
                                    'type': 'integer',
                                    'description': 'Total bytes transmitted',
                                    'minimum': 0
                                },
                                'tx_packets': {
                                    'type': 'integer',
                                    'description': 'Total packets transmitted',
                                    'minimum': 0
                                },
                                'tx_errors': {
                                    'type': 'integer',
                                    'description': 'Total transmit errors',
                                    'minimum': 0
                                },
                                'tx_dropped': {
                                    'type': 'integer',
                                    'description': 'Total transmit packets dropped',
                                    'minimum': 0
                                }
                            }
                        },
                        'stats_error': {
                            'type': 'string',
                            'description': 'Error message if statistics could not be collected'
                        },
                        'state': {
                            'type': 'string',
                            'enum': ['created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead'],
                            'description': 'Current state of the container'
                        }
                    },
                    'required': ['id', 'name', 'endpoint_id', 'mac_address']
                }
            },
            'total_stats': {
                'type': 'object',
                'description': 'Aggregated statistics across all containers on the network',
                'properties': {
                    'rx_bytes': {
                        'type': 'integer',
                        'description': 'Total bytes received by all containers',
                        'minimum': 0
                    },
                    'rx_packets': {
                        'type': 'integer',
                        'description': 'Total packets received by all containers',
                        'minimum': 0
                    },
                    'rx_errors': {
                        'type': 'integer',
                        'description': 'Total receive errors across all containers',
                        'minimum': 0
                    },
                    'rx_dropped': {
                        'type': 'integer',
                        'description': 'Total receive packets dropped across all containers',
                        'minimum': 0
                    },
                    'tx_bytes': {
                        'type': 'integer',
                        'description': 'Total bytes transmitted by all containers',
                        'minimum': 0
                    },
                    'tx_packets': {
                        'type': 'integer',
                        'description': 'Total packets transmitted by all containers',
                        'minimum': 0
                    },
                    'tx_errors': {
                        'type': 'integer',
                        'description': 'Total transmit errors across all containers',
                        'minimum': 0
                    },
                    'tx_dropped': {
                        'type': 'integer',
                        'description': 'Total transmit packets dropped across all containers',
                        'minimum': 0
                    },
                    'containers_count': {
                        'type': 'integer',
                        'description': 'Total number of containers connected to the network',
                        'minimum': 0
                    },
                    'containers_with_stats': {
                        'type': 'integer',
                        'description': 'Number of containers with successfully collected statistics',
                        'minimum': 0
                    },
                    'containers_with_errors': {
                        'type': 'integer',
                        'description': 'Number of containers with statistics collection errors',
                        'minimum': 0
                    }
                },
                'required': [
                    'rx_bytes', 'rx_packets', 'rx_errors', 'rx_dropped',
                    'tx_bytes', 'tx_packets', 'tx_errors', 'tx_dropped',
                    'containers_count'
                ]
            },
            'success': {
                'type': 'boolean',
                'description': 'Whether the statistics were successfully collected'
            },
            'message': {
                'type': 'string',
                'description': 'Status message about the operation'
            },
            'timestamp': {
                'type': 'string',
                'format': 'date-time',
                'description': 'ISO 8601 timestamp of when the statistics were collected'
            },
            'collection_time_ms': {
                'type': 'integer',
                'description': 'Time taken to collect all statistics in milliseconds',
                'minimum': 0
            },
            'warnings': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Any warnings that occurred during statistics collection'
            }
        },
        'required': [
            'network_id', 'network_name', 'driver', 'scope', 'created', 'ipam',
            'internal', 'enable_ipv6', 'attachable', 'ingress', 'options', 'labels',
            'containers', 'total_stats', 'success', 'message', 'timestamp'
        ]
    }
)
async def get_network_stats(
    network_id: str,
    verbose: bool = False,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Retrieve detailed statistics and information for a Docker network.

    This function provides comprehensive information about a Docker network, including:
    - Network configuration and settings
    - IPAM (IP Address Management) configuration
    - List of connected containers with their network details
    - Network statistics (when verbose=True)
    - Aggregated statistics across all containers

    Args:
        network_id: Network ID or name to get statistics for
        verbose: If True, includes detailed statistics for each container (may increase response time)
        timeout: Timeout in seconds for the operation (1-300)

    Returns:
        Dictionary containing detailed network information and statistics:
        - network_id: The ID of the network
        - network_name: The name of the network
        - driver: The network driver used
        - ipam: IP Address Management configuration
        - containers: List of containers connected to the network
        - total_stats: Aggregated network statistics
        - success: Boolean indicating if the operation was successful
        - message: Status message
        - timestamp: ISO 8601 timestamp of when the operation completed

    Raises:
        ContainerError: If the operation fails, the network is not found, or the request times out
        ValueError: If input validation fails
        asyncio.TimeoutError: If the operation times out
    """
    start_time = time.time()
    logger.info(
        "Retrieving statistics for network '%s' (verbose: %s, timeout: %ds)",
        network_id, verbose, timeout
    )
    
    try:
        # Input validation with detailed error messages
        if not network_id or not network_id.strip():
            error_msg = "Network ID cannot be empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not isinstance(verbose, bool):
            error_msg = f"verbose must be a boolean, got {type(verbose).__name__}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not isinstance(timeout, int) or timeout < 1 or timeout > 300:
            error_msg = f"timeout must be an integer between 1 and 300, got {timeout}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Log the start of the operation with context
        logger.debug(
            "Starting network stats collection for network '%s' (timeout: %ds)",
            network_id, timeout
        )
        
        # Get network details with timeout and proper error handling
        inspect_cmd = ["network", "inspect", network_id, "--format", "{{json .}}"]
        logger.debug("Executing Docker command: %s", " ".join(inspect_cmd))
        
        try:
            # Calculate remaining time for the operation
            elapsed = time.time() - start_time
            remaining_timeout = max(1, timeout - int(elapsed))
            
            inspect_result = await run_docker_command(
                '', 
                inspect_cmd, 
                format_json=True, 
                timeout=remaining_timeout
            )
            
            logger.debug("Successfully retrieved network inspection data")
            
        except asyncio.TimeoutError as e:
            error_msg = f"Timeout after {timeout}s while inspecting network '{network_id}'"
            logger.error(error_msg)
            raise ContainerError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse network information: {str(e)}"
            logger.exception(error_msg)
            raise ContainerError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to inspect network '{network_id}': {str(e)}"
            logger.exception(
                "Unexpected error during network inspection",
                exc_info=True,
                extra={
                    'network_id': network_id,
                    'timeout': timeout,
                    'elapsed_seconds': time.time() - start_time
                }
            )
            raise ContainerError(error_msg) from e
        
        if not inspect_result or not isinstance(inspect_result, list) or not inspect_result[0]:
            error_msg = f"Network '{network_id}' not found or not accessible"
            logger.error(error_msg)
            raise ContainerError(error_msg)
        
        network_info = inspect_result[0]
        network_name = network_info.get('Name', network_id)
        network_id = network_info.get('Id', network_id)  # Use the actual ID from Docker
        
        # Prepare the base response
        response = {
            'network_id': network_id,
            'network_name': network_name,
            'driver': network_info.get('Driver', ''),
            'scope': network_info.get('Scope', ''),
            'created': network_info.get('Created', ''),
            'internal': network_info.get('Internal', False),
            'enable_ipv6': network_info.get('EnableIPv6', False),
            'attachable': network_info.get('Attachable', False),
            'ingress': network_info.get('Ingress', False),
            'options': network_info.get('Options', {}),
            'labels': network_info.get('Labels', {}),
            'ipam': {
                'driver': network_info.get('IPAM', {}).get('Driver', 'default'),
                'options': network_info.get('IPAM', {}).get('Options', {}),
                'config': []
            },
            'containers': [],
            'total_stats': {
                'rx_bytes': 0,
                'rx_packets': 0,
                'rx_errors': 0,
                'rx_dropped': 0,
                'tx_bytes': 0,
                'tx_packets': 0,
                'tx_errors': 0,
                'tx_dropped': 0,
                'containers_count': 0
            },
            'success': True,
            'message': f"Successfully retrieved statistics for network '{network_name}'",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Process IPAM config with validation
        try:
            if 'IPAM' in network_info and 'Config' in network_info['IPAM']:
                for config in network_info['IPAM']['Config'] or []:
                    ipam_config = {}
                    if 'Subnet' in config and config['Subnet']:
                        ipam_config['subnet'] = config['Subnet']
                    if 'Gateway' in config and config['Gateway']:
                        ipam_config['gateway'] = config['Gateway']
                    if 'IPRange' in config and config['IPRange']:
                        ipam_config['ip_range'] = config['IPRange']
                    if 'AuxiliaryAddresses' in config and config['AuxiliaryAddresses']:
                        ipam_config['auxiliary_addresses'] = config['AuxiliaryAddresses']
                    
                    # Only add non-empty configs
                    if ipam_config:
                        response['ipam']['config'].append(ipam_config)
                        
                logger.debug("Processed IPAM configuration with %d config entries", 
                           len(response['ipam']['config']))
        except Exception as e:
            logger.warning("Error processing IPAM configuration: %s", str(e), exc_info=True)
            # Continue with empty IPAM config if there's an error
        
        # Skip container stats if not in verbose mode
        if not verbose:
            logger.debug("Verbose mode disabled, returning basic network info")
            return response
            
        # Get container stats for the network with error handling
        try:
            containers = network_info.get('Containers', {}) or {}
            if not containers:
                logger.info("No containers found in network '%s'", network_name)
                response['message'] = f"No containers found in network '{network_name}'"
                return response
                
            logger.debug("Found %d containers in network '%s'", len(containers), network_name)
            
        except Exception as e:
            logger.error(
                "Error retrieving container information: %s", 
                str(e),
                exc_info=True
            )
            # Continue with empty container list if there's an error
            containers = {}
            response['message'] = f"Warning: Error retrieving container information: {str(e)}"
        
        # Track container count for response
        container_count = len(containers)
        response['total_stats']['containers_count'] = container_count
        logger.debug("Found %d containers in network '%s'", container_count, network_name)
        
        # Process each container in the network with error handling and timeouts
        processed_containers = 0
        for container_id, container_info in containers.items():
            try:
                # Check if we're running out of time
                elapsed = time.time() - start_time
                if elapsed > (timeout * 0.8):  # Use 80% of timeout for processing
                    logger.warning(
                        "Approaching timeout, skipping remaining containers. "
                        "Elapsed: %.2fs, Timeout: %ds", 
                        elapsed, timeout
                    )
                    response['message'] = (
                        f"Warning: Partial results - processing stopped due to timeout. "
                        f"Processed {processed_containers} of {len(containers)} containers."
                    )
                    break
                
                container_name = container_info.get('Name', container_id[:12])
                logger.debug("Processing container: %s (%s)", container_name, container_id)
                
                # Safely extract container network info with defaults
                ipv4 = container_info.get('IPv4Address', '').split('/')
                ipv6 = container_info.get('IPv6Address', '').split('/')
                
                container_network = {
                    'id': container_id,
                    'name': container_name,
                    'endpoint_id': container_info.get('EndpointID', ''),
                    'mac_address': container_info.get('MacAddress', ''),
                    'ipv4_address': ipv4[0] if ipv4 and ipv4[0] else '',
                    'ipv6_address': ipv6[0] if ipv6 and ipv6[0] else '',
                    'ip_prefix_length': int(ipv4[1]) if len(ipv4) > 1 and ipv4[1].isdigit() else 0,
                    'ipv6_prefix_length': int(ipv6[1]) if len(ipv6) > 1 and ipv6[1].isdigit() else 0
                }
                
                # Get container stats if verbose mode is enabled
                if verbose:
                    try:
                        # Calculate remaining time for this operation
                        elapsed = time.time() - start_time
                        remaining_timeout = max(1, int((timeout * 0.8) - elapsed))  # Use 80% of remaining time
                        
                        stats_cmd = [
                            "container", "stats", "--no-stream", "--no-trunc",
                            "--format", "{{json .}}", container_id
                        ]
                        logger.debug("Fetching stats for container %s (timeout: %ds)", 
                                   container_id, remaining_timeout)
                        
                        stats_result = await run_docker_command(
                            '', 
                            stats_cmd, 
                            format_json=True, 
                            timeout=remaining_timeout
                        )
                        
                        if stats_result and isinstance(stats_result, dict):
                            # Extract network stats from the container stats with validation
                            net_stats = {}
                            stat_keys = [
                                'rx_bytes', 'rx_packets', 'rx_errors', 'rx_dropped',
                                'tx_bytes', 'tx_packets', 'tx_errors', 'tx_dropped'
                            ]
                            
                            for stat_key in stat_keys:
                                try:
                                    value = stats_result.get(stat_key, '0')
                                    # Handle cases where the value might be a string with non-numeric characters
                                    if isinstance(value, str):
                                        # Extract numbers from strings like "1.23kB" -> 1230
                                        import re
                                        num_match = re.search(r'[0-9.]+', value)
                                        if num_match:
                                            # Convert to float first to handle decimal points, then to int
                                            net_stats[stat_key] = int(float(num_match.group(0)))
                                        else:
                                            net_stats[stat_key] = 0
                                    else:
                                        net_stats[stat_key] = int(value)
                                        
                                    # Ensure the value is non-negative
                                    net_stats[stat_key] = max(0, net_stats[stat_key])
                                    
                                except (ValueError, TypeError) as e:
                                    logger.warning(
                                        "Invalid stat value for %s: %s", 
                                        stat_key, str(e)
                                    )
                                    net_stats[stat_key] = 0
                            
                            # Add to total stats with thread-safety in mind
                            for key, value in net_stats.items():
                                if key in response['total_stats']:
                                    response['total_stats'][key] += value
                            
                            container_network['stats'] = net_stats
                            
                    except asyncio.TimeoutError as e:
                        logger.warning("Timeout getting stats for container %s: %s", 
                                     container_id, str(e))
                        container_network['stats_error'] = 'timeout'
                    except json.JSONDecodeError as e:
                        logger.warning("Failed to parse stats for container %s: %s", 
                                     container_id, str(e))
                        container_network['stats_error'] = 'invalid_format'
                    except Exception as e:
                        logger.warning(
                            "Error getting stats for container %s: %s", 
                            container_id, 
                            str(e),
                            exc_info=True
                        )
                        container_network['stats_error'] = 'unexpected_error'
                
                # Add container to response and increment counter
                response['containers'].append(container_network)
                processed_containers += 1
                
            except Exception as e:
                logger.warning("Error processing container %s: %s", container_id, str(e), exc_info=True)
                continue
        
        # Log completion
        elapsed = time.time() - start_time
        logger.info(
            "Successfully retrieved stats for network '%s' with %d containers in %.2f seconds",
            network_name, len(response['containers']), elapsed
        )
        
        return response
        
    except asyncio.TimeoutError as e:
        error_msg = f"Operation timed out after {timeout} seconds"
        logger.error(
            error_msg,
            extra={
                'network_id': network_id,
                'timeout': timeout,
                'elapsed_seconds': time.time() - start_time
            }
        )
        raise ContainerError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse network information: {str(e)}"
        logger.exception(
            error_msg,
            extra={
                'network_id': network_id,
                'exception_type': type(e).__name__
            }
        )
        raise ContainerError(error_msg) from e
    except ContainerError:
        # Re-raise ContainerError as is, but log it first
        logger.error(
            "ContainerError during network stats retrieval",
            exc_info=True,
            extra={
                'network_id': network_id,
                'elapsed_seconds': time.time() - start_time
            }
        )
        raise
    except Exception as e:
        error_msg = f"Unexpected error getting network stats: {str(e)}"
        logger.exception(
            error_msg,
            extra={
                'network_id': network_id,
                'exception_type': type(e).__name__,
                'elapsed_seconds': time.time() - start_time
            }
        )
        raise ContainerError(error_msg) from e
