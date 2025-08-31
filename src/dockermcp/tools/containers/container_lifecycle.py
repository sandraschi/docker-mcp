"""
Container lifecycle management for Docker MCP.

Provides tools for managing container lifecycle operations:
- Start containers
- Stop containers
- Restart containers
- Remove containers
- Pause/Unpause containers
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import docker
from docker.models.containers import Container
from fastmcp.tools import Tool
from fastmcp.types import Param, Return
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ContainerAction(str, Enum):
    """Available container actions."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    REMOVE = "remove"
    PAUSE = "pause"
    UNPAUSE = "unpause"

class ContainerLifecycleRequest(BaseModel):
    """Request model for container lifecycle operations."""
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    action: ContainerAction = Field(
        ...,
        description="Action to perform on the container"
    )
    force: bool = Field(
        default=False,
        description="Force the action (e.g., force remove a running container)"
    )
    timeout: int = Field(
        default=10,
        ge=1,
        le=300,
        description="Timeout in seconds for stop/restart operations"
    )
    remove_volumes: bool = Field(
        default=False,
        description="Remove volumes when removing a container"
    )

class ContainerLifecycleResponse(BaseModel):
    """Response model for container lifecycle operations."""
    success: bool
    message: str
    container_id: str
    action: str
    state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@Tool(
    name="manage_container_lifecycle",
    description="Manage container lifecycle operations (start, stop, restart, remove, pause, unpause)",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID or name of the container"
            },
            "action": {
                "type": "string",
                "enum": ["start", "stop", "restart", "remove", "pause", "unpause"],
                "description": "Action to perform on the container"
            },
            "force": {
                "type": "boolean",
                "default": False,
                "description": "Force the action (e.g., force remove a running container)"
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 10,
                "description": "Timeout in seconds for stop/restart operations"
            },
            "remove_volumes": {
                "type": "boolean",
                "default": False,
                "description": "Remove volumes when removing a container"
            }
        },
        "required": ["container_id", "action"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "container_id": {"type": "string"},
            "action": {"type": "string"},
            "state": {
                "type": ["object", "null"],
                "properties": {
                    "Status": {"type": "string"},
                    "Running": {"type": "boolean"},
                    "Paused": {"type": "boolean"},
                    "Restarting": {"type": "boolean"},
                    "Pid": {"type": "integer"},
                    "ExitCode": {"type": "integer"},
                    "Error": {"type": "string"},
                    "StartedAt": {"type": "string", "format": "date-time"},
                    "FinishedAt": {"type": "string", "format": "date-time"}
                }
            },
            "error": {"type": ["string", "null"]}
        },
        "required": ["success", "message", "container_id", "action"]
    },
    examples=[
        {
            "name": "Stop a container",
            "input": {
                "container_id": "my-container",
                "action": "stop",
                "timeout": 10
            },
            "output": {
                "success": True,
                "message": "Successfully stopped container my-container",
                "container_id": "my-container",
                "action": "stop",
                "state": {
                    "Status": "exited",
                    "Running": False,
                    "Paused": False,
                    "Restarting": False,
                    "Pid": 0,
                    "ExitCode": 0,
                    "Error": "",
                    "StartedAt": "2023-01-01T12:00:00Z",
                    "FinishedAt": "2023-01-01T12:00:10Z"
                },
                "error": None
            }
        },
        {
            "name": "Start a container",
            "input": {
                "container_id": "my-container",
                "action": "start"
            },
            "output": {
                "success": True,
                "message": "Successfully started container my-container",
                "container_id": "my-container",
                "action": "start",
                "state": {
                    "Status": "running",
                    "Running": True,
                    "Paused": False,
                    "Restarting": False,
                    "Pid": 1234,
                    "ExitCode": 0,
                    "Error": "",
                    "StartedAt": "2023-01-01T12:00:00Z",
                    "FinishedAt": "0001-01-01T00:00:00Z"
                }
            }
        }
    ]
)
async def manage_container_lifecycle(
    request: ContainerLifecycleRequest
) -> Dict[str, Any]:
    container_id = request.container_id
    action = request.action
    force = request.force
    timeout = request.timeout
    remove_volumes = request.remove_volumes
    """
    Manage container lifecycle operations.
    
    Args:
        container_id: ID or name of the container
        action: Action to perform (start, stop, restart, remove, pause, unpause)
        force: Force the action if needed
        timeout: Timeout in seconds for stop/restart operations
        remove_volumes: Remove volumes when removing a container
        
    Returns:
        Dictionary with operation result and container state
    """
    client = docker.from_env()
    
    try:
        container = client.containers.get(container_id)
        container_attrs = container.attrs
        
        if action == ContainerAction.START:
            if container.status == 'running':
                return {
                    'success': False,
                    'message': f'Container {container_id} is already running',
                    'container_id': container_id,
                    'action': action,
                    'state': container_attrs['State']
                }
            container.start()
            message = f'Successfully started container {container_id}'
            
        elif action == ContainerAction.STOP:
            if container.status == 'exited':
                return {
                    'success': False,
                    'message': f'Container {container_id} is already stopped',
                    'container_id': container_id,
                    'action': action,
                    'state': container_attrs['State']
                }
            container.stop(timeout=timeout)
            message = f'Successfully stopped container {container_id}'
            
        elif action == ContainerAction.RESTART:
            container.restart(timeout=timeout)
            message = f'Successfully restarted container {container_id}'
            
        elif action == ContainerAction.REMOVE:
            if container.status == 'running' and not force:
                return {
                    'success': False,
                    'message': f'Cannot remove running container {container_id}. Use force=True to force removal.',
                    'container_id': container_id,
                    'action': action,
                    'error': 'Container is running',
                    'state': container_attrs['State']
                }
            container.remove(force=force, v=remove_volumes)
            message = f'Successfully removed container {container_id}'
            
        elif action == ContainerAction.PAUSE:
            if container.status != 'running':
                return {
                    'success': False,
                    'message': f'Cannot pause container {container_id} in state {container.status}',
                    'container_id': container_id,
                    'action': action,
                    'error': 'Container is not running',
                    'state': container_attrs['State']
                }
            container.pause()
            message = f'Successfully paused container {container_id}'
            
        elif action == ContainerAction.UNPAUSE:
            if container.status != 'paused':
                return {
                    'success': False,
                    'message': f'Container {container_id} is not paused',
                    'container_id': container_id,
                    'action': action,
                    'state': container_attrs['State']
                }
            container.unpause()
            message = f'Successfully unpaused container {container_id}'
            
        else:
            return {
                'success': False,
                'message': f'Invalid action: {action}',
                'container_id': container_id,
                'action': action,
                'error': 'Invalid action'
            }
        
        # Get updated container state
        container.reload()
        
        return {
            'success': True,
            'message': message,
            'container_id': container_id,
            'action': action,
            'state': container.attrs['State']
        }
        
    except docker.errors.NotFound:
        return {
            'success': False,
            'message': f'Container {container_id} not found',
            'container_id': container_id,
            'action': action,
            'error': 'Container not found'
        }
    except docker.errors.APIError as e:
        return {
            'success': False,
            'message': f'Docker API error: {str(e)}',
            'container_id': container_id,
            'action': action,
            'error': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'container_id': container_id,
            'action': action,
            'error': str(e)
        }
