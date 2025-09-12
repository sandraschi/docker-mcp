"""
Container Tools for Docker MCP

This module provides a unified interface to container management functionality
using FastMCP 2.12+ tool pattern.

For advanced use cases, you can import directly from the specialized modules:
- `container_lifecycle.py`: Container lifecycle operations
- `container_logs.py`: Container log management
- `container_exec.py`: Command execution in containers
- `container_inspect.py`: Container inspection and monitoring
- `container_models.py`: Shared data models and request/response types
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, TypeVar, Union, cast

# Configure logging
from dockermcp.logging_config import logger, configure_logging
from dockermcp import check_docker_available, docker_available, docker_error
from ..error_handling import handle_docker_errors, format_daemon_not_running

# Import FastMCP components
from fastmcp.tools import tool

# Import custom exceptions
from .container_models import ContainerError

# Import container models and types
from .container_models import *
from .container_logs import LogStreamType, ContainerLogsRequest

# Import tool implementations
from .container_lifecycle import *
from .container_logs import *
from .container_exec import *
from .container_inspect import *

# Configure logging
configure_logging()

# Import all container models and types for re-export
from .container_models import *

# Import tool implementations from specialized modules with clear aliases
# This makes it clear which functions are being re-exported
from . import container_lifecycle
from .container_lifecycle import (
    list_containers as _list_containers_impl,
    create_container as _create_container_impl,
    start_container as _start_container_impl,
    stop_container as _stop_container_impl,
    restart_container as _restart_container_impl,
    remove_container as _remove_container_impl,
    prune_containers as _prune_containers_impl,
    manage_container_lifecycle as _manage_container_lifecycle_impl,
)

from .container_logs import (
    get_container_logs as _get_container_logs,
    stream_container_logs as _stream_container_logs,
)

from .container_exec import (
    execute_in_container as _execute_in_container,
    exec_command as _exec_command,
)

from .container_inspect import (
    inspect_container as _inspect_container,
    container_stats as _container_stats,
    container_top as _container_top,
)

# Import container manager and utilities
from .container_utils import (
    create_response,
    handle_error,
    container_mgr,
    run_docker_command,
)

# Type variables for generics
T = TypeVar('T', bound=BaseModel)
ContainerT = TypeVar('ContainerT', bound=BaseModel)

from dockermcp.logging_config import logger

# Get a child logger for this module
logger = logger.getChild('container_tools')

# Type variables for request/response models
T = TypeVar('T', bound=BaseModel)

# Tool Registration Helpers
# -----------------------------------------------------------------------------

# Tool registration helpers
# -----------------------------------------------------------------------------

def create_container_tool():
    """Create a Tool instance for container operations with proper error handling."""
    return Tool(
        name="container_operations",
        description="Manage Docker containers with comprehensive error handling",
        func=handle_container_operation
    )

# Container Tools Metadata
# -----------------------------------------------------------------------------

# Container Lifecycle Tools
# -----------------------------------------------------------------------------

@tool(
    name="list_containers",
    description="List Docker containers with optional filtering",
    parameters={
        'type': 'object',
        'properties': {
            'all_states': {
                'type': 'boolean',
                'description': 'Include stopped containers',
                'default': True
            },
            'filters': {
                'type': 'object',
                'description': 'Filter containers by key-value pairs',
                'additionalProperties': {'type': 'string'},
                'default': {}
            }
        },
        'required': []
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'containers': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'name': {'type': 'string'},
                        'image': {'type': 'string'},
                        'status': {'type': 'string'},
                        'state': {'type': 'string'},
                        'created': {'type': 'string', 'format': 'date-time'},
                        'ports': {
                            'type': 'object',
                            'additionalProperties': {'type': 'string'}
                        },
                        'networks': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        }
                    },
                    'required': ['id', 'name', 'image', 'status', 'state', 'created']
                }
            },
            'error': {'type': 'string'}
        },
        'required': ['success', 'containers']
    }
)
@handle_docker_errors
@check_docker_available
async def list_containers(
    all_states: bool = True,
    filters: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    List Docker containers with optional filtering.
    
    Args:
        all_states: If True, include stopped containers
        filters: Dictionary of filter key-value pairs
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - containers: List of container information dictionaries
        - error: Error message if success is False
        
    Example:
        ```python
        # List all containers (including stopped ones)
        result = await list_containers(all_states=True)
        if result['success']:
            for container in result['containers']:
                logger.info(f"{container['name']} - {container['status']}")
        
        # List only running containers
        result = await list_containers(all_states=False)
        
        # Filter containers by label
        result = await list_containers(
            filters={"label": "environment=production"}
        )
        ```
    """
    try:
        request = ListContainersRequest(
            all_states=all_states,
            filters=filters or {}
        )
        containers = await _list_containers_impl(request)
        return {
            'success': True,
            'containers': containers,
            'error': None
        }
    except Exception as e:
        error_msg = f"Error listing containers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'containers': [],
            'error': error_msg
        }

