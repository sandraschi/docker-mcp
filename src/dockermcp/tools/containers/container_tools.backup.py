"""
Container management tools for Docker MCP.

This module provides a unified interface to container management functionality,
re-exporting tools from specialized modules for backward compatibility.

New code should import directly from the specialized modules:
- container_lifecycle.py: Container lifecycle operations (create, start, stop, etc.)
- container_logs.py: Log retrieval and streaming
- container_exec.py: Command execution in containers
- container_inspect.py: Container inspection and monitoring
"""
from dockermcp.logging_config import logger, configure_logging
configure_logging()


import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from fastmcp.tools import Tool
from pydantic import BaseModel

# Re-export container models for backward compatibility
from .container_models import (
    ContainerInfo,
    ContainerLifecycleRequest,
    ContainerLifecycleResponse,
    ContainerLogsRequest,
    ContainerLogsResponse,
    ContainerExecRequest,
    ContainerExecResponse,
    ContainerInspectRequest,
    ContainerInspectResponse,
    ContainerStatsRequest,
    ContainerStatsResponse,
    ContainerTopRequest,
    ContainerTopResponse,
    ListContainersRequest,
    StartContainerRequest,
    StopContainerRequest,
    PruneContainersRequest,
    ExecCommandRequest,
    InspectContainerRequest,
)

# Import container manager type for type checking
from ..core.containers import ContainerManager

# Import container manager and utilities
from .container_utils import (
    create_response,
    handle_error,
    container_mgr,
    run_docker_command,
)

# Import tool implementations from specialized modules
from .container_lifecycle import (
    list_containers,
    create_container,
    start_container,
    stop_container,
    restart_container,
    remove_container,
    prune_containers,
)

from .container_logs import (
    get_container_logs,
    stream_container_logs as _stream_container_logs,
)

from .container_exec import (
    execute_in_container,
    exec_command,
)

from .container_inspect import (
    inspect_container,
    container_stats,
    container_top,
)

# Set up logging
logger = logging.getLogger(__name__)

# For backward compatibility, alias stream_container_logs to get_container_logs
stream_container_logs = get_container_logs

# Type variables for request/response models
T = TypeVar('T', bound=BaseModel)

# Re-export container_mgr with proper type annotation
container_mgr = cast(ContainerManager, container_mgr)

# Re-export the container manager and utility functions
__all__ = [
    # Models
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
    'list_containers',
    'create_container',
    'start_container',
    'stop_container',
    'restart_container',
    'remove_container',
    'prune_containers',
    
    # Log functions
    'get_container_logs',
    'stream_container_logs',
    
    # Exec functions
    'execute_in_container',
    'exec_command',
    
    # Inspection functions
    'inspect_container',
    'container_stats',
    'container_top',
]

# Type variables for request/response models
T = TypeVar('T', bound=BaseModel)

# Re-export container_mgr with proper type annotation
container_mgr = cast(ContainerManager, container_mgr)

# For backward compatibility, delegate to the new implementations
@Tool(
    name='list_containers',
    description='List containers with various filtering options',
    parameters={
        'type': 'object',
        'properties': {
            'all_states': {
                'type': 'boolean',
                'default': False,
                'description': 'Show all containers (default shows just running)'
            },
            'filters': {
                'type': 'object',
                'description': 'Filter containers by various criteria'
            },
            'limit': {
                'type': 'integer',
                'description': 'Limit the number of containers to return'
            },
            'size': {
                'type': 'boolean',
                'default': False,
                'description': 'Include container size information'
            },
            'format': {
                'type': 'string',
                'enum': ['minimal', 'standard', 'detailed'],
                'default': 'standard',
                'description': 'Output format (minimal, standard, detailed)'
            }
        }
    },
    },
            'warnings': {
                'type': 'array',
                'items': {'type': 'string'}
            },
            'error': {'type': 'string'},
            'error_type': {'type': 'string'}
        }
    }
)
def list_containers(
    all_states: bool = False,
    filters: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    size: bool = False,
    format: str = 'standard'
) -> Dict[str, Any]:
    """
    List containers with various filtering options.
    
    This is a facade function that delegates to the implementation in container_lifecycle.py
    """
    return list_containers(all_states, filters, limit, size, format)

