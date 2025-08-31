"""
Container management tools for Docker MCP.

This module provides FastMCP 2.11.3 compatible tools for managing Docker containers.
"""
from typing import Dict, Any, Optional, List, Type, TypeVar, Generic, Union
from datetime import datetime
from pydantic import BaseModel
from fastmcp.tools import Tool
from fastmcp.types import Param, Return, Stream
from dockermcp.core.containers import ContainerManager
from dockermcp.utils import run_docker_command
from dockermcp.tools.containers.container_models import (
    ListContainersRequest, CreateContainerRequest, StartContainerRequest,
    StopContainerRequest, RestartContainerRequest, RemoveContainerRequest,
    GetContainerLogsRequest, ContainerResponse, ContainerInfo,
    PruneContainersRequest, PruneContainersResponse, ExecCommandRequest,
    ExecCommandResponse, InspectContainerRequest, ContainerDetails,
    ContainerStatsRequest, ContainerStatsResponse
)

# Type variables for request/response models
T = TypeVar('T', bound=BaseModel)

# Initialize container manager
import docker
container_mgr = ContainerManager(docker_client=docker.from_env())

def create_response(
    response_model: Type[T], 
    success: bool, 
    message: str, 
    **kwargs
) -> Dict[str, Any]:
    """
    Create a standardized response dictionary with proper JSON serialization.
    
    Args:
        response_model: The Pydantic model class for the response
        success: Whether the operation was successful
        message: Status message
        **kwargs: Additional fields to include in the response
        
    Returns:
        Dict containing the response data with proper JSON serialization
    """
    from datetime import datetime
    from pydantic import BaseModel
    
    def json_serializer(obj):
        """Custom JSON serializer for objects not serializable by default."""
        if isinstance(obj, (datetime, BaseModel)):
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        raise TypeError(f"Type {type(obj)} not JSON serializable")
    
    # Create base response
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add additional fields
    for key, value in kwargs.items():
        if value is not None:
            if hasattr(value, 'model_dump'):
                response[key] = value.model_dump()
            else:
                response[key] = value
    
    # If a response model is provided, validate the response
    if response_model and issubclass(response_model, BaseModel):
        try:
            return response_model(**response).model_dump()
        except Exception as e:
            logger.error(f"Error validating response with {response_model.__name__}: {e}")
            # Return unvalidated response but with proper serialization
            return json.loads(json.dumps(response, default=json_serializer))
    
    return response

def handle_error(error: Exception, context: str = "") -> Dict[str, Any]:
    """Handle errors consistently across all tools."""
    error_msg = f"Error in {context}: {str(error)}" if context else f"Error: {str(error)}"
    return {
        "success": False,
        "error": error_msg,
        "error_type": error.__class__.__name__
    }

