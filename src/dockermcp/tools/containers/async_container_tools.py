"""
Async Container Tools for Docker MCP.

This module provides async container management functionality using aiodocker.
"""
import aiodocker
import logging
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from pydantic import BaseModel, Field
from enum import Enum
from fastmcp.tools import Tool, tool, tool, tool
from fastmcp.exceptions import ToolException
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

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
    description="Manage container lifecycle operations (start, stop, restart, remove, pause, unpause)"
)
async def manage_container_lifecycle(
    container_id: str,
    action: str,
    force: bool = False,
    timeout: int = 10,
    remove_volumes: bool = False
) -> Dict[str, Any]:
    """
    Execute container lifecycle operations asynchronously.
    
    Args:
        container_id: ID or name of the container
        action: Action to perform (start, stop, restart, remove, pause, unpause)
        force: Force the action if needed
        timeout: Timeout in seconds for stop/restart operations (1-300)
        remove_volumes: Remove volumes when removing a container
        
    Returns:
        Dictionary with operation result and container state
    """
    try:
        async with aiodocker.Docker() as docker:
            container = docker.containers.container(container_id)
            
            try:
                container_data = await container.show()
                container_status = container_data['State']['Status']
            except aiodocker.DockerError as e:
                if "no such container" in str(e).lower():
                    return {
                        'success': False,
                        'message': f'Container {container_id} not found',
                        'container_id': container_id,
                        'action': action,
                        'error': 'Container not found'
                    }
                raise
            
            if action == ContainerAction.START:
                if container_status == 'running':
                    return {
                        'success': False,
                        'message': f'Container {container_id} is already running',
                        'container_id': container_id,
                        'action': action,
                        'state': container_data['State']
                    }
                await container.start()
                message = f'Successfully started container {container_id}'
                
            elif action == ContainerAction.STOP:
                if container_status == 'exited':
                    return {
                        'success': False,
                        'message': f'Container {container_id} is already stopped',
                        'container_id': container_id,
                        'action': action,
                        'state': container_data['State']
                    }
                await container.stop(t=timeout)
                message = f'Successfully stopped container {container_id}'
                
            elif action == ContainerAction.RESTART:
                await container.stop(t=timeout)
                await container.start()
                message = f'Successfully restarted container {container_id}'
                
            elif action == ContainerAction.REMOVE:
                if container_status == 'running' and not force:
                    return {
                        'success': False,
                        'message': f'Cannot remove running container {container_id}. Use force=True to force removal.',
                        'container_id': container_id,
                        'action': action,
                        'error': 'Container is running',
                        'state': container_data['State']
                    }
                await container.delete(force=force, v=remove_volumes)
                return {
                    'success': True,
                    'message': f'Successfully removed container {container_id}',
                    'container_id': container_id,
                    'action': action
                }
                
            elif action == ContainerAction.PAUSE:
                if container_status != 'running':
                    return {
                        'success': False,
                        'message': f'Cannot pause container {container_id} in state {container_status}',
                        'container_id': container_id,
                        'action': action,
                        'error': 'Container is not running',
                        'state': container_data['State']
                    }
                await container.pause()
                message = f'Successfully paused container {container_id}'
                
            elif action == ContainerAction.UNPAUSE:
                if container_status != 'paused':
                    return {
                        'success': False,
                        'message': f'Cannot unpause container {container_id} in state {container_status}',
                        'container_id': container_id,
                        'action': action,
                        'error': 'Container is not paused',
                        'state': container_data['State']
                    }
                await container.unpause()
                message = f'Successfully unpaused container {container_id}'
                
            else:
                return {
                    'success': False,
                    'message': f'Invalid action: {action}',
                    'container_id': container_id,
                    'action': action,
                    'error': 'Invalid action',
                    'state': container_data.get('State')
                }
            
            # Get updated container state
            updated_data = await container.show()
            return {
                'success': True,
                'message': message,
                'container_id': container_id,
                'action': action,
                'state': updated_data['State']
            }
            
    except aiodocker.DockerError as e:
        return {
            'success': False,
            'message': f'Docker error: {str(e)}',
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