@tool(
    name="create_container",
    description="Create a new container with the specified configuration",
    parameters={
        'type': 'object',
        'properties': {
            'image': {
                'type': 'string',
                'description': 'Docker image name and tag (e.g., nginx:latest)',
                'default': 'nginx:latest'
            },
            'name': {
                'type': 'string',
                'description': 'Name for the container',
                'default': ''
            },
            'command': {
                'type': ['string', 'array'],
                'description': 'Command to run in the container',
                'items': {'type': 'string'},
                'default': None
            },
            'ports': {
                'type': 'object',
                'description': 'Port mappings (e.g., {"80/tcp": 8080, "443/tcp": 8443})',
                'additionalProperties': {
                    'type': ['integer', 'string', 'null']
                },
                'default': {}
            },
            'environment': {
                'type': 'object',
                'description': 'Environment variables',
                'additionalProperties': {'type': 'string'},
                'default': {}
            },
            'volumes': {
                'type': 'object',
                'description': 'Volume bindings (e.g., {"/host/path": {"bind": "/container/path", "mode": "rw"}})',
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'bind': {'type': 'string'},
                        'mode': {'type': 'string'}
                    },
                    'required': ['bind']
                },
                'default': {}
            },
            'network': {
                'type': 'string',
                'description': 'Network to connect the container to',
                'default': 'bridge'
            },
            'restart_policy': {
                'type': 'string',
                'description': 'Restart policy (no, on-failure, unless-stopped, always)',
                'enum': ['no', 'on-failure', 'unless-stopped', 'always'],
                'default': 'no'
            },
            'auto_remove': {
                'type': 'boolean',
                'description': 'Automatically remove the container when it exits',
                'default': False
            },
            'detach': {
                'type': 'boolean',
                'description': 'Run container in the background',
                'default': True
            },
            'tty': {
                'type': 'boolean',
                'description': 'Allocate a pseudo-TTY',
                'default': False
            },
            'stdin_open': {
                'type': 'boolean',
                'description': 'Keep STDIN open even if not attached',
                'default': False
            },
            'mem_limit': {
                'type': 'string',
                'description': 'Memory limit (e.g., 1g, 512m)',
                'default': None
            },
            'cpu_shares': {
                'type': 'integer',
                'description': 'CPU shares (relative weight)',
                'default': None
            },
            'labels': {
                'type': 'object',
                'description': 'Container labels',
                'additionalProperties': {'type': 'string'},
                'default': {}
            }
        },
        'required': ['image']
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'container': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'status': {'type': 'string'},
                    'warnings': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                },
                'required': ['id', 'name', 'status']
            },
            'error': {'type': 'string'}
        },
        'required': ['success']
    }
)
@handle_docker_errors
@check_docker_available
async def create_container(
    image: str,
    name: str = '',
    command: Optional[Union[str, List[str]]] = None,
    ports: Optional[Dict[str, Union[int, str, None]]] = None,
    environment: Optional[Dict[str, str]] = None,
    volumes: Optional[Dict[str, Dict[str, str]]] = None,
    network: str = 'bridge',
    restart_policy: str = 'no',
    auto_remove: bool = False,
    detach: bool = True,
    tty: bool = False,
    stdin_open: bool = False,
    mem_limit: Optional[str] = None,
    cpu_shares: Optional[int] = None,
    labels: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a new container with the specified configuration.
    
    Args:
        image: Docker image name and tag (e.g., nginx:latest)
        name: Name for the container
        command: Command to run in the container
        ports: Port mappings (e.g., {"80/tcp": 8080})
        environment: Environment variables
        volumes: Volume bindings
        network: Network to connect to
        restart_policy: Restart policy (no, on-failure, unless-stopped, always)
        auto_remove: Automatically remove the container when it exits
        detach: Run container in the background
        tty: Allocate a pseudo-TTY
        stdin_open: Keep STDIN open even if not attached
        mem_limit: Memory limit (e.g., 1g, 512m)
        cpu_shares: CPU shares (relative weight)
        labels: Container labels
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - container: Dictionary with container details if successful
        - error: Error message if success is False
        
    Example:
        ```python
        # Create a simple nginx container
        result = await create_container(
            image="nginx:latest",
            name="my-nginx",
            ports={"80/tcp": 8080},
            detach=True
        )
        
        if result['success']:
            logger.info(f"Created container {result['container']['id']}")
        else:
            logger.error(f"Failed to create container: {result['error']}")
        ```
    """
    try:
        # Convert parameters to ContainerLifecycleRequest
        request = ContainerLifecycleRequest(
            image=image,
            name=name,
            command=command,
            ports=ports or {},
            environment=environment or {},
            volumes=volumes or {},
            network=network,
            restart_policy=restart_policy,
            auto_remove=auto_remove,
            detach=detach,
            tty=tty,
            stdin_open=stdin_open,
            mem_limit=mem_limit,
            cpu_shares=cpu_shares,
            labels=labels or {}
        )
        
        # Call the implementation
        container = await _create_container_impl(request)
        
        return {
            'success': True,
            'container': container,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Error creating container: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'container': None,
            'error': error_msg
        }

@tool(
    name="start_container",
    description="Start a stopped container with the specified configuration",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container to start',
                'default': ''
            },
            'detach': {
                'type': 'boolean',
                'description': 'Run container in the background',
                'default': True
            },
            'binds': {
                'type': 'object',
                'description': 'Volume bindings',
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'bind': {'type': 'string'},
                        'mode': {'type': 'string'}
                    },
                    'required': ['bind']
                },
                'default': {}
            },
            'port_bindings': {
                'type': 'object',
                'description': 'Port bindings',
                'additionalProperties': {
                    'type': ['array', 'null'],
                    'items': {
                        'type': 'object',
                        'properties': {
                            'HostPort': {'type': 'string'},
                            'HostIp': {'type': 'string'}
                        }
                    }
                },
                'default': {}
            },
            'links': {
                'type': 'object',
                'description': 'Links to other containers',
                'additionalProperties': {'type': 'string'},
                'default': {}
            },
            'restart_policy': {
                'type': 'object',
                'description': 'Container restart policy',
                'properties': {
                    'Name': {
                        'type': 'string',
                        'enum': ['no', 'on-failure', 'unless-stopped', 'always'],
                        'default': 'no'
                    },
                    'MaximumRetryCount': {
                        'type': 'integer',
                        'default': 0
                    }
                },
                'default': {'Name': 'no', 'MaximumRetryCount': 0}
            },
            'cap_add': {
                'type': 'array',
                'description': 'Add Linux capabilities',
                'items': {'type': 'string'},
                'default': []
            },
            'cap_drop': {
                'type': 'array',
                'description': 'Drop Linux capabilities',
                'items': {'type': 'string'},
                'default': []
            }
        },
        'required': ['container_id']
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'container': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'status': {'type': 'string'},
                    'warnings': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                },
                'required': ['id', 'name', 'status']
            },
            'error': {'type': 'string'}
        },
        'required': ['success']
    }
)
@handle_docker_errors
@check_docker_available
async def start_container(
    container_id: str,
    detach: bool = True,
    binds: Optional[Dict[str, Dict[str, str]]] = None,
    port_bindings: Optional[Dict[str, Optional[List[Dict[str, str]]]]] = None,
    links: Optional[Dict[str, str]] = None,
    restart_policy: Optional[Dict[str, Any]] = None,
    cap_add: Optional[List[str]] = None,
    cap_drop: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Start a stopped container with the specified configuration.
    
    Args:
        container_id: ID or name of the container to start
        detach: Run container in the background
        binds: Volume bindings
        port_bindings: Port bindings
        links: Links to other containers
        restart_policy: Container restart policy
        cap_add: Add Linux capabilities
        cap_drop: Drop Linux capabilities
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - container: Dictionary with container details if successful
        - error: Error message if success is False
        
    Example:
        ```python
        # Start a container with default settings
        result = await start_container(
            container_id="my-container"
        )
        
        if result['success']:
            logger.info(f"Started container {result['container']['id']}")
        
        # Start a container with port bindings
        result = await start_container(
            container_id="my-container",
            port_bindings={
                "80/tcp": [{"HostPort": "8080"}],
                "443/tcp": [{"HostPort": "8443"}]
            }
        )
        ```
    """
    if not docker_available:
        return format_daemon_not_running()
        
    try:
        # Convert parameters to StartContainerRequest
        request = StartContainerRequest(
            container_id=container_id,
            detach=detach,
            binds=binds or {},
            port_bindings=port_bindings or {},
            links=links or {},
            restart_policy=restart_policy or {'Name': 'no', 'MaximumRetryCount': 0},
            cap_add=cap_add or [],
            cap_drop=cap_drop or []
        )
        
        # Call the implementation
        container = await _start_container_impl(request)
        
        return {
            'success': True,
            'container': container,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Error starting container {container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'container': None,
            'error': error_msg
        }
@handle_docker_errors
@check_docker_available
async def restart_container(
    container_id: str,
    timeout: int = 10,
    force: bool = False
) -> Dict[str, Any]:
    """
    Restart a container with the specified configuration.
    
    Args:
        container_id: ID or name of the container to restart
        timeout: Timeout in seconds to wait for the container to stop before killing it
        force: Force restart the container (SIGKILL instead of SIGTERM)
        
    Returns:
        Dictionary with container restart details
        
    Example:
        ```python
        # Restart a container with default settings
        result = await restart_container(
            container_id="my-container"
        )
        
        # Force restart a container immediately
        result = await restart_container(
            container_id="my-container",
            timeout=0,
            force=True
        )
        
        # Gracefully restart a container with a 30-second timeout
        result = await restart_container(
            container_id="my-container",
            timeout=30,
            force=False
        )
        ```
    """
    if not docker_available:
        return format_daemon_not_running()
        
    request = ContainerLifecycleRequest(
        container_id=container_id,
        action=ContainerAction.RESTART,
        timeout=timeout,
        force=force
    )
    return await _restart_container_impl(request)

@tool(
    name="stop_container",
    description="Stop a running container with the specified configuration",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container to stop',
                'default': ''
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds to wait for the container to stop before killing it',
                'minimum': 0,
                'default': 10
            },
            'force': {
                'type': 'boolean',
                'description': 'Force stop the container (SIGKILL instead of SIGTERM)',
                'default': False
            }
        },
        'required': ['container_id']
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'container': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'status': {'type': 'string'},
                    'stopped': {'type': 'boolean'}
                },
                'required': ['id', 'name', 'status', 'stopped']
            },
            'error': {'type': 'string'}
        },
        'required': ['success']
    }
)
@handle_docker_errors
@check_docker_available
async def stop_container(
    container_id: str,
    timeout: int = 10,
    force: bool = False
) -> Dict[str, Any]:
    """
    Stop a running container with the specified configuration.
    
    Args:
        container_id: ID or name of the container to stop
        timeout: Timeout in seconds to wait for the container to stop before killing it
        force: If True, force stop the container (SIGKILL instead of SIGTERM)
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - container: Dictionary with container details if successful
        - error: Error message if success is False
        
    Example:
        ```python
        # Stop a container with default settings
        result = await stop_container(
            container_id="my-container"
        )
        
        if result['success']:
            logger.info(f"Stopped container {result['container']['id']}")
        
        # Force stop a container immediately
        result = await stop_container(
            container_id="my-container",
            timeout=0,
            force=True
        )
        
        # Gracefully stop a container with a 30-second timeout
        result = await stop_container(
            container_id="my-container",
            timeout=30,
            force=False
        )
        ```
    """
    if not docker_available:
        return format_daemon_not_running()
        
    try:
        # Convert parameters to StopContainerRequest
        request = StopContainerRequest(
            container_id=container_id,
            timeout=timeout,
            force=force
        )
        
        # Call the implementation
        container = await _stop_container_impl(request)
        
        return {
            'success': True,
            'container': container,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Error stopping container {container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'container': None,
            'error': error_msg
        }

@tool(
    name="stop_container",
    description="Stop a running container with the specified configuration",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container to stop',
                'default': ''
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds to wait for the container to stop before killing it',
                'minimum': 0,
                'default': 10
            },
            'force': {
                'type': 'boolean',
                'description': 'Force stop the container (SIGKILL instead of SIGTERM)',
                'default': False
            }
        },
        'required': ['container_id']
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'container': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'status': {'type': 'string'},
                    'stopped': {'type': 'boolean'}
                },
                'required': ['id', 'name', 'status', 'stopped']
            },
            'error': {'type': 'string'}
        },
        'required': ['success']
    }
)
@handle_docker_errors
@check_docker_available
async def stop_container(
    container_id: str,
    timeout: int = 10,
    force: bool = False
) -> Dict[str, Any]:
    """
    Stop a running container with the specified configuration.
    
    Args:
        container_id: ID or name of the container to stop
        timeout: Timeout in seconds to wait for the container to stop before killing it
        force: If True, force stop the container (SIGKILL instead of SIGTERM)
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - container: Dictionary with container details if successful
        - error: Error message if success is False
        
    Example:
        ```python
        # Stop a container with default settings
        result = await stop_container(
            container_id="my-container"
        )
        
        if result['success']:
            logger.info(f"Stopped container {result['container']['id']}")
        
        # Force stop a container immediately
        result = await stop_container(
            container_id="my-container",
            timeout=0,
            force=True
        )
        
        # Gracefully stop a container with a 30-second timeout
        result = await stop_container(
            container_id="my-container",
            timeout=30,
            force=False
        )
        ```
    """
    if not docker_available:
        return format_daemon_not_running()
        
    try:
        # Convert parameters to StopContainerRequest
        request = StopContainerRequest(
            container_id=container_id,
            timeout=timeout,
            force=force
        )
        
        # Call the implementation
        container = await _stop_container_impl(request)
        
        return {
            'success': True,
            'container': container,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Error stopping container {container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'container': None,
            'error': error_msg
        }

@tool(
    name="remove_container",
    description="Remove a container with the specified configuration",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container to remove',
                'default': ''
            },
            'force': {
                'type': 'boolean',
                'description': 'Force remove the container if it is running',
                'default': False
            },
            'remove_volumes': {
                'type': 'boolean',
                'description': 'Remove anonymous volumes associated with the container',
                'default': False
            },
            'remove_links': {
                'type': 'boolean',
                'description': 'Remove the specified link and not the underlying container',
                'default': False
            }
        },
        'required': ['container_id']
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'container': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'removed': {'type': 'boolean'},
                    'message': {'type': 'string'}
                },
                'required': ['id', 'name', 'removed', 'message']
            },
            'error': {'type': 'string'}
        },
        'required': ['success']
    }
)
@handle_docker_errors
@check_docker_available
async def remove_container(
    container_id: str,
    force: bool = False,
    remove_volumes: bool = False,
    remove_links: bool = False
) -> Dict[str, Any]:
    """
    Remove a container with the specified configuration.
    
    Args:
        container_id: ID or name of the container to remove
        force: Force remove the container if it is running
        remove_volumes: Remove anonymous volumes associated with the container
        remove_links: Remove the specified link and not the underlying container
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - container: Dictionary with container details if successful
        - error: Error message if success is False
        
    Example:
        ```python
        # Remove a stopped container
        result = await remove_container(
            container_id="my-container"
        )
        
        if result['success']:
            logger.info(f"Removed container {result['container']['id']}")
        
        # Force remove a running container
        result = await remove_container(
            container_id="my-container",
            force=True
        )
        ```
    """
    if not docker_available:
        return format_daemon_not_running()
        
    try:
        # Convert parameters to RemoveContainerRequest
        request = RemoveContainerRequest(
            container_id=container_id,
            force=force,
            remove_volumes=remove_volumes,
            remove_links=remove_links
        )
        
        # Call the implementation
        container = await _remove_container_impl(request)
        
        return {
            'success': True,
            'container': container,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Error removing container {container_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'container': None,
            'error': error_msg
        }

@tool(
    name="prune_containers",
    description="Remove all stopped containers with the specified configuration",
    parameters={
        'type': 'object',
        'properties': {
            'filters': {
                'type': 'object',
                'description': 'Filters to apply when pruning containers',
                'properties': {
                    'until': {
                        'type': 'string',
                        'description': 'Timestamp to filter containers created before this time',
                        'format': 'date-time'
                    },
                    'label': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Only remove containers with the given labels'
                    },
                    'label!': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Exclude containers with the given labels'
                    },
                    'status': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'enum': ['created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead']
                        },
                        'description': 'Filter containers by status'
                    }
                },
                'default': {}
            }
        },
        'required': []
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'result': {
                'type': 'object',
                'properties': {
                    'containers_deleted': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of container IDs that were deleted'
                    },
                    'space_reclaimed': {
                        'type': 'integer',
                        'description': 'Disk space reclaimed in bytes'
                    }
                },
                'required': ['containers_deleted', 'space_reclaimed']
            },
            'error': {'type': 'string'}
        },
        'required': ['success']
    }
)
@handle_docker_errors
@check_docker_available
async def prune_containers(
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Remove all stopped containers with the specified configuration.
    
    Args:
        filters: Dictionary of filters to apply when pruning containers
            - until (str): Timestamp to filter containers created before this time
            - label (List[str]): Only remove containers with the given labels
            - label! (List[str]): Exclude containers with the given labels
            - status (List[str]): Filter containers by status
            
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - result: Dictionary with pruning results if successful
            - containers_deleted: List of container IDs that were deleted
            - space_reclaimed: Disk space reclaimed in bytes
        - error: Error message if success is False
        
    Example:
        ```python
        # Prune all stopped containers
        result = await prune_containers()
        
        if result['success']:
            logger.info(f"Reclaimed {result['result']['space_reclaimed']} bytes")
        
        # Prune containers created before a specific time
        result = await prune_containers(
            filters={
                'until': '2023-01-01T00:00:00Z'
            }
        )
        
        # Prune containers with specific labels
        result = await prune_containers(
            filters={
                'label': ['app=test', 'environment=dev']
            }
        )
        
        # Prune only exited containers
        result = await prune_containers(
            filters={
                'status': ['exited']
            }
        )
        ```
    """
    if not docker_available:
        return format_daemon_not_running()
        
    try:
        # Convert parameters to PruneContainersRequest
        request = PruneContainersRequest(filters=filters or {})
        
        # Call the implementation
        result = await _prune_containers_impl(request)
        
        return {
            'success': True,
            'result': result,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Error pruning containers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'result': None,
            'error': error_msg
        }

# Container Logs Tools
# -----------------------------------------------------------------------------

@tool(
    name="get_container_logs",
    description="Get logs from a container with the specified configuration",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container',
                'default': ''
            },
            'follow': {
                'type': 'boolean',
                'description': 'Follow log output (returns AsyncGenerator when True)',
                'default': False
            },
            'stdout': {
                'type': 'boolean',
                'description': 'Return STDOUT logs',
                'default': True
            },
            'stderr': {
                'type': 'boolean',
                'description': 'Return STDERR logs',
                'default': True
            },
            'since': {
                'type': 'string',
                'description': 'Show logs since timestamp (e.g., 2023-01-01T00:00:00Z) or relative (e.g., 10m for 10 minutes)',
                'default': ''
            },
            'until': {
                'type': 'string',
                'description': 'Show logs before a timestamp (e.g., 2023-01-01T00:00:00Z) or relative (e.g., 10m for 10 minutes)',
                'default': ''
            },
            'timestamps': {
                'type': 'boolean',
                'description': 'Show timestamps',
                'default': False
            },
            'tail': {
                'type': 'string',
                'description': 'Number of lines to show from the end of the logs (e.g., "100" or "all")',
                'default': 'all'
            }
        },
        'required': ['container_id']
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'result': {
                'type': 'object',
                'properties': {
                    'logs': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of log lines'
                    },
                    'required': ['log']
                }
            },
            'message': {'type': 'string', 'description': 'Status message'}
        },
        'required': ['container_id']
    }
)
@handle_docker_errors
@check_docker_available
async def get_container_logs(
    container_id: str,
    follow: bool = False,
    stdout: bool = True,
    stderr: bool = True,
    since: str = '',
    until: str = '',
    timestamps: bool = False,
    tail: str = 'all',
    details: bool = False
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """
    Get logs from a container with the specified configuration.
    
    Args:
        container_id: ID or name of the container
        follow: If True, returns an async generator that yields log lines as they come in.
                If False, returns a dictionary with all logs at once.
        stdout: Return STDOUT logs
        stderr: Return STDERR logs
        since: Show logs since timestamp (e.g., 2023-01-01T00:00:00Z) or relative (e.g., 10m for 10 minutes)
        until: Show logs before a timestamp (e.g., 2023-01-01T00:00:00Z) or relative (e.g., 10m for 10 minutes)
        timestamps: Show timestamps
        tail: Number of lines to show from the end of the logs (default: all)
        details: Show extra details provided to logs
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the operation was successful
        - result: Dictionary with log data if successful
            - logs: List of log entries
            - container_id: ID of the container
            - container_name: Name of the container
        - error: Error message if success is False
        
        If follow=True, returns an AsyncGenerator that yields log entries as they come in
        with the same structure.
        
    Example:
        ```python
        # Get the last 100 lines of logs (synchronous)
        result = await get_container_logs(
            container_id="my-container",
            tail="100"
        )
        
        if result['success']:
            for log in result['result']['logs']:
                logger.info(log)
        
        # Follow logs in real-time (asynchronous)
        log_gen = get_container_logs(
            container_id="my-container",
            follow=True
        )
        
        async for log_entry in log_gen:
            if log_entry['success']:
                logger.info(log_entry['result']['log'])
            else:
                logger.error(f"Error: {log_entry['error']}")
        ```
    """
    if not docker_available:
        return format_daemon_not_running()
        
    try:
        # Convert parameters to GetContainerLogsRequest
        request = GetContainerLogsRequest(
            container_id=container_id,
            follow=follow,
            stdout=stdout,
            stderr=stderr,
            since=since,
            until=until,
            timestamps=timestamps,
            tail=tail,
            details=details
        )
        
        if follow:
            # For streaming logs, wrap the generator to maintain consistent response format
            async def wrapped_generator():
                try:
                    async for log_entry in _stream_container_logs_impl(request):
                        yield {
                            'success': True,
                            'result': log_entry,
                            'error': None
                        }
                except Exception as e:
                    error_msg = f"Error streaming container logs: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    yield {
                        'success': False,
                        'result': None,
                        'error': error_msg
                    }
            
            return wrapped_generator()
        else:
            # For non-streaming logs, call the implementation directly
            logs = await _get_container_logs_impl(request)
            return {
                'success': True,
                'result': logs,
                'error': None
            }
            
    except Exception as e:
        error_msg = f"Error getting container logs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        if follow:
            # For streaming, return a generator that yields the error
            async def error_generator():
                yield {
                    'success': False,
                    'result': None,
                    'error': error_msg
                }
            return error_generator()
        else:
            # For non-streaming, return the error directly
            return {
                'success': False,
                'result': None,
                'error': error_msg
            }
    # The function now properly handles both streaming and non-streaming cases
    # in the try-except block above, so we can remove this redundant code
        # For streaming logs, use the async generator
        try:
            async for log_entry in stream_container_logs(request):
                # Convert the log entry to the expected format
                yield {
                    'container_id': container_id,
                    'timestamp': log_entry.get('timestamp', ''),
                    'stream': log_entry.get('stream', 'stdout'),
                    'log': log_entry.get('line', '')
                }
        except Exception as e:
            logger.error(f"Error streaming logs: {str(e)}", exc_info=True)
            yield {
                'container_id': container_id,
                'error': str(e),
                'message': 'Error streaming logs'
            }
    else:
        # For non-streaming logs, collect all logs and return them
        try:
            logs = []
            # Set up a timeout for non-streaming logs
            request.follow = False
            
            # Collect all log entries
            async for log_entry in stream_container_logs(request):
                logs.append({
                    'timestamp': log_entry.get('timestamp', ''),
                    'stream': log_entry.get('stream', 'stdout'),
                    'log': log_entry.get('line', '')
                })
            
            # Yield the final result and stop iteration
            yield {
                'container_id': container_id,
                'logs': logs,
                'message': f'Retrieved {len(logs)} log entries'
            }
            raise StopAsyncIteration
            
        except Exception as e:
            logger.error(f"Error getting container logs: {str(e)}", exc_info=True)
            yield {
                'container_id': container_id,
                'error': str(e),
                'message': 'Error getting container logs',
                'logs': []
            }
            raise StopAsyncIteration

# Container Execution Tools
# -----------------------------------------------------------------------------

@tool(
    name="execute_in_container",
    description="Execute a command in a running container with the specified configuration"
)
@handle_docker_errors
@check_docker_available
async def execute_in_container(request: ContainerExecRequest) -> Dict[str, Any]:
    """Execute a command in a container with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await _execute_in_container(request)

@tool(
    name="exec_command",
    description="Execute a command in a running container (legacy interface) with the specified configuration"
)
@handle_docker_errors
@check_docker_available
async def exec_command(request: ExecCommandRequest) -> Dict[str, Any]:
    """Execute a command in a container (legacy interface) with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await _exec_command(request)

# Container Inspection Tools
# -----------------------------------------------------------------------------

@tool(
    name="inspect_container",
    description="Inspect a container with the specified configuration"
)
@handle_docker_errors
@check_docker_available
async def inspect_container(request: InspectContainerRequest) -> Dict[str, Any]:
    """Inspect a container with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await _inspect_container(request)

@tool(
    name="container_stats",
    description="Get container resource usage statistics with the specified configuration"
)
@handle_docker_errors
@check_docker_available
async def container_stats(request: ContainerStatsRequest) -> Dict[str, Any]:
    """Get container stats with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await _container_stats(request)

@tool(
    name="container_top",
    description="Display the running processes of a container with the specified configuration"
)
@handle_docker_errors
@check_docker_available
async def container_top(request: ContainerTopRequest) -> Dict[str, Any]:
    """Get container top processes with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await _container_top(request)

# Tool registration
# In FastMCP 2.12+, tools are automatically registered via the @Tool decorator
# This function is kept for backward compatibility
def get_tools():
    """
    Get all tools defined in this module for registration with FastMCP 2.12+.
    
    This function returns a list of tool instances that have been decorated
    with @Tool and should be registered with the FastMCP tool registry.
    
    Returns:
        List of tool functions decorated with @Tool
    """
    import inspect
    from inspect import isfunction, getmembers
    
    # Get all functions in this module that have been decorated with @Tool
    tools = [
        func for _, func in getmembers(inspect.currentframe().f_globals['__builtins__']['__import__'](inspect.currentframe().f_globals['__name__'])) 
        if isfunction(func) and hasattr(func, '_tool')
    ]
    
    logger.info(f"Found {len(tools)} container tools with @Tool decorator")
    return tools

@handle_docker_errors
@check_docker_available
async def _create_container_impl(request: ContainerLifecycleRequest) -> Dict[str, Any]:
    """Implementation of create_container with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await container_lifecycle.create_container_impl(request)

@handle_docker_errors
@check_docker_available
async def _list_containers_impl(request: ListContainersRequest) -> List[Dict[str, Any]]:
    """
    Implementation of list_containers with error handling.
    
    Args:
        request: ListContainersRequest with filtering options
        
    Returns:
        List of container information dictionaries
    """
    if not docker_available:
        return []
        
    try:
        # Import here to avoid circular imports
        from . import container_lifecycle
        containers = await container_lifecycle.list_containers_impl(request)
        
        # Convert ContainerInfo objects to dictionaries
        return [
            {
                'id': container.id,
                'name': container.name,
                'image': container.image,
                'status': container.status,
                'state': container.state.value,
                'created': container.created.isoformat(),
                'ports': container.ports,
                'networks': container.networks
            }
            for container in containers
        ]
    except Exception as e:
        logger.error(f"Error listing containers: {str(e)}", exc_info=True)
        return []

@handle_docker_errors
@check_docker_available
async def _start_container_impl(request: StartContainerRequest) -> Dict[str, Any]:
    """Implementation of start_container with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await container_lifecycle.start_container_impl(request)

@handle_docker_errors
@check_docker_available
async def _stop_container_impl(request: StopContainerRequest) -> Dict[str, Any]:
    """Implementation of stop_container with error handling."""
    if not docker_available:
        return format_daemon_not_running()
    return await container_lifecycle.stop_container_impl(request)

# All tool functions are now defined above with @Tool decorators and proper error handling

# Public API
# -----------------------------------------------------------------------------
# This section defines the public interface of the module. Only symbols listed
# in __all__ will be available when importing from this module.

__all__ = [
    # Functions
    'get_tools',
    # Container Lifecycle Management
    'list_containers',
    'create_container',
    'start_container',
    'stop_container',
    'restart_container',
    'remove_container',
    'prune_containers',
    
    # Log Management
    'get_container_logs',
    'stream_container_logs',
    
    # Command Execution
    'execute_in_container',
    'exec_command',
    
    # Inspection and Monitoring
    'inspect_container',
    'container_stats',
    'container_top',
    
    # Models and Types
    'ContainerInfo',
    'ContainerLifecycleRequest',
    'ContainerLifecycleResponse',
    'ContainerLogsRequest',
    'ContainerLogsResponse',
    'ContainerExecRequest',
    'ContainerExecResponse',
    'ContainerInspectRequest',
    'ContainerInspectResponse',
    'ContainerStatsRequest',
    'ContainerStatsResponse',
    'ContainerTopRequest',
    'ContainerTopResponse',
    'ListContainersRequest',
    'StartContainerRequest',
    'StopContainerRequest',
    'PruneContainersRequest',
    'ExecCommandRequest',
    'InspectContainerRequest',
    
    # Utility functions
    'create_response',
    'handle_error',
    'container_mgr',
    'run_docker_command',
    
    # Container lifecycle functions
    'manage_container_lifecycle',
]