@Tool(
    name="list_containers",
    description="List Docker containers with detailed status information",
    parameters={
        "type": "object",
        "properties": {
            "all_states": {
                "type": "boolean",
                "default": False,
                "description": "Show all containers including stopped ones (default: running only)"
            },
            "filters": {
                "type": "object",
                "additionalProperties": {"type": ["string", "array"]},
                "default": {},
                "description": "Filter containers by labels or other attributes"
            },
            "limit": {
                "type": ["integer", "null"],
                "minimum": 1,
                "default": None,
                "description": "Limit the number of containers to return"
            },
            "size": {
                "type": "boolean",
                "default": False,
                "description": "Include container size information"
            }
        },
        "required": []
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "containers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "names": {"type": "array", "items": {"type": "string"}},
                        "image": {"type": "string"},
                        "image_id": {"type": "string"},
                        "command": {"type": "string"},
                        "created": {"type": "integer"},
                        "ports": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ip": {"type": "string"},
                                    "private_port": {"type": "integer"},
                                    "public_port": {"type": ["integer", "null"]},
                                    "type": {"type": "string"}
                                }
                            }
                        },
                        "size_rw": {"type": ["integer", "null"]},
                        "size_root_fs": {"type": ["integer", "null"]},
                        "labels": {"type": "object"},
                        "state": {"type": "string"},
                        "status": {"type": "string"},
                        "host_config": {"type": "object"},
                        "network_settings": {"type": "object"},
                        "mounts": {"type": "array"}
                    },
                    "required": ["id", "names", "image", "state", "status"]
                }
            },
            "summary": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "running": {"type": "integer"},
                    "paused": {"type": "integer"},
                    "stopped": {"type": "integer"},
                    "created": {"type": "integer"},
                    "restarting": {"type": "integer"},
                    "removing": {"type": "integer"},
                    "dead": {"type": "integer"},
                    "exited": {"type": "integer"}
                },
                "required": ["total", "running", "paused", "stopped"]
            },
            "error": {"type": ["string", "null"]},
            "error_type": {"type": ["string", "null"]}
        },
        "required": ["success", "message", "containers", "summary"]
    },
    examples=[
        {
            "name": "List running containers",
            "input": {
                "all_states": False,
                "limit": 5,
                "size": True
            },
            "output": {
                "success": True,
                "message": "Successfully listed 3 containers",
                "containers": [
                    {
                        "id": "a1b2c3d4e5f6",
                        "names": ["/my-container-1"],
                        "image": "nginx:latest",
                        "image_id": "sha256:...",
                        "command": "nginx -g 'daemon off;'",
                        "created": 1609459200,
                        "ports": [{"private_port": 80, "public_port": 8080, "type": "tcp"}],
                        "size_rw": 0,
                        "size_root_fs": 1337,
                        "labels": {"com.example.vendor": "ACME"},
                        "state": "running",
                        "status": "Up 2 hours"
                    }
                ],
                "summary": {
                    "total": 3,
                    "running": 2,
                    "paused": 0,
                    "stopped": 1,
                    "created": 0,
                    "restarting": 0,
                    "removing": 0,
                    "dead": 0,
                    "exited": 1
                },
                "error": null,
                "error_type": null
            }
        },
        {
            "name": "List all containers with filters",
            "input": {
                "all_states": True,
                "filters": {
                    "status": ["running", "paused"],
                    "label": ["com.example.environment=production"]
                }
            },
            "output": {
                "success": True,
                "message": "Found 2 matching containers",
                "containers": [
                    {
                        "id": "x1y2z3a4b5c6",
                        "names": ["/production-app-1"],
                        "image": "myapp:1.0.0",
                        "image_id": "sha256:...",
                        "state": "running",
                        "status": "Up 5 days",
                        "labels": {
                            "com.example.environment": "production",
                            "com.example.service": "api"
                        }
                    }
                ],
                "summary": {
                    "total": 1,
                    "running": 1,
                    "paused": 0,
                    "stopped": 0,
                    "created": 0,
                    "restarting": 0,
                    "removing": 0,
                    "dead": 0,
                    "exited": 0
                },
                "error": null,
                "error_type": null
            }
        }
    ]
)
async def list_containers(
    request: ListContainersRequest
) -> Dict[str, Any]:
    """List all Docker containers with status information."""
    try:
        # Use the utility function to list containers
        result = run_docker_command(
            'ps',
            ['-a'] if request.all_states else [],
            format_json=True
        )
        
        if not isinstance(result, list):
            result = [result] if result else []
            
        # Format the container information
        containers = []
        for container in result:
            containers.append({
                'id': container.get('ID', ''),
                'name': container.get('Names', ''),
                'image': container.get('Image', ''),
                'status': container.get('Status', ''),
                'state': 'running' if 'Up' in container.get('Status', '') else 'exited',
                'created': container.get('CreatedAt', ''),
                'ports': container.get('Ports', '')
            })
            
        return {
            "success": True,
            "containers": containers,
            "total": len(containers),
            "running": len([c for c in containers if c.get("state") == "running"]),
            "stopped": len([c for c in containers if c.get("state") != "running"])
        }
    except Exception as e:
        return handle_error(e, "list_containers")