@Tool(
    name='create_container',
    description='Create a new Docker container from an image with advanced configuration options',
    parameters={
        'type': 'object',
        'properties': {
            'image': {
                'type': 'string',
                'description': 'Name of the image to use for the container',
                'examples': ['nginx:latest', 'postgres:13']
            },
            'name': {
                'type': 'string',
                'description': 'Name to assign to the container',
                'examples': ['my-nginx', 'db-container']
            },
            'command': {
                'type': 'string',
                'description': 'Command to run in the container',
                'examples': ['nginx -g \'daemon off;\'', 'bash']
            },
            'entrypoint': {
                'type': 'string',
                'description': 'Override the default entrypoint of the image',
                'examples': ['/bin/sh', '/app/start.sh']
            },
            'environment': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'description': 'Environment variables to set in the container',
                'examples': [{'NODE_ENV': 'production', 'DEBUG': 'true'}]
            },
            'ports': {
                'type': 'object',
                'additionalProperties': {
                    'oneOf': [
                        {'type': 'string'},
                        {'type': 'integer'},
                        {
                            'type': 'object',
                            'properties': {
                                'host_ip': {'type': 'string'},
                                'host_port': {'type': 'integer'}
                            }
                        }
                    ]
                },
                'description': 'Port mappings (format: {"container_port": "host_port" or {"host_port": 8080, "host_ip": "0.0.0.0"}})',
                'examples': [{'80/tcp': 8080}, {'5432/tcp': 5432}]
            },
            'volumes': {
                'type': 'object',
                'additionalProperties': {
                    'oneOf': [
                        {'type': 'string'},
                        {
                            'type': 'object',
                            'properties': {
                                'bind': {'type': 'string'},
                                'mode': {'type': 'string', 'enum': ['ro', 'rw']}
                            },
                            'required': ['bind']
                        }
                    ]
                },
                'description': 'Volume mappings (format: {"host_path": "container_path" or {"bind": "/container/path", "mode": "ro"}})',
                'examples': [{'/host/path': '/container/path'}, {'/data': {'bind': '/var/lib/data', 'mode': 'rw'}}]
            },
            'network': {
                'type': 'string',
                'description': 'Network to connect the container to',
                'default': 'bridge',
                'examples': ['bridge', 'host', 'none']
            },
            'network_mode': {
                'type': 'string',
                'description': 'Network mode for the container',
                'enum': ['bridge', 'host', 'none', 'container:<name|id>'],
                'default': 'bridge'
            },
            'restart_policy': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'enum': ['no', 'on-failure', 'always', 'unless-stopped'],
                        'default': 'no'
                    },
                    'maximum_retry_count': {
                        'type': 'integer',
                        'minimum': 0,
                        'default': 0
                    }
                },
                'required': ['name'],
                'description': 'Restart policy for the container',
                'examples': [{'name': 'always'}, {'name': 'on-failure', 'maximum_retry_count': 3}]
            },
            'cap_add': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Add Linux capabilities',
                'examples': [['NET_ADMIN', 'SYS_ADMIN']]
            },
            'cap_drop': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Drop Linux capabilities',
                'examples': [['NET_RAW']]
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'description': 'Labels to apply to the container',
                'examples': [{'com.example.app': 'myapp', 'environment': 'production'}]
            },
            'detach': {
                'type': 'boolean',
                'default': True,
                'description': 'Run container in the background (detached mode)'
            },
            'auto_remove': {
                'type': 'boolean',
                'default': False,
                'description': 'Automatically remove the container when it exits'
            },
            'tty': {
                'type': 'boolean',
                'default': False,
                'description': 'Allocate a pseudo-TTY'
            },
            'stdin_open': {
                'type': 'boolean',
                'default': False,
                'description': 'Keep STDIN open even if not attached'
            },
            'mem_limit': {
                'type': 'string',
                'description': 'Memory limit (format: <number>[<unit>], where unit = b, k, m, or g)',
                'examples': ['512m', '2g']
            },
            'cpus': {
                'type': 'number',
                'minimum': 0.1,
                'description': 'Number of CPUs to allocate',
                'examples': [1.5, 2]
            },
            'working_dir': {
                'type': 'string',
                'description': 'Working directory inside the container',
                'examples': ['/app', '/var/www']
            },
            'user': {
                'type': 'string',
                'description': 'Username or UID (format: <name|uid>[:<group|gid>])',
                'examples': ['1000', 'www-data:www-data']
            },
            'healthcheck': {
                'type': 'object',
                'properties': {
                    'test': {
                        'oneOf': [
                            {'type': 'string'},
                            {'type': 'array', 'items': {'type': 'string'}},
                            {'type': 'null'}
                        ],
                        'description': 'Command to run to check health (e.g., ["CMD", "curl", "-f", "http://localhost"] or "NONE")'
                    },
                    'interval': {
                        'type': 'integer',
                        'minimum': 1000000000,  # 1 second in nanoseconds
                        'description': 'Time between running the check (in nanoseconds)'
                    },
                    'timeout': {
                        'type': 'integer',
                        'minimum': 1000000000,  # 1 second in nanoseconds
                        'description': 'Maximum time to allow one check to run (in nanoseconds)'
                    },
                    'retries': {
                        'type': 'integer',
                        'minimum': 1,
                        'description': 'Consecutive failures needed to consider unhealthy'
                    },
                    'start_period': {
                        'type': 'integer',
                        'minimum': 0,
                        'description': 'Start period for the container to initialize before starting health-retries (in nanoseconds)'
                    }
                },
                'required': ['test'],
                'description': 'Health check configuration',
                'examples': [
                    {
                        'test': ["CMD", "curl", "-f", "http://localhost"],
                        'interval': 30000000000,  # 30 seconds
                        'timeout': 10000000000,   # 10 seconds
                        'retries': 3,
                        'start_period': 5000000000  # 5 seconds
                    }
                ]
            }
        },
        'required': ['image'],
        'additionalProperties': False
    },
    'message': {
                'type': 'string',
                'description': 'Status message indicating success or failure'
            },
            'container_id': {
                'type': 'string',
                'description': 'ID of the created container',
                'examples': ['a1b2c3d4e5f6']
            },
            'warnings': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Non-critical warnings about the operation'
            },
            'error': {
                'type': 'string',
                'description': 'Error message if the operation failed'
            },
            'error_type': {
                'type': 'string',
                'description': 'Type of error that occurred',
                'examples': ['ImageNotFound', 'DockerAPIError', 'UnexpectedError']
            }
        },
        'required': ['success', 'message']
    },
    examples=[
        {
            'name': 'Create a simple Nginx container',
            'description': 'Create a basic Nginx container with port mapping',
            'input': {
                'image': 'nginx:latest',
                'name': 'my-nginx',
                'ports': {'80/tcp': 8080},
                'detach': True
            },
            'output': {
                'success': True,
                'message': 'Container created successfully',
                'container_id': 'a1b2c3d4e5f6',
                'warnings': []
            }
        },
        {
            'name': 'Create a database container with volumes and environment',
            'description': 'Create a PostgreSQL container with persistent storage and environment variables',
            'input': {
                'image': 'postgres:13',
                'name': 'my-postgres',
                'environment': {
                    'POSTGRES_USER': 'admin',
                    'POSTGRES_PASSWORD': 'secret',
                    'POSTGRES_DB': 'mydb'
                },
                'volumes': {
                    'pgdata': {'bind': '/var/lib/postgresql/data', 'mode': 'rw'}
                },
                'ports': {'5432/tcp': 5432},
                'restart_policy': {'name': 'unless-stopped'}
            },
            'output': {
                'success': True,
                'message': 'Container created successfully',
                'container_id': 'b2c3d4e5f6g7',
                'warnings': []
            }
        }
    ]
)
def create_container(
    image: str,
    name: Optional[str] = None,
    command: Optional[Union[str, List[str]]] = None,
    entrypoint: Optional[Union[str, List[str]]] = None,
    environment: Optional[Dict[str, str]] = None,
    ports: Optional[Dict[str, Union[str, int, Dict[str, Union[str, int]]]]] = None,
    volumes: Optional[Dict[str, Union[str, Dict[str, str]]]] = None,
    network: str = 'bridge',
    network_mode: Optional[str] = None,
    restart_policy: Optional[Dict[str, Union[str, int]]] = None,
    cap_add: Optional[List[str]] = None,
    cap_drop: Optional[List[str]] = None,
    labels: Optional[Dict[str, str]] = None,
    detach: bool = True,
    auto_remove: bool = False,
    tty: bool = False,
    stdin_open: bool = False,
    mem_limit: Optional[str] = None,
    cpus: Optional[float] = None,
    working_dir: Optional[str] = None,
    user: Optional[str] = None,
    healthcheck: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new Docker container with the specified configuration.
    
    This is a facade function that delegates to the implementation in container_lifecycle.py
    """
    return _create_container(
        image,
        name,
        command,
        entrypoint,
        environment,
        ports,
        volumes,
        network,
        network_mode,
        restart_policy,
        cap_add,
        cap_drop,
        labels,
        detach,
        auto_remove,
        tty,
        stdin_open,
        mem_limit,
        cpus,
        working_dir,
        user,
        healthcheck
    )

@Tool(
    name="start_container",
    description="Start a stopped container",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to start"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container to start (alternative to container_id)"
            },
            "detach_keys": {
                "type": "string",
                "description": "Override the key sequence for detaching a container"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ]
    },
    "message": {"type": "string"},
            "container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "ports": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "created": {"type": "string", "format": "date-time"},
                    "started_at": {"type": "string", "format": "date-time"}
                },
                "required": ["id", "name", "status"]
            },
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "message"]
    },
    examples=[
        {
            "name": "Start a container by ID",
            "input": {
                "container_id": "a1b2c3d4e5f6"
            },
            "output": {
                "success": True,
                "message": "Container started successfully",
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "my-container",
                    "status": "running",
                    "ports": ["80/tcp -> 0.0.0.0:8080"],
                    "created": "2023-01-01T12:00:00Z",
                    "started_at": "2023-01-01T13:00:00Z"
                }
            }
        },
        {
            "name": "Start a container by name",
            "input": {
                "container_name": "my-container"
            },
            "output": {
                "success": True,
                "message": "Container my-container started successfully",
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "my-container",
                    "status": "running",
                    "ports": ["80/tcp -> 0.0.0.0:8080"],
                    "created": "2023-01-01T12:00:00Z",
                    "started_at": "2023-01-01T13:00:00Z"
                }
            }
        }
    ]
)
def start_container(
    request: StartContainerRequest
) -> Dict[str, Any]:
    """
    Start a stopped container.
    
    This is a facade function that delegates to the implementation in container_lifecycle.py
    """
    return _start_container(request)

@Tool(
    name='stop_container',
    description='Stop one or more running containers with advanced options',
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID of the container to stop (mutually exclusive with container_name)',
                'examples': ['a1b2c3d4e5f6']
            },
            'container_name': {
                'type': 'string',
                'description': 'Name of the container to stop (mutually exclusive with container_id)',
                'examples': ['my-container']
            },
            'timeout': {
                'type': 'integer',
                'description': 'Timeout in seconds to wait for the container to stop before killing it',
                'minimum': 0,
                'maximum': 300,
                'default': 10
            },
            'force': {
                'type': 'boolean',
                'description': 'Force stop the container (SIGKILL)',
                'default': False
            },
            'signal': {
                'type': 'string',
                'description': 'Signal to send to the container (e.g., SIGTERM, SIGKILL)',
                'default': 'SIGTERM',
                'examples': ['SIGTERM', 'SIGKILL', 'SIGINT', 'SIGHUP']
            },
            'wait': {
                'type': 'boolean',
                'description': 'Wait for the container to stop before returning',
                'default': True
            },
            'remove': {
                'type': 'boolean',
                'description': 'Remove the container after stopping it',
                'default': False
            },
            'remove_volumes': {
                'type': 'boolean',
                'description': 'Remove anonymous volumes associated with the container',
                'default': False
            },
            'links': {
                'type': 'boolean',
                'description': 'Remove the specified link and not the underlying container',
                'default': False
            },
            'check_interval': {
                'type': 'number',
                'description': 'Interval in seconds between container state checks',
                'minimum': 0.1,
                'maximum': 5.0,
                'default': 0.5
            },
            'validate': {
                'type': 'boolean',
                'description': 'Validate the container state before stopping',
                'default': True
            }
        },
        'oneOf': [
            {'required': ['container_id']},
            {'required': ['container_name']}
        ],
        'additionalProperties': False
    },
    'message': {
                'type': 'string',
                'description': 'Status message indicating success or failure'
            },
            'container_id': {
                'type': 'string',
                'description': 'ID of the container',
                'examples': ['a1b2c3d4e5f6']
            },
            'container_name': {
                'type': 'string',
                'description': 'Name of the container',
                'examples': ['my-container']
            },
            'state': {
                'type': 'string',
                'description': 'Current state of the container',
                'examples': ['exited', 'running', 'dead']
            },
            'status': {
                'type': 'string',
                'description': 'Human-readable status of the container',
                'examples': ['Exited (0) 5 minutes ago', 'Up 2 minutes']
            },
            'exit_code': {
                'type': 'integer',
                'description': 'Exit code of the container',
                'examples': [0, 137, 143]
            },
            'stopped_at': {
                'type': 'string',
                'format': 'date-time',
                'description': 'Timestamp when the container was stopped',
                'examples': ['2023-01-01T13:00:00Z']
            },
            'warnings': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'Non-critical warnings about the operation'
            },
            'error': {
                'type': 'string',
                'description': 'Error message if the operation failed'
            },
            'error_type': {
                'type': 'string',
                'description': 'Type of error that occurred',
                'examples': ['ContainerNotFound', 'DockerAPIError', 'UnexpectedError']
            }
        },
        'required': ['success', 'message']
    },
    examples=[
        {
            'name': 'Stop container by ID with timeout',
            'description': 'Stop a container using its ID with a 10-second timeout',
            'input': {
                'container_id': 'a1b2c3d4e5f6',
                'timeout': 10,
                'signal': 'SIGTERM'
            },
            'output': {
                'success': True,
                'message': 'Container stopped successfully',
                'container_id': 'a1b2c3d4e5f6',
                'container_name': 'my-container',
                'state': 'exited',
                'status': 'Exited (0) 5 seconds ago',
                'exit_code': 0,
                'stopped_at': '2023-01-01T13:00:00Z',
                'warnings': []
            }
        },
        {
            'name': 'Force stop and remove container by name',
            'description': 'Force stop a container using its name and remove it',
            'input': {
                'container_name': 'my-container',
                'force': True,
                'remove': True,
                'remove_volumes': True
            },
            'output': {
                'success': True,
                'message': 'Container stopped and removed successfully',
                'container_name': 'my-container',
                'state': 'removed',
                'status': 'Removed',
                'warnings': ['Container was removed']
            }
        }
    ]
)
async def stop_container(
    container_id: Optional[str] = None,
    container_name: Optional[str] = None,
    timeout: int = 10,
    force: bool = False,
    signal: str = 'SIGTERM',
    wait: bool = True,
    remove: bool = False,
    remove_volumes: bool = False,
    links: bool = False,
    check_interval: float = 0.5,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Stop one or more running containers with advanced options.
    
    This function stops a running container with the specified ID or name, with support for
    various stop options including timeouts, signals, and automatic removal.
    
    Args:
        container_id: ID of the container to stop (mutually exclusive with container_name)
        container_name: Name of the container to stop (mutually exclusive with container_id)
        timeout: Timeout in seconds to wait for the container to stop before killing it
        force: Force stop the container (SIGKILL)
        signal: Signal to send to the container (e.g., 'SIGTERM', 'SIGKILL')
        wait: Wait for the container to stop before returning
        remove: Remove the container after stopping it
        remove_volumes: Remove anonymous volumes associated with the container
        links: Remove the specified link and not the underlying container
        check_interval: Interval in seconds between container state checks
        validate: Validate the container state before stopping
        
    Returns:
        Dictionary containing:
        - success (bool): Whether the container was stopped successfully
        - message (str): Status message
        - container_id (str): ID of the container
        - container_name (str): Name of the container
        - state (str): Current state of the container
        - status (str): Human-readable status of the container
        - exit_code (int, optional): Exit code of the container
        - stopped_at (str, optional): Timestamp when the container was stopped
        - warnings (List[str], optional): Non-critical warnings
        - error (str, optional): Error message if stop failed
        - error_type (str, optional): Type of error that occurred
    """
    import time
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    result = {
        'success': False,
        'message': '',
        'container_id': container_id or '',
        'container_name': container_name or '',
        'state': '',
        'status': '',
        'exit_code': None,
        'stopped_at': '',
        'warnings': [],
        'error': None,
        'error_type': None
    }
    
    try:
        # Validate inputs
        if not container_id and not container_name:
            raise ValueError('Either container_id or container_name must be provided')
        if container_id and container_name:
            raise ValueError('Only one of container_id or container_name can be provided')
        
        # Get the container by ID or name
        try:
            if container_id:
                container = container_mgr.get_container(container_id=container_id)
            else:
                container = container_mgr.get_container(container_name=container_name)
                result['container_id'] = container.id
                result['container_name'] = container_name
        except docker.errors.NotFound:
            error_msg = f'Container not found: {container_id or container_name}'
            logger.error(error_msg)
            result.update({
                'message': error_msg,
                'error': error_msg,
                'error_type': 'ContainerNotFound'
            })
            return result
        
        # Update result with container info
        result['container_id'] = container.id
        result['container_name'] = container.name
        container.reload()
        
        # Check if container is already stopped
        if container.status == 'exited' and not force and not remove:
            result.update({
                'success': True,
                'message': 'Container is already stopped',
                'state': container.status,
                'status': container.attrs.get('State', {}).get('Status', ''),
                'exit_code': container.attrs.get('State', {}).get('ExitCode'),
                'stopped_at': container.attrs.get('State', {}).get('FinishedAt', '')
            })
            return result
        
        # Log the stop request
        logger.info(
            'Stopping container %s (ID: %s) with %s (timeout: %ds, force: %s)',
            container.name,
            container.id,
            signal,
            timeout,
            force
        )
        
        # Stop the container
        try:
            container.stop(
                timeout=timeout if not force else 0,
                signal=signal if not force else 'SIGKILL'
            )
        except docker.errors.APIError as e:
            if 'is not running' in str(e):
                logger.info('Container %s is already stopped', container.id)
            else:
                raise
        
        # Wait for container to stop if requested
        if wait:
            start_time = time.time()
            while time.time() - start_time < (timeout + 2):  # Add buffer time
                container.reload()
                if container.status == 'exited':
                    break
                time.sleep(check_interval)
            else:
                if force:
                    logger.warning('Container %s did not stop within timeout, forcing...', container.id)
                    container.kill()
                else:
                    error_msg = f'Timeout waiting for container {container.id} to stop'
                    logger.error(error_msg)
                    result.update({
                        'message': error_msg,
                        'error': error_msg,
                        'error_type': 'StopTimeout',
                        'state': container.status,
                        'status': container.attrs.get('State', {}).get('Status', '')
                    })
                    return result
        
        # Remove the container if requested
        if remove:
            try:
                container.remove(v=remove_volumes, link=links, force=force)
                result['warnings'].append('Container was removed')
                result['state'] = 'removed'
                result['status'] = 'Removed'
            except Exception as e:
                error_msg = f'Failed to remove container: {str(e)}'
                logger.warning(error_msg)
                result['warnings'].append(error_msg)
        
        # Get the final container state if not removed
        if not remove:
            container.reload()
            result.update({
                'state': container.status,
                'status': container.attrs.get('State', {}).get('Status', ''),
                'exit_code': container.attrs.get('State', {}).get('ExitCode'),
                'stopped_at': container.attrs.get('State', {}).get('FinishedAt', '')
            })
        
        # Set success and message
        result.update({
            'success': True,
            'message': 'Container stopped successfully' + (' and removed' if remove else '')
        })
        
        logger.info(
            'Successfully stopped container %s (State: %s, Status: %s)',
            container.id,
            result['state'],
            result['status']
        )
        
        return result
        
    except docker.errors.NotFound as e:
        error_msg = f'Container not found: {container_id or container_name}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': error_msg,
            'error': str(e),
            'error_type': 'ContainerNotFound'
        })
        return result
        
    except docker.errors.APIError as e:
        error_msg = f'Docker API error while stopping container: {str(e)}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': 'Failed to stop container due to Docker API error',
            'error': str(e),
            'error_type': 'DockerAPIError'
        })
        return result
        
    except Exception as e:
        error_msg = f'Unexpected error stopping container: {str(e)}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': 'Failed to stop container due to an unexpected error',
            'error': str(e),
            'error_type': 'UnexpectedError'
        })
        return result

