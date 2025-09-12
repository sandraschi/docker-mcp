"""
Container listing functionality for Docker MCP.

This module provides tools for listing Docker containers with various filtering options.
It is designed to work with FastMCP 2.12+ and follows the project's coding standards.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# Docker SDK
import docker
from docker.errors import DockerException

# FastMCP imports
from fastmcp.tools import Tool, tool

# Import custom exceptions
from .container_models import ContainerError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

class ListContainersRequest:
    """Request model for listing containers."""
    
    def __init__(
        self,
        all_states: bool = True,
        filters: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Initialize ListContainersRequest.
        
        Args:
            all_states: If True, include stopped containers
            filters: Dictionary of filter key-value pairs
        """
        self.all_states = all_states
        self.filters = filters or {}

@tool(
    name="list_containers",
    description="List Docker containers with optional filtering",
    parameters={
        'type': 'object',
        'properties': {
            'all_states': {
                'type': 'boolean',
                'description': 'If True, include stopped containers',
                'default': True
            },
            'filters': {
                'type': 'object',
                'description': 'Dictionary of filter key-value pairs',
                'additionalProperties': {'type': 'string'},
                'default': {}
            }
        },
        'required': []
    },
    response_model={
        'type': 'object',
        'properties': {
            'containers': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'name': {'type': 'string'},
                        'status': {'type': 'string'},
                        'image': {'type': 'string'},
                        'created': {'type': 'string', 'format': 'date-time'},
                        'ports': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'private_port': {'type': 'integer'},
                                    'public_port': {'type': 'integer'},
                                    'type': {'type': 'string'}
                                }
                            }
                        },
                        'labels': {
                            'type': 'object',
                            'additionalProperties': {'type': 'string'}
                        },
                        'state': {'type': 'string'},
                        'status': {'type': 'string'}
                    }
                }
            }
        },
        'required': ['containers']
    },
    examples=[
        {
            'summary': 'List all containers',
            'value': {
                'all_states': True,
                'filters': {}
            }
        },
        {
            'summary': 'List only running containers',
            'value': {
                'all_states': False,
                'filters': {}
            }
        },
        {
            'summary': 'Filter containers by label',
            'value': {
                'all_states': True,
                'filters': {
                    'label': 'com.example.app=test'
                }
            }
        }
    ]
)
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
        
        # Get container list using the implementation function
        containers = await _list_containers_impl(request)
        
        return {
            'success': True,
            'containers': containers
        }
        
    except Exception as e:
        error_msg = f"Failed to list containers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'containers': [],
            'error': error_msg
        }

async def _list_containers_impl(request: ListContainersRequest) -> List[Dict[str, Any]]:
    """
    Implementation of container listing with error handling.
    
    Args:
        request: ListContainersRequest with filtering options
        
    Returns:
        List of container information dictionaries
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(
            all=request.all_states,
            filters=request.filters
        )
        
        result = []
        for container in containers:
            try:
                container.reload()
                attrs = container.attrs
                
                # Extract basic container info
                container_info = {
                    'id': container.id,
                    'name': container.name.lstrip('/'),
                    'image': container.image.tags[0] if container.image.tags else container.image.id,
                    'status': container.status,
                    'state': attrs.get('State', {}).get('Status', 'unknown'),
                    'created': attrs.get('Created'),
                    'ports': attrs.get('NetworkSettings', {}).get('Ports', {}),
                    'networks': list(attrs.get('NetworkSettings', {}).get('Networks', {}).keys())
                }
                
                result.append(container_info)
                
            except Exception as e:
                logger.warning(f"Error processing container {container.id}: {str(e)}")
                continue
                
        return result
        
    except DockerException as e:
        error_msg = f"Docker error listing containers: {str(e)}"
        logger.error(error_msg)
        raise ContainerError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error listing containers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ContainerError(error_msg)

def get_tools():
    """
    Get all tools defined in this module for registration with FastMCP 2.12+.
    
    Returns:
        List of tool functions to register with FastMCP
    """
    return [list_containers]