@Tool(
    name="create_container",
    description="Create a new Docker container from an image",
    parameters={
        "type": "object",
        "properties": {
            "image": {
                "type": "string",
                "description": "Name of the image to use for the container"
            },
            "name": {
                "type": "string",
                "description": "Assign a name to the container"
            },
            "command": {
                "type": "string",
                "description": "Command to run in the container"
            },
            "environment": {
                "type": "object",
                "description": "Environment variables to set in the container"
            },
            "ports": {
                "type": "object",
                "description": "Port mappings (host_port: container_port)"
            },
            "volumes": {
                "type": "object",
                "description": "Volume mappings (host_path: container_path)"
            },
            "network": {
                "type": "string",
                "description": "Connect container to a network"
            },
            "restart_policy": {
                "type": "string",
                "enum": ["no", "on-failure", "always", "unless-stopped"],
                "description": "Restart policy for the container"
            }
        },
        "required": ["image"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "image": {"type": "string"},
                    "status": {"type": "string"}
                },
                "required": ["id", "name", "image", "status"]
            },
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "message"]
    },
    examples=[
        {
            "name": "Create a simple container",
            "input": {
                "image": "nginx:latest",
                "name": "my-nginx"
            },
            "output": {
                "success": True,
                "message": "Container created successfully",
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "my-nginx",
                    "image": "nginx:latest",
                    "status": "created"
                }
            }
        },
        {
            "name": "Create a container with environment variables and ports",
            "input": {
                "image": "postgres:13",
                "name": "my-db",
                "environment": {
                    "POSTGRES_PASSWORD": "secret",
                    "POSTGRES_USER": "user"
                },
                "ports": {
                    "5432/tcp": 5432
                }
            },
            "output": {
                "success": True,
                "message": "Container created successfully",
                "container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "my-db",
                    "image": "postgres:13",
                    "status": "created"
                }
            }
        }
    ]
)
async def create_container(
    request: CreateContainerRequest
) -> Dict[str, Any]:
    """Create a new Docker container from an image."""
    try:
        container = await container_mgr.create_container(
            image=request.image,
            name=request.name,
            command=request.command,
            ports=request.ports,
            environment=request.environment,
            volumes=request.volumes,
            network=request.network,
            restart_policy=request.restart_policy,
            auto_remove=request.auto_remove,
            detach=request.detach,
            tty=request.tty,
            stdin_open=request.stdin_open,
            mem_limit=request.mem_limit,
            cpu_shares=request.cpu_shares,
            labels=request.labels
        )
        return ContainerResponse(
            success=True,
            message="Container created successfully",
            container=container
        ).dict()
    except Exception as e:
        return handle_error(e, "create_container")

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
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
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
async def start_container(
    request: StartContainerRequest
) -> Dict[str, Any]:
    """Start a stopped container."""
    try:
        container = await container_mgr.start_container(request.container_name)
        return ContainerResponse(
            success=True,
            message="Container started successfully",
            container=container
        ).dict()
    except Exception as e:
        return handle_error(e, "start_container")