@Tool(
    name="restart_container",
    description="Restart one or more containers with advanced options",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to restart (mutually exclusive with container_name)",
                "default": None
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container to restart (mutually exclusive with container_id)",
                "default": None
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds to wait for the container to stop before killing it",
                "default": 10,
                "minimum": 1
            },
            "signal": {
                "type": "string",
                "description": "Signal to send to the container (e.g., 'SIGTERM', 'SIGKILL')",
                "default": "SIGTERM"
            },
            "force": {
                "type": "boolean",
                "description": "Force stop the container before restarting (SIGKILL)",
                "default": False
            },
            "wait": {
                "type": "boolean",
                "description": "Wait for the container to be running before returning",
                "default": True
            },
            "check_interval": {
                "type": "number",
                "description": "Interval in seconds between container state checks",
                "default": 0.5,
                "minimum": 0.1,
                "maximum": 5.0
            },
            "validate": {
                "type": "boolean",
                "description": "Validate the container state before restarting",
                "default": True
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ],
        "additionalProperties": False
    },
    "message": {"type": "string"},
            "container_id": {"type": "string"},
            "container_name": {"type": "string"},
            "state": {"type": "string"},
            "status": {"type": "string"},
            "started_at": {"type": "string"},
            "restart_count": {"type": "integer"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "message"],
        "additionalProperties": False
    },
    examples=[
        {
            "container_id": "a1b2c3d4e5f6",
            "timeout": 30,
            "signal": "SIGTERM"
        },
        {
            "container_name": "my-web-app",
            "force": true,
            "wait": false
        }
    ]
)
async def restart_container(
    container_id: Optional[str] = None,
    container_name: Optional[str] = None,
    timeout: int = 10,
    signal: str = 'SIGTERM',
    force: bool = False,
    wait: bool = True,
    check_interval: float = 0.5,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Restart a container with advanced options.
    
    This function restarts a container with the specified ID or name, with support for
    various restart options including timeouts, signals, and validation.
    
    Args:
        container_id: ID of the container to restart (mutually exclusive with container_name)
        container_name: Name of the container to restart (mutually exclusive with container_id)
        timeout: Timeout in seconds to wait for the container to stop before killing it
        signal: Signal to send to the container (e.g., 'SIGTERM', 'SIGKILL')
        force: Force stop the container before restarting (SIGKILL)
        wait: Wait for the container to be running before returning
        check_interval: Interval in seconds between container state checks
        validate: Validate the container state before restarting
        
    Returns:
        Dictionary containing:
        - success (bool): Whether the container was restarted successfully
        - message (str): Status message
        - container_id (str): ID of the container
        - container_name (str): Name of the container
        - state (str): Current state of the container
        - status (str): Human-readable status of the container
        - started_at (str): Timestamp when the container was started
        - restart_count (int): Number of times the container has been restarted
        - warnings (List[str], optional): Non-critical warnings
        - error (str, optional): Error message if restart failed
        - error_type (str, optional): Type of error that occurred
    """
    import time
    from datetime import datetime
    
    # Initialize result dictionary
    result = {
        'success': False,
        'message': '',
        'container_id': '',
        'container_name': '',
        'state': '',
        'status': '',
        'started_at': '',
        'restart_count': 0,
        'warnings': []
    }
    
    # Get Docker client
    client = container_mgr.client
    
    try:
        # Get container by ID or name
        container = None
        try:
            if container_id:
                container = client.containers.get(container_id)
                result['container_id'] = container.id
                result['container_name'] = container.name
            elif container_name:
                container = client.containers.get(container_name)
                result['container_id'] = container.id
                result['container_name'] = container.name
            else:
                error_msg = 'Either container_id or container_name must be provided'
                logger.error(error_msg)
                result.update({
                    'message': error_msg,
                    'error': error_msg,
                    'error_type': 'ValidationError'
                })
                return result
        except docker.errors.NotFound as e:
            error_msg = f'Container not found: {container_id or container_name}'
            logger.error(error_msg, exc_info=True)
            result.update({
                'message': error_msg,
                'error': str(e),
                'error_type': 'ContainerNotFound'
            })
            return result
            
        # Log the restart request
        logger.info(
            'Restarting container %s (ID: %s) with timeout=%s, signal=%s, force=%s',
            container.name, container.id[:12], timeout, signal, force
        )
        
        # Validate container state if requested
        if validate:
            container.reload()
            if container.status not in ['running', 'paused', 'restarting']:
                error_msg = f'Container is not in a restartable state: {container.status}'
                logger.warning(error_msg)
                result.update({
                    'message': error_msg,
                    'error': error_msg,
                    'error_type': 'InvalidState',
                    'state': container.status,
                    'status': container.attrs.get('State', {}).get('Status', '')
                })
                return result
        
        # Get current restart count
        result['restart_count'] = container.attrs.get('RestartCount', 0)
        
        # Restart the container
        try:
            container.restart(timeout=timeout, signal=signal if not force else 'SIGKILL')
            logger.info('Successfully sent restart signal to container %s', container.id[:12])
        except docker.errors.APIError as e:
            error_msg = f'Docker API error while restarting container: {str(e)}'
            logger.error(error_msg, exc_info=True)
            result.update({
                'message': 'Failed to restart container due to Docker API error',
                'error': str(e),
                'error_type': 'DockerAPIError',
                'state': container.status,
                'status': container.attrs.get('State', {}).get('Status', '')
            })
            return result
        
        # Wait for container to be running if requested
        if wait:
            logger.debug('Waiting for container %s to be running...', container.id[:12])
            start_time = time.time()
            max_wait = max(timeout + 5, 30)  # Ensure minimum 30s wait time
            
            while time.time() - start_time < max_wait:
                container.reload()
                status = container.status.lower()
                
                if status == 'running':
                    logger.debug('Container %s is now running', container.id[:12])
                    break
                elif status in ['exited', 'dead', 'paused']:
                    error_msg = f'Container entered {status} state after restart'
                    logger.error(error_msg)
                    result.update({
                        'message': error_msg,
                        'error': error_msg,
                        'error_type': 'ContainerNotRunning',
                        'state': container.status,
                        'status': container.attrs.get('State', {}).get('Status', ''),
                        'exit_code': container.attrs.get('State', {}).get('ExitCode')
                    })
                    return result
                    
                time.sleep(check_interval)
            else:
                error_msg = f'Timeout waiting for container {container.id[:12]} to start running'
                logger.error(error_msg)
                result.update({
                    'message': error_msg,
                    'error': error_msg,
                    'error_type': 'StartTimeout',
                    'state': container.status,
                    'status': container.attrs.get('State', {}).get('Status', '')
                })
                return result
        
        # Get updated container info
        container.reload()
        result.update({
            'success': True,
            'message': f'Container {container.name} restarted successfully',
            'state': container.status,
            'status': container.attrs.get('State', {}).get('Status', ''),
            'started_at': container.attrs.get('State', {}).get('StartedAt', ''),
            'restart_count': container.attrs.get('RestartCount', result['restart_count'] + 1)
        })
        
        logger.info(
            'Successfully restarted container %s (State: %s, Status: %s, Restart count: %d)',
            container.name,
            result['state'],
            result['status'],
            result['restart_count']
        )
        
        return result
        
    except docker.errors.NotFound as e:
        error_msg = f'Container not found: {container_id or container_name}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': error_msg,
            'error': str(e),
            'error_type': 'ContainerNotFound'
        })
        return result
        
    except docker.errors.APIError as e:
        error_msg = f'Docker API error while restarting container: {str(e)}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': 'Failed to restart container due to Docker API error',
            'error': str(e),
            'error_type': 'DockerAPIError'
        })
        return result
        
    except Exception as e:
        error_msg = f'Unexpected error restarting container: {str(e)}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': 'Failed to restart container due to an unexpected error',
            'error': str(e),
            'error_type': 'UnexpectedError'
        })
        return result

@Tool(
    name="remove_container",
    description="Remove one or more containers with advanced options",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to remove (mutually exclusive with container_name)",
                "default": None
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container to remove (mutually exclusive with container_id)",
                "default": None
            },
            "force": {
                "type": "boolean",
                "description": "Force the removal of a running container (uses SIGKILL)",
                "default": False
            },
            "remove_volumes": {
                "type": "boolean",
                "description": "Remove anonymous volumes associated with the container",
                "default": False
            },
            "remove_links": {
                "type": "boolean",
                "description": "Remove the specified link and not the underlying container",
                "default": False
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds to wait for the container to stop before killing it (if force is False)",
                "default": 10,
                "minimum": 1
            },
            "check_interval": {
                "type": "number",
                "description": "Interval in seconds between container state checks",
                "default": 0.5,
                "minimum": 0.1,
                "maximum": 5.0
            },
            "validate": {
                "type": "boolean",
                "description": "Validate the container state before removal",
                "default": True
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ],
        "additionalProperties": False
    },
    "message": {"type": "string"},
            "container_id": {"type": "string"},
            "container_name": {"type": "string"},
            "removed": {"type": "boolean"},
            "removed_volumes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of volume names that were removed"
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
            "error": {"type": "string"},
            "error_type": {"type": "string"},
            "state_before_removal": {"type": "string"},
            "status_before_removal": {"type": "string"},
            "removed_at": {"type": "string", "format": "date-time"}
        },
        "required": ["success", "message", "container_id", "container_name", "removed"],
        "additionalProperties": False
    },
    examples=[
        {
            "container_id": "a1b2c3d4e5f6",
            "force": False,
            "remove_volumes": True,
            "remove_links": False
        },
        {
            "container_name": "my-web-app",
            "force": True,
            "remove_volumes": True,
            "timeout": 30
        }
    ]
)
async def remove_container(
    container_id: Optional[str] = None,
    container_name: Optional[str] = None,
    force: bool = False,
    remove_volumes: bool = False,
    remove_links: bool = False,
    timeout: int = 10,
    check_interval: float = 0.5,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Remove a container with advanced options.
    
    This function removes a container with the specified ID or name, with support for
    force removal, volume cleanup, and link management.
    
    Args:
        container_id: ID of the container to remove (mutually exclusive with container_name)
        container_name: Name of the container to remove (mutually exclusive with container_id)
        force: Force the removal of a running container (uses SIGKILL)
        remove_volumes: Remove anonymous volumes associated with the container
        remove_links: Remove the specified link and not the underlying container
        timeout: Timeout in seconds to wait for the container to stop before killing it
        check_interval: Interval in seconds between container state checks
        validate: Validate the container state before removal
        
    Returns:
        Dictionary containing:
        - success (bool): Whether the container was removed successfully
        - message (str): Status message
        - container_id (str): ID of the container
        - container_name (str): Name of the container
        - removed (bool): Whether the container was actually removed
        - removed_volumes (List[str]): List of volume names that were removed
        - warnings (List[str], optional): Non-critical warnings
        - error (str, optional): Error message if removal failed
        - error_type (str, optional): Type of error that occurred
        - state_before_removal (str, optional): State of the container before removal
        - status_before_removal (str, optional): Status of the container before removal
        - removed_at (str): Timestamp when the container was removed
    """
    import time
    from datetime import datetime
    
    # Initialize result dictionary
    result = {
        'success': False,
        'message': '',
        'container_id': '',
        'container_name': '',
        'removed': False,
        'removed_volumes': [],
        'warnings': [],
        'removed_at': datetime.utcnow().isoformat()
    }
    
    # Get Docker client
    client = container_mgr.client
    container = None
    
    try:
        # Get container by ID or name
        try:
            if container_id:
                container = client.containers.get(container_id)
                result['container_id'] = container.id
                result['container_name'] = container.name
            elif container_name:
                container = client.containers.get(container_name)
                result['container_id'] = container.id
                result['container_name'] = container.name
            else:
                error_msg = 'Either container_id or container_name must be provided'
                logger.error(error_msg)
                result.update({
                    'message': error_msg,
                    'error': error_msg,
                    'error_type': 'ValidationError'
                })
                return result
        except docker.errors.NotFound as e:
            error_msg = f'Container not found: {container_id or container_name}'
            logger.error(error_msg, exc_info=True)
            result.update({
                'message': error_msg,
                'error': str(e),
                'error_type': 'ContainerNotFound',
                'removed': False
            })
            return result
            
        # Log the removal request
        logger.info(
            'Removing container %s (ID: %s) with force=%s, remove_volumes=%s, remove_links=%s',
            container.name, container.id[:12], force, remove_volumes, remove_links
        )
        
        # Get container state before removal
        container.reload()
        result.update({
            'state_before_removal': container.status,
            'status_before_removal': container.attrs.get('State', {}).get('Status', '')
        })
        
        # Validate container state if requested
        if validate and container.status == 'running' and not force:
            error_msg = 'Cannot remove running container. Use force=True to force removal.'
            logger.warning(error_msg)
            result.update({
                'message': error_msg,
                'error': error_msg,
                'error_type': 'ContainerRunning',
                'removed': False
            })
            return result
        
        # Stop the container if it's running and force is False
        if container.status == 'running' and not force:
            logger.info('Stopping container %s before removal...', container.id[:12])
            try:
                container.stop(timeout=timeout)
                # Wait for container to stop
                start_time = time.time()
                while time.time() - start_time < timeout:
                    container.reload()
                    if container.status == 'exited':
                        break
                    time.sleep(check_interval)
                else:
                    if not force:
                        error_msg = f'Timeout waiting for container {container.id[:12]} to stop'
                        logger.error(error_msg)
                        result.update({
                            'message': error_msg,
                            'error': error_msg,
                            'error_type': 'StopTimeout',
                            'removed': False
                        })
                        return result
                    logger.warning('Forcing container stop due to timeout')
            except Exception as e:
                if not force:
                    error_msg = f'Error stopping container before removal: {str(e)}'
                    logger.error(error_msg, exc_info=True)
                    result.update({
                        'message': 'Failed to stop container before removal',
                        'error': str(e),
                        'error_type': 'StopError',
                        'removed': False
                    })
                    return result
                logger.warning('Error stopping container, but continuing with force removal')
        
        # Get volumes to be removed if requested
        if remove_volumes:
            try:
                mounts = container.attrs.get('Mounts', [])
                result['removed_volumes'] = [
                    m['Name'] for m in mounts 
                    if m.get('Type') == 'volume' and m.get('Name')
                ]
                if result['removed_volumes']:
                    logger.info(
                        'Will remove volumes: %s', 
                        ', '.join(result['removed_volumes'])
                    )
            except Exception as e:
                warning_msg = f'Failed to get volume information: {str(e)}'
                logger.warning(warning_msg, exc_info=True)
                result['warnings'].append(warning_msg)
        
        # Remove the container
        try:
            container.remove(
                force=force,
                v=remove_volumes,
                link=remove_links
            )
            result.update({
                'success': True,
                'message': f'Container {container.name} removed successfully',
                'removed': True,
                'removed_at': datetime.utcnow().isoformat()
            })
            
            logger.info(
                'Successfully removed container %s (ID: %s)',
                container.name, container.id[:12]
            )
            
            return result
            
        except docker.errors.APIError as e:
            error_msg = f'Docker API error while removing container: {str(e)}'
            logger.error(error_msg, exc_info=True)
            result.update({
                'message': 'Failed to remove container due to Docker API error',
                'error': str(e),
                'error_type': 'DockerAPIError',
                'removed': False
            })
            return result
            
    except docker.errors.NotFound as e:
        error_msg = f'Container not found during removal: {container_id or container_name}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': error_msg,
            'error': str(e),
            'error_type': 'ContainerNotFound',
            'removed': False
        })
        return result
        
    except docker.errors.APIError as e:
        error_msg = f'Docker API error: {str(e)}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': 'Failed to remove container due to Docker API error',
            'error': str(e),
            'error_type': 'DockerAPIError',
            'removed': False
        })
        return result
        
    except Exception as e:
        error_msg = f'Unexpected error removing container: {str(e)}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': 'Failed to remove container due to an unexpected error',
            'error': str(e),
            'error_type': 'UnexpectedError',
            'removed': False
        })
        return result