@Tool(
    name="stop_container",
    description="Stop a running container",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to stop"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container to stop (alternative to container_id)"
            },
            "timeout": {
                "type": "integer",
                "minimum": 0,
                "default": 10,
                "description": "Timeout in seconds to wait for the container to stop before killing it"
            },
            "force": {
                "type": "boolean",
                "default": False,
                "description": "Force stop the container"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "exit_code": {"type": "integer"},
                    "started_at": {"type": "string", "format": "date-time"},
                    "finished_at": {"type": "string", "format": "date-time"}
                },
                "required": ["id", "name", "status", "exit_code"]
            },
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "message"]
    },
    examples=[
        {
            "name": "Stop a container by ID",
            "input": {
                "container_id": "a1b2c3d4e5f6",
                "timeout": 10
            },
            "output": {
                "success": True,
                "message": "Container a1b2c3d4e5f6 stopped successfully",
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "my-container",
                    "status": "exited",
                    "exit_code": 0,
                    "started_at": "2023-01-01T12:00:00Z",
                    "finished_at": "2023-01-01T13:00:00Z"
                }
            }
        },
        {
            "name": "Force stop a container",
            "input": {
                "container_id": "b2c3d4e5f6g7",
                "force": True
            },
            "output": {
                "success": True,
                "message": "Container b2c3d4e5f6g7 stopped successfully",
                "container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "another-container",
                    "status": "exited",
                    "exit_code": 137,
                    "started_at": "2023-01-01T12:00:00Z",
                    "finished_at": "2023-01-01T13:00:00Z"
                }
            }
        }
    ]
)
async def stop_container(
    request: StopContainerRequest
) -> Dict[str, Any]:
    """Stop a running container."""
    try:
        # Build the command with optional timeout
        cmd = ['stop']
        if request.timeout:
            cmd.extend(['--time', str(request.timeout)])
        cmd.append(request.container_name)
        
        # Execute the stop command
        result = run_docker_command('container', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"Failed to stop container {request.container_name}"
            }
            
        # Get the updated container info
        container_info = run_docker_command(
            'inspect',
            [request.container_name],
            format_json=True
        )
        
        return {
            "success": True,
            "message": f"Container {request.container_name} stopped successfully",
            "container": container_info
        }
    except Exception as e:
        return handle_error(e, "stop_container")

@Tool(
    name="restart_container",
    description="Restart a container"
)
async def restart_container(
    request: RestartContainerRequest
) -> Dict[str, Any]:
    """Restart a container."""
    try:
        # Build the command with optional timeout
        cmd = ['restart']
        if request.timeout:
            cmd.extend(['--time', str(request.timeout)])
        cmd.append(request.container_name)
        
        # Execute the restart command
        result = run_docker_command('container', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"Failed to restart container {request.container_name}"
            }
            
        # Get the updated container info
        container_info = run_docker_command(
            'inspect',
            [request.container_name],
            format_json=True
        )
        
        return {
            "success": True,
            "message": f"Container {request.container_name} restarted successfully",
            "container": container_info
        }
    except Exception as e:
        return handle_error(e, "restart_container")

@Tool(
    name="remove_container",
    description="Remove one or more containers",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to remove"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container to remove (alternative to container_id)"
            },
            "force": {
                "type": "boolean",
                "default": False,
                "description": "Force the removal of a running container (uses SIGKILL)"
            },
            "remove_volumes": {
                "type": "boolean",
                "default": False,
                "description": "Remove anonymous volumes associated with the container"
            },
            "remove_links": {
                "type": "boolean",
                "default": False,
                "description": "Remove the specified link and not the underlying container"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "removed_container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "removed": {"type": "boolean"}
                },
                "required": ["id", "name", "removed"]
            },
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success", "message"]
    },
    examples=[
        {
            "name": "Remove a container by ID",
            "input": {
                "container_id": "a1b2c3d4e5f6"
            },
            "output": {
                "success": True,
                "message": "Container a1b2c3d4e5f6 removed successfully",
                "removed_container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "my-container",
                    "removed": True
                }
            }
        },
        {
            "name": "Force remove a running container with volumes",
            "input": {
                "container_name": "my-database",
                "force": True,
                "remove_volumes": True
            },
            "output": {
                "success": True,
                "message": "Container my-database removed successfully",
                "removed_container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "my-database",
                    "removed": True
                }
            }
        }
    ]
)
async def remove_container(
    request: RemoveContainerRequest
) -> Dict[str, Any]:
    """Remove a container."""
    try:
        # Build the command with options
        cmd = ['rm']
        if request.force:
            cmd.append('--force')
        if request.remove_volumes:
            cmd.append('--volumes')
        cmd.append(request.container_name)
        
        # Execute the remove command
        result = run_docker_command('container', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"Failed to remove container {request.container_name}"
            }
            
        return {
            "success": True,
            "message": f"Container {request.container_name} removed successfully"
        }
    except Exception as e:
        return handle_error(e, "remove_container")

@Tool(
    name="get_container_logs",
    description="Fetch the logs of a container",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID of the container to get logs from"
            },
            "container_name": {
                "type": "string",
                "description": "Name of the container to get logs from (alternative to container_id)"
            },
            "follow": {
                "type": "boolean",
                "default": False,
                "description": "Follow log output (like tail -f)"
            },
            "tail": {
                "type": "integer",
                "minimum": 0,
                "description": "Number of lines to show from the end of the logs"
            },
            "since": {
                "type": "string",
                "description": "Show logs since a timestamp or relative time (e.g., 2m for 2 minutes)"
            },
            "until": {
                "type": "string",
                "description": "Show logs before a timestamp or relative time"
            },
            "timestamps": {
                "type": "boolean",
                "default": False,
                "description": "Show timestamps"
            },
            "details": {
                "type": "boolean",
                "default": False,
                "description": "Show extra details provided to logs"
            }
        },
        "oneOf": [
            {"required": ["container_id"]},
            {"required": ["container_name"]}
        ]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "logs": {"type": "string"},
            "container": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "required": ["id", "name"]
            },
            "log_metadata": {
                "type": "object",
                "properties": {
                    "line_count": {"type": "integer"},
                    "first_timestamp": {"type": "string", "format": "date-time"},
                    "last_timestamp": {"type": "string", "format": "date-time"}
                }
            },
            "error": {"type": "string"},
            "error_type": {"type": "string"}
        },
        "required": ["success"]
    },
    examples=[
        {
            "name": "Get the last 100 lines of logs",
            "input": {
                "container_id": "a1b2c3d4e5f6",
                "tail": 100
            },
            "output": {
                "success": True,
                "logs": "2023-01-01T12:00:00Z INFO: Server started on port 8080\n2023-01-01T12:00:05Z INFO: New connection from 192.168.1.1",
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "web-app"
                },
                "log_metadata": {
                    "line_count": 2,
                    "first_timestamp": "2023-01-01T12:00:00Z",
                    "last_timestamp": "2023-01-01T12:00:05Z"
                }
            }
        },
        {
            "name": "Follow logs in real-time",
            "input": {
                "container_name": "database",
                "follow": True,
                "timestamps": True
            },
            "output": {
                "success": True,
                "logs": "2023-01-01T12:00:00Z INFO: Database connection established\n2023-01-01T12:00:01Z INFO: Starting query execution",
                "container": {
                    "id": "b2c3d4e5f6g7",
                    "name": "database"
                },
                "log_metadata": {
                    "line_count": 2,
                    "first_timestamp": "2023-01-01T12:00:00Z",
                    "last_timestamp": "2023-01-01T12:00:01Z"
                }
            }
        }
    ]
)
async def get_container_logs(
    request: GetContainerLogsRequest
) -> Dict[str, Any]:
    """Get logs from a container."""
    try:
        # Build the logs command with options
        cmd = ['logs', request.container_name]
        
        if request.follow:
            cmd.append('--follow')
        if request.tail:
            cmd.extend(['--tail', str(request.tail)])
        if request.since:
            cmd.extend(['--since', str(request.since)])
        if request.until:
            cmd.extend(['--until', str(request.until)])
        if request.timestamps:
            cmd.append('--timestamps')
            
        # Execute the logs command
        result = run_docker_command('container', cmd, format_json=False)
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"Failed to get logs for container {request.container_name}",
                "container": request.container_name
            }
            
        return {
            "success": True,
            "logs": result.stdout,
            "container": request.container_name
        }
    except Exception as e:
        return handle_error(e, "get_container_logs")

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
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
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
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
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
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
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
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
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
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
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