@Tool(
    name="get_container_logs",
    description="Fetch and stream logs from a container with advanced filtering options",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to get logs from (mutually exclusive with container_name)",
                "default": None
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container to get logs from (mutually exclusive with container_id)",
                "default": None
            },
            "follow": {
                "type": "boolean",
                "description": "Follow log output (like tail -f)",
                "default": False
            },
            "stdout": {
                "type": "boolean",
                "description": "Return logs from stdout",
                "default": True
            },
            "stderr": {
                "type": "boolean",
                "description": "Return logs from stderr",
                "default": True
            },
            "since": {
                "type": "string",
                "description": "Show logs since a timestamp (e.g., 2013-01-02T13:23:37) or relative (e.g., 42m for 42 minutes)",
                "default": None
            },
            "until": {
                "type": "string",
                "description": "Show logs before a timestamp or relative time",
                "default": None
            },
            "timestamps": {
                "type": "boolean",
                "description": "Add timestamps to every log line",
                "default": False
            },
            "tail": {
                "type": ["integer", "string"],
                "description": "Number of lines to show from the end of the logs, or 'all' for all logs",
                "default": "all"
            },
            "details": {
                "type": "boolean",
                "description": "Show extra details provided to logs (e.g., --details in docker logs)",
                "default": False
            },
            "max_size": {
                "type": "integer",
                "description": "Maximum number of bytes to return (approximate)",
                "default": 1048576,  # 1MB
                "minimum": 1,
                "maximum": 10485760  # 10MB
            },
            "stream": {
                "type": "boolean",
                "description": "Stream logs as they are generated (for follow mode)",
                "default": False
            },
            "filter": {
                "type": "string",
                "description": "Filter logs by a search term (case-insensitive)",
                "default": None
            },
            "timezone": {
                "type": "string",
                "description": "Timezone for timestamps (e.g., 'UTC', 'America/New_York')",
                "default": "UTC"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ],
        "additionalProperties": False
    },
    "container_id": {"type": "string"},
            "container_name": {"type": "string"},
            "logs": {
                "type": ["string", "array"],
                "description": "Log lines as a string (if not streaming) or array of log entries (if streaming)",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string", "format": "date-time"},
                        "stream": {"type": "string", "enum": ["stdout", "stderr"]},
                        "line": {"type": "string"}
                    },
                    "required": ["line"]
                }
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "line_count": {"type": "integer"},
                    "first_timestamp": {"type": ["string", "null"], "format": "date-time"},
                    "last_timestamp": {"type": ["string", "null"], "format": "date-time"},
                    "bytes_read": {"type": "integer"},
                    "streams": {
                        "type": "object",
                        "properties": {
                            "stdout": {"type": "boolean"},
                            "stderr": {"type": "boolean"}
                        }
                    },
                    "truncated": {"type": "boolean"}
                }
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "container_id", "container_name"],
        "additionalProperties": False
    },
    examples=[
        {
            "container_id": "a1b2c3d4e5f6",
            "tail": 100,
            "timestamps": True
        },
        {
            "container_name": "web-app",
            "follow": True,
            "filter": "ERROR",
            "timezone": "UTC"
        }
    ]
)
async def get_container_logs(
    container_id: Optional[str] = None,
    container_name: Optional[str] = None,
    follow: bool = False,
    stdout: bool = True,
    stderr: bool = True,
    since: Optional[str] = None,
    until: Optional[str] = None,
    timestamps: bool = False,
    tail: Union[int, str] = "all",
    details: bool = False,
    max_size: int = 1048576,
    stream: bool = False,
    filter: Optional[str] = None,
    timezone: str = "UTC"
) -> Dict[str, Any]:
    """
    Fetch container logs with advanced filtering and formatting options.
    
    This function retrieves logs from a container with support for filtering by time,
    log level, and content, as well as real-time log following.
    
    Args:
        container_id: ID of the container to get logs from
        container_name: Name of the container to get logs from
        follow: Follow log output (like tail -f)
        stdout: Include stdout logs
        stderr: Include stderr logs
        since: Show logs since a timestamp or relative time
        until: Show logs before a timestamp or relative time
        timestamps: Add timestamps to every log line
        tail: Number of lines to show from the end or 'all'
        details: Show extra details provided to logs
        max_size: Maximum number of bytes to return (approximate)
        stream: Stream logs as they are generated (for follow mode)
        filter: Filter logs by a search term (case-insensitive)
        timezone: Timezone for timestamps
        
    Returns:
        Dictionary containing log data and metadata
    """
    from datetime import datetime, timezone as tz
    import re
    import pytz
    from typing import Dict, Any, Optional, Union, List, Generator, AsyncGenerator
    
    # Initialize result dictionary
    result: Dict[str, Any] = {
        'success': False,
        'container_id': '',
        'container_name': '',
        'logs': [],
        'metadata': {
            'line_count': 0,
            'first_timestamp': None,
            'last_timestamp': None,
            'bytes_read': 0,
            'streams': {
                'stdout': stdout,
                'stderr': stderr
            },
            'truncated': False
        },
        'warnings': []
    }
    
    # Get Docker client
    client = container_mgr.client
    
    try:
        # Get container by ID or name
        try:
            if container_id:
                container = client.containers.get(container_id)
            elif container_name:
                container = client.containers.get(container_name)
            else:
                error_msg = 'Either container_id or container_name must be provided'
                logger.error(error_msg)
                result.update({
                    'message': error_msg,
                    'error': error_msg,
                    'error_type': 'ValidationError',
                    'success': False
                })
                return result
                
            result['container_id'] = container.id
            result['container_name'] = container.name
            
        except Exception as e:
            error_msg = f'Container not found: {container_id or container_name}'
            logger.error(error_msg, exc_info=True)
            result.update({
                'message': error_msg,
                'error': str(e),
                'error_type': 'ContainerNotFound',
                'success': False
            })
            return result
            
        # Log the request
        logger.info(
            'Fetching logs for container %s (ID: %s), follow=%s, tail=%s',
            container.name, container.id[:12], follow, tail
        )
        
        # Prepare log fetching parameters
        log_params: Dict[str, Any] = {
            'stdout': stdout,
            'stderr': stderr,
            'follow': follow,
            'timestamps': timestamps,
            'details': details,
            'tail': str(tail) if isinstance(tail, int) else tail,
            'since': since,
            'until': until,
            'stream': stream or follow
        }
        
        # Filter out None values
        log_params = {k: v for k, v in log_params.items() if v is not None}
        
        try:
            # Get logs from container
            logs = container.logs(**log_params)
            
            # Process logs based on streaming mode
            if stream or follow:
                # For streaming logs, return a generator
                async def log_generator() -> AsyncGenerator[Dict[str, Any], None]:
                    try:
                        for log_chunk in logs:
                            if not log_chunk:
                                continue
                                
                            # Process log chunk
                            log_entry = _process_log_chunk(
                                log_chunk,
                                timestamps,
                                timezone,
                                filter
                            )
                            
                            if log_entry:
                                yield log_entry
                                
                                # Update metadata
                                result['metadata']['line_count'] += 1
                                result['metadata']['bytes_read'] += len(log_chunk)
                                
                                # Update timestamps
                                if 'timestamp' in log_entry:
                                    ts = log_entry['timestamp']
                                    if not result['metadata']['first_timestamp']:
                                        result['metadata']['first_timestamp'] = ts
                                    result['metadata']['last_timestamp'] = ts
                                    
                    except Exception as e:
                        error_msg = f'Error streaming logs: {str(e)}'
                        logger.error(error_msg, exc_info=True)
                        yield {
                            'error': error_msg,
                            'error_type': 'LogStreamError'
                        }
                
                result['success'] = True
                result['message'] = 'Streaming logs started'
                result['logs'] = log_generator()
                
            else:
                # For non-streaming logs, process all at once
                log_entries = []
                first_ts = None
                last_ts = None
                
                for log_chunk in logs:
                    if not log_chunk:
                        continue
                        
                    log_entry = _process_log_chunk(
                        log_chunk,
                        timestamps,
                        timezone,
                        filter
                    )
                    
                    if log_entry:
                        log_entries.append(log_entry)
                        
                        # Update metadata
                        result['metadata']['bytes_read'] += len(log_chunk)
                        
                        # Update timestamps
                        if 'timestamp' in log_entry:
                            ts = log_entry['timestamp']
                            if first_ts is None:
                                first_ts = ts
                            last_ts = ts
                
                # Update result with processed logs
                result.update({
                    'success': True,
                    'message': f'Retrieved {len(log_entries)} log entries',
                    'logs': log_entries,
                    'metadata': {
                        **result['metadata'],
                        'line_count': len(log_entries),
                        'first_timestamp': first_ts,
                        'last_timestamp': last_ts,
                        'truncated': result['metadata']['bytes_read'] >= max_size
                    }
                })
                
                # Apply max size limit
                if result['metadata']['bytes_read'] >= max_size:
                    result['warnings'].append(
                        f'Logs truncated at {max_size} bytes. Use filters or pagination for more logs.'
                    )
            
            return result
            
        except Exception as e:
            error_msg = f'Docker API error while fetching logs: {str(e)}'
            logger.error(error_msg, exc_info=True)
            result.update({
                'message': 'Failed to fetch logs due to Docker API error',
                'error': str(e),
                'error_type': 'DockerAPIError',
                'success': False
            })
            return result
            
    except Exception as e:
        error_msg = f'Unexpected error fetching container logs: {str(e)}'
        logger.error(error_msg, exc_info=True)
        result.update({
            'message': 'Failed to fetch logs due to an unexpected error',
            'error': str(e),
            'error_type': 'UnexpectedError',
            'success': False
        })
        return result

def _process_log_chunk(
    log_chunk: bytes,
    include_timestamps: bool = False,
    timezone: str = 'UTC',
    filter_term: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Process a single log chunk into a structured format.
    
    Args:
        log_chunk: Raw log chunk bytes
        include_timestamps: Whether to include timestamps in the output
        timezone: Timezone for timestamps
        filter_term: Optional term to filter logs by
        
    Returns:
        Structured log entry or None if filtered out
    """
    try:
        # Decode the log chunk
        log_line = log_chunk.decode('utf-8', errors='replace').strip()
        
        # Skip empty lines
        if not log_line:
            return None
            
        # Parse timestamp if present
        timestamp = None
        log_content = log_line
        
        # Try to extract timestamp (format: 2023-01-01T12:00:00.000000Z )
        ts_match = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+', log_line)
        if ts_match:
            timestamp = ts_match.group(1)
            log_content = log_line[ts_match.end():]
            
            # Normalize timezone if needed
            try:
                tz_obj = pytz.timezone(timezone)
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                timestamp = dt.astimezone(tz_obj).isoformat()
            except (ValueError, pytz.exceptions.UnknownTimeZoneError) as e:
                logger.warning(f'Failed to parse timestamp {timestamp}: {str(e)}')
        
        # Determine stream type (stdout/stderr)
        stream = 'stderr' if log_line.startswith('stderr') else 'stdout'
        
        # Apply content filter if specified
        if filter_term and filter_term.lower() not in log_content.lower():
            return None
            
        # Build result entry
        entry = {
            'line': log_content,
            'stream': stream
        }
        
        if timestamp and include_timestamps:
            entry['timestamp'] = timestamp
            
        return entry
        
    except Exception as e:
        logger.error(f'Error processing log chunk: {str(e)}', exc_info=True)
        return {
            'line': f'[Error processing log line: {str(e)}]',
            'stream': 'stderr',
            'error': str(e)
        }

@Tool(
    name="prune_containers",
    description="Remove all stopped containers and free up disk space",
    parameters={
        "type": "object",
        "properties": {
            "filters": {
                "type": "object",
                "description": "Filter output based on conditions provided",
                "properties": {
                    "until": {
                        "type": "string",
                        "description": "Prune containers created before this timestamp"
                    },
                    "label": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Prune containers with (or without, if label is prefixed with !) the specified labels"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["created", "restarting", "running", "removing", "paused", "exited", "dead"],
                        "description": "Prune containers with the specified status"
                    },
                    "is-task": {
                        "type": "boolean",
                        "description": "Filter tasks (swarm mode)"
                    }
                }
            },
            "force": {
                "type": "boolean",
                "default": False,
                "description": "Do not prompt for confirmation"
            },
            "remove_volumes": {
                "type": "boolean",
                "default": False,
                "description": "Prune volumes associated with the containers"
            },
            "remove_networks": {
                "type": "boolean",
                "default": False,
                "description": "Prune networks associated with the containers"
            }
        }
    },
    "message": {"type": "string"},
            "prune_result": {
                "type": "object",
                "properties": {
                    "containers_deleted": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "space_reclaimed": {
                        "type": "integer",
                        "description": "Disk space reclaimed in bytes"
                    },
                    "volumes_deleted": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "networks_deleted": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["containers_deleted", "space_reclaimed"]
            },
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "message"]
    },
    examples=[
        {
            "name": "Prune all stopped containers",
            "input": {
                "force": True
            },
            "output": {
                "success": True,
                "message": "Successfully pruned 3 containers",
                "prune_result": {
                    "containers_deleted": [
                        "a1b2c3d4e5f6",
                        "b2c3d4e5f6g7",
                        "c3d4e5f6g7h8"
                    ],
                    "space_reclaimed": 524288000,
                    "volumes_deleted": [],
                    "networks_deleted": []
                }
            }
        },
        {
            "name": "Prune containers older than 1 week with volumes",
            "input": {
                "filters": {
                    "until": "168h"
                },
                "remove_volumes": True,
                "force": True
            },
            "output": {
                "success": True,
                "message": "Successfully pruned 5 containers and their volumes",
                "prune_result": {
                    "containers_deleted": [
                        "d4e5f6g7h8i9",
                        "e5f6g7h8i9j0"
                    ],
                    "space_reclaimed": 1073741824,
                    "volumes_deleted": [
                        "vol1",
                        "vol2"
                    ],
                    "networks_deleted": []
                }
            }
        }
    ]
)
async def prune_containers(
    request: PruneContainersRequest
) -> Dict[str, Any]:
    """Remove all stopped containers and free up disk space."""
    try:
        # Build the prune command
        cmd = ['prune', '--force']
        if request.filters:
            for key, value in request.filters.items():
                cmd.extend(['--filter', f"{key}={value}"])
        
        # Execute the prune command
        result = run_docker_command('container', cmd, format_json=True)
        
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": "Failed to parse prune results"
            }
            
        return {
            "success": True,
            "containers_deleted": result.get("ContainersDeleted", []),
            "space_reclaimed": result.get("SpaceReclaimed", 0),
            "message": f"Successfully pruned {len(result.get('ContainersDeleted', []))} containers"
        }
    except Exception as e:
        return handle_error(e, "prune_containers")

@Tool(
    name="exec_command",
    description="Execute a command in a running container",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID or name of the container"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container (alternative to container_id)"
            },
            "command": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command to execute and its arguments as an array"
            },
            "detach": {
                "type": "boolean",
                "default": False,
                "description": "Run command in the background (detached mode)"
            },
            "environment": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Environment variables to set in the container (key-value pairs)"
            },
            "tty": {
                "type": "boolean",
                "default": True,
                "description": "Allocate a pseudo-TTY"
            },
            "interactive": {
                "type": "boolean",
                "default": True,
                "description": "Keep STDIN open even if not attached"
            },
            "workdir": {
                "type": "string",
                "description": "Working directory inside the container"
            },
            "user": {
                "type": "string",
                "description": "Username or UID (format: <name|uid>[:<group|gid>])"
            },
            "privileged": {
                "type": "boolean",
                "default": False,
                "description": "Give extended privileges to the command"
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "default": 60,
                "description": "Command execution timeout in seconds"
            }
        },
        "oneOf": [
            {"required": ["container_id", "command"]},
            {"required": ["container_name", "command"]}
        ]
    },
    "exit_code": {"type": "integer"},
            "output": {"type": "string"},
            "error": {"type": "string"},
            "exec_id": {"type": "string"},
            "container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": ["id", "name"]
            },
            "execution_time": {"type": "number", "format": "float"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "exit_code"]
    },
    examples=[
        {
            "name": "Run a simple command",
            "input": {
                "container_id": "a1b2c3d4e5f6",
                "command": ["ls", "-la", "/app"]
            },
            "output": {
                "success": True,
                "exit_code": 0,
                "output": "total 16\ndrwxr-xr-x 1 root root 4096 Jan  1 12:00 .\ndrwxr-xr-x 1 root root 4096 Jan  1 12:00 ..\n-rw-r--r-- 1 root root  220 Jan  1 12:00 app.py",
                "execution_time": 0.123,
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "web-app"
                }
            }
        },
        {
            "name": "Run a command with environment variables",
            "input": {
                "container_name": "database",
                "command": ["sh", "-c", "echo $DB_NAME && echo $DB_USER"],
                "environment": {
                    "DB_NAME": "mydb",
                    "DB_USER": "admin"
                },
                "workdir": "/data",
                "user": "postgres"
            },
            "output": {
                "success": True,
                "exit_code": 0,
                "output": "mydb\nadmin\n",
                "execution_time": 0.234,
                "container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "database"
                }
            }
        },
        {
            "name": "Run a long-running command in detached mode",
            "input": {
                "container_id": "c3d4e5f6g7h8",
                "command": ["python", "background_task.py"],
                "detach": True,
                "environment": {
                    "LOG_LEVEL": "DEBUG"
                }
            },
            "output": {
                "success": True,
                "exit_code": 0,
                "exec_id": "x1y2z3a4b5c6",
                "container": {
                    "id": "c3d4e5f6g7h8",
                    "name": "worker"
                },
                "message": "Command started in detached mode with exec ID: x1y2z3a4b5c6"
            }
        }
    ]
)
async def exec_command(
    request: ExecCommandRequest
) -> Dict[str, Any]:
    """Execute a command in a running container."""
    try:
        # Build the exec command with options
        cmd = ['exec']
        
        if request.user:
            cmd.extend(['--user', request.user])
        if request.workdir:
            cmd.extend(['--workdir', request.workdir])
        if request.detach:
            cmd.append('--detach')
        if request.tty:
            cmd.append('--tty')
        if request.privileged:
            cmd.append('--privileged')
            
        # Add environment variables if any
        if request.environment:
            for key, value in request.environment.items():
                cmd.extend(['-e', f"{key}={value}"])
                
        # Add container and command
        cmd.append(request.container_id)
        
        # Handle command (can be string or list)
        if isinstance(request.command, str):
            cmd.extend(['sh', '-c', request.command])
        else:
            cmd.extend(request.command)
            
        # Execute the command
        result = run_docker_command('container', cmd, format_json=False)
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "container_id": request.container_id
        }
    except Exception as e:
        return handle_error(e, "exec_command")

@Tool(
    name="inspect_container",
    description="Get detailed information about a container including configuration, state, and network settings",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to inspect"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container (alternative to container_id)"
            },
            "size": {
                "type": "boolean",
                "default": False,
                "description": "Include container size information (adds significant overhead)"
            },
            "format": {
                "type": "string",
                "enum": ["json", "yaml", "table"],
                "default": "json",
                "description": "Output format for the inspection data"
            },
            "include_network": {
                "type": "boolean",
                "default": True,
                "description": "Include detailed network configuration"
            },
            "include_volumes": {
                "type": "boolean",
                "default": True,
                "description": "Include volume mounts information"
            },
            "include_environment": {
                "type": "boolean",
                "default": True,
                "description": "Include environment variables"
            },
            "include_ports": {
                "type": "boolean",
                "default": True,
                "description": "Include port mappings"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ]
    },
    "container": {
                "type": "object",
                "description": "Container inspection data",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "state": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["running", "paused", "restarting", "removing", "exited", "dead", "created"]},
                            "running": {"type": "boolean"},
                            "paused": {"type": "boolean"},
                            "restarting": {"type": "boolean"},
                            "oom_killed": {"type": "boolean"},
                            "dead": {"type": "boolean"},
                            "pid": {"type": "integer"},
                            "exit_code": {"type": "integer"},
                            "started_at": {"type": "string", "format": "date-time"},
                            "finished_at": {"type": "string", "format": "date-time"}
                        },
                        "required": ["status", "running", "paused", "restarting"]
                    },
                    "config": {"type": "object"},
                    "host_config": {"type": "object"},
                    "network_settings": {"type": "object"},
                    "mounts": {"type": "array", "items": {"type": "object"}},
                    "size_rw": {"type": "integer", "description": "Size of files that have been created or changed"},
                    "size_root_fs": {"type": "integer", "description": "Total size of all files in the container"}
                },
                "required": ["id", "name", "state"]
            },
            "message": {"type": "string"},
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success"]
    },
    examples=[
        {
            "name": "Inspect a container by ID",
            "input": {
                "container_id": "a1b2c3d4e5f6",
                "size": True
            },
            "output": {
                "success": True,
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "web-app",
                    "state": {
                        "status": "running",
                        "running": True,
                        "paused": False,
                        "restarting": False,
                        "oom_killed": False,
                        "dead": False,
                        "pid": 1234,
                        "exit_code": 0,
                        "started_at": "2023-01-01T12:00:00Z"
                    },
                    "config": {
                        "image": "nginx:latest",
                        "env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
                        "cmd": ["nginx", "-g", "daemon off;"],
                        "working_dir": "/app"
                    },
                    "size_rw": 1024,
                    "size_root_fs": 2048
                },
                "message": "Container details retrieved successfully"
            }
        },
        {
            "name": "Inspect a container by name with minimal details",
            "input": {
                "container_name": "database",
                "include_network": False,
                "include_volumes": False
            },
            "output": {
                "success": True,
                "container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "database",
                    "state": {
                        "status": "running",
                        "running": True,
                        "paused": False,
                        "restarting": False
                    },
                    "config": {
                        "image": "postgres:13",
                        "env": ["POSTGRES_PASSWORD=secret"],
                        "cmd": ["postgres"]
                    }
                },
                "message": "Container details retrieved successfully"
            }
        }
    ]
)
async def inspect_container(
    request: InspectContainerRequest
) -> Dict[str, Any]:
    """Get detailed information about a container."""
    try:
        # Execute the inspect command
        result = run_docker_command(
            'inspect',
            [request.container_id],
            format_json=True
        )
        
        if not result:
            return {
                "success": False,
                "error": f"Container {request.container_id} not found",
                "container_id": request.container_id
            }
            
        # If we got a list, take the first item (should be the container)
        container_info = result[0] if isinstance(result, list) else result
        
        return {
            "success": True,
            "container": container_info,
            "container_id": request.container_id,
            "message": "Container details retrieved successfully"
        }
    except Exception as e:
        return handle_error(e, "inspect_container")

@Tool(
    name="container_stats",
    description="Get real-time container resource usage statistics including CPU, memory, network, and block I/O metrics",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to get stats for"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container (alternative to container_id)"
            },
            "stream": {
                "type": "boolean",
                "default": False,
                "description": "Stream stats continuously (default: single snapshot)"
            },
            "interval": {
                "type": "integer",
                "minimum": 1,
                "default": 1,
                "description": "Interval in seconds between stats updates (min: 1s)"
            },
            "format": {
                "type": "string",
                "enum": ["json", "table"],
                "default": "json",
                "description": "Output format for the stats data"
            },
            "include_network": {
                "type": "boolean",
                "default": True,
                "description": "Include network I/O statistics"
            },
            "include_disk": {
                "type": "boolean",
                "default": True,
                "description": "Include disk I/O statistics"
            },
            "include_memory": {
                "type": "boolean",
                "default": True,
                "description": "Include memory usage statistics"
            },
            "include_cpu": {
                "type": "boolean",
                "default": True,
                "description": "Include CPU usage statistics"
            },
            "human_readable": {
                "type": "boolean",
                "default": True,
                "description": "Show sizes in human-readable format (e.g., 1K, 2M, 3G)"
            },
            "max_samples": {
                "type": "integer",
                "minimum": 1,
                "description": "Maximum number of samples to collect (only when stream=True)"
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "default": 30,
                "description": "Maximum time in seconds to collect stats (only when stream=True)"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ]
    },
    "container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "read_time": {"type": "string", "format": "date-time"}
                },
                "required": ["id", "name"]
            },
            "cpu": {
                "type": "object",
                "properties": {
                    "usage_percent": {"type": "number", "format": "float"},
                    "total_usage": {"type": "integer"},
                    "system_cpu_usage": {"type": "integer"},
                    "online_cpus": {"type": "integer"},
                    "throttling_data": {"type": "object"}
                }
            },
            "memory": {
                "type": "object",
                "properties": {
                    "usage": {"type": "integer"},
                    "max_usage": {"type": "integer"},
                    "limit": {"type": "integer"},
                    "usage_percent": {"type": "number", "format": "float"},
                    "stats": {"type": "object"}
                }
            },
            "network": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "rx_bytes": {"type": "integer"},
                        "rx_packets": {"type": "integer"},
                        "rx_errors": {"type": "integer"},
                        "rx_dropped": {"type": "integer"},
                        "tx_bytes": {"type": "integer"},
                        "tx_packets": {"type": "integer"},
                        "tx_errors": {"type": "integer"},
                        "tx_dropped": {"type": "integer"}
                    }
                }
            },
            "block_io": {
                "type": "object",
                "properties": {
                    "read": {"type": "integer"},
                    "write": {"type": "integer"},
                    "total": {"type": "integer"}
                }
            },
            "pids": {"type": "integer"},
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "container"]
    },
    examples=[
        {
            "name": "Get a single stats snapshot for a container by ID",
            "input": {
                "container_id": "a1b2c3d4e5f6"
            },
            "output": {
                "success": true,
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "web-app",
                    "read_time": "2023-01-01T12:00:00Z"
                },
                "cpu": {
                    "usage_percent": 12.34,
                    "total_usage": 123456789,
                    "system_cpu_usage": 1000000000,
                    "online_cpus": 4,
                    "throttling_data": {}
                },
                "memory": {
                    "usage": 25690112,
                    "max_usage": 51290112,
                    "limit": 1073741824,
                    "usage_percent": 2.4,
                    "stats": {
                        "cache": 12345678,
                        "rss": 12345678
                    }
                },
                "network": {
                    "eth0": {
                        "rx_bytes": 1234,
                        "tx_bytes": 5678,
                        "rx_packets": 10,
                        "tx_packets": 12,
                        "rx_errors": 0,
                        "tx_errors": 0,
                        "rx_dropped": 0,
                        "tx_dropped": 0
                    }
                },
                "block_io": {
                    "read": 123456,
                    "write": 78901,
                    "total": 202357
                },
                "pids": 5
            }
        },
        {
            "name": "Stream stats with custom interval and limit",
            "input": {
                "container_name": "database",
                "stream": true,
                "interval": 5,
                "max_samples": 3,
                "include_network": false
            },
            "output": {
                "success": true,
                "container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "database",
                    "read_time": "2023-01-01T12:00:00Z"
                },
                "cpu": {
                    "usage_percent": 45.67,
                    "total_usage": 987654321,
                    "system_cpu_usage": 2000000000,
                    "online_cpus": 8
                },
                "memory": {
                    "usage": 536870912,
                    "limit": 2147483648,
                    "usage_percent": 25.0
                },
                "block_io": {
                    "read": 987654,
                    "write": 123456,
                    "total": 1111110
                },
                "pids": 12
            }
        }
    ]
)
async def container_stats(
    request: ContainerStatsRequest
) -> Dict[str, Any]:
    """Get real-time container resource usage statistics."""
    try:
        # Build the stats command
        cmd = ['stats', '--no-stream'] if not request.stream else ['stats']
        cmd.append(request.container_id)
        cmd.append('--format')
        cmd.append('json')
        
        if request.stream:
            # For streaming, we need to handle this differently
            # as run_docker_command is not designed for streaming
            # For now, we'll just get a single snapshot
            cmd = ['stats', '--no-stream', '--format', 'json', request.container_id]
        
        # Execute the stats command
        result = run_docker_command('container', cmd, format_json=True)
        
        if not result:
            return {
                "success": False,
                "error": f"Could not get stats for container {request.container_id}",
                "container_id": request.container_id
            }
            
        # Format the stats response
        stats = result[0] if isinstance(result, list) else result
        
        # Calculate memory usage percentage
        memory_usage = stats.get('memory_stats', {}).get('usage', 0)
        memory_limit = stats.get('memory_stats', {}).get('limit', 1)  # Avoid division by zero
        memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
        
        # Calculate CPU percentage (this is a simplified version)
        cpu_delta = 0.0
        system_cpu_delta = 0.0
        cpu_percent = 0.0
        
        cpu_stats = stats.get('cpu_stats', {})
        precpu_stats = stats.get('precpu_stats', {})
        
        if cpu_stats and precpu_stats:
            cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                       precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
            system_cpu_delta = cpu_stats.get('system_cpu_usage', 0) - \
                             precpu_stats.get('system_cpu_usage', 0)
            
            if system_cpu_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_cpu_delta) * cpu_stats.get('online_cpus', 1) * 100
        
        response = {
            "success": True,
            "container_id": request.container_id,
            "name": stats.get('name', '').lstrip('/'),
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage": memory_usage,
            "memory_limit": memory_limit,
            "memory_percent": round(memory_percent, 2),
            "network_io": stats.get('networks', {}),
            "block_io": stats.get('blkio_stats', {}),
            "pids": stats.get('pids_stats', {}).get('current', 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
    except Exception as e:
        return handle_error(e, "container_stats")

@Tool(
    name="container_top",
    description="Display the running processes of a container",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to inspect"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container (alternative to container_id)"
            },
            "ps_args": {
                "type": "string",
                "default": "-ef",
                "description": "Arguments to pass to the ps command (default: '-ef' for full format)"
            },
            "format": {
                "type": "string",
                "enum": ["json", "table", "list"],
                "default": "json",
                "description": "Output format for the process list"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ]
    },
    "container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": ["id", "name"]
            },
            "processes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "uid": {"type": "string"},
                        "pid": {"type": "integer"},
                        "ppid": {"type": "integer"},
                        "c": {"type": "integer"},
                        "stime": {"type": "string"},
                        "tty": {"type": "string"},
                        "time": {"type": "string"},
                        "cmd": {"type": "string"}
                    }
                }
            },
            "titles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Column titles for the process list"
            },
            "message": {"type": "string"},
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "container"]
    },
    examples=[
        {
            "name": "Get process list for a container by ID",
            "input": {
                "container_id": "a1b2c3d4e5f6",
                "ps_args": "aux"
            },
            "output": {
                "success": true,
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "web-app"
                },
                "titles": ["USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "TTY", "STAT", "START", "TIME", "COMMAND"],
                "processes": [
                    {
                        "USER": "root",
                        "PID": 1,
                        "%CPU": 0.5,
                        "%MEM": 2.1,
                        "VSZ": "123456",
                        "RSS": "12345",
                        "TTY": "?",
                        "STAT": "Ss",
                        "START": "12:00",
                        "TIME": "0:00",
                        "COMMAND": "/usr/sbin/nginx -g 'daemon off;'"
                    },
                    {
                        "USER": "www-data",
                        "PID": 10,
                        "%CPU": 0.1,
                        "%MEM": 0.5,
                        "VSZ": "23456",
                        "RSS": "2345",
                        "TTY": "?",
                        "STAT": "S",
                        "START": "12:01",
                        "TIME": "0:00",
                        "COMMAND": "php-fpm"
                    }
                ],
                "message": "Process list retrieved successfully"
            }
        },
        {
            "name": "Get process list for a container by name with default ps args",
            "input": {
                "container_name": "database"
            },
            "output": {
                "success": true,
                "container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "database"
                },
                "titles": ["UID", "PID", "PPID", "C", "STIME", "TTY", "TIME", "CMD"],
                "processes": [
                    {
                        "UID": "postgres",
                        "PID": 1,
                        "PPID": 0,
                        "C": 0,
                        "STIME": "12:00",
                        "TTY": "?",
                        "TIME": "00:00:01",
                        "CMD": "postgres"
                    },
                    {
                        "UID": "postgres",
                        "PID": 10,
                        "PPID": 1,
                        "C": 0,
                        "STIME": "12:00",
                        "TTY": "?",
                        "TIME": "00:00:00",
                        "CMD": "postgres: checkpointer"
                    }
                ],
                "message": "Process list retrieved successfully"
            }
        }
    ]
)
async def container_top(
    container_id: Optional[str] = None,
    container_name: Optional[str] = None,
    ps_args: str = "-ef",
    format: str = "json"
) -> Dict[str, Any]:
    """Display the running processes of a container.
    
    Args:
        container_id: The ID of the container to inspect
        container_name: The name of the container (alternative to container_id)
        ps_args: Arguments to pass to the ps command (default: '-ef' for full format)
        format: Output format (json, table, or list)
        
    Returns:
        Dict containing container process information
    """
    try:
        # Resolve container ID if name is provided
        container_identifier = container_id or container_name
        if not container_identifier:
            return {
                "success": False,
                "error": "Either container_id or container_name must be provided"
            }
            
        # Build the top command
        cmd = ['top', container_identifier, ps_args]
        
        # Execute the top command
        result = run_docker_command('container', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"Failed to get process list for container {container_identifier}",
                "container_id": container_id,
                "container_name": container_name
            }
            
        # Parse the output
        lines = result.stdout.strip().split('\n')
        if not lines:
            return {
                "success": False,
                "error": "No output from top command",
                "container_id": container_id,
                "container_name": container_name
            }
            
        # The first line contains the headers
        headers = [h.strip() for h in lines[0].split()]
        
        # The rest are the processes
        processes = []
        for line in lines[1:]:
            if not line.strip():
                continue
                
            # Split the line while preserving quoted strings
            parts = []
            current = ""
            in_quotes = False
            
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ' ' and not in_quotes:
                    if current:
                        parts.append(current)
                        current = ""
                    continue
                else:
                    current += char
                    
            if current:
                parts.append(current)
                
            # Map parts to headers
            process = {}
            for i, header in enumerate(headers):
                if i < len(parts):
                    process[header] = parts[i].strip('"')
                else:
                    process[header] = ""
                    
            processes.append(process)
            
        # Get container name if we only had ID
        container_name_result = None
        if container_name is None:
            inspect_result = run_docker_command(
                'inspect',
                ['--format', '{{.Name}}', container_identifier],
                format_json=False
            )
            if inspect_result.returncode == 0:
                container_name = inspect_result.stdout.strip().lstrip('/')
        
        return {
            "success": True,
            "container": {
                "id": container_id or container_identifier,
                "name": container_name or container_identifier
            },
            "titles": headers,
            "processes": processes,
            "message": "Process list retrieved successfully"
        }
        
    except Exception as e:
        return handle_error(e, "container_top")

