"""
Container listing functionality for Docker MCP.

This module provides tools for listing Docker containers with various filtering options.
It follows FastMCP 2.12+ standards for tool registration.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import docker
from docker.errors import DockerException
from fastmcp.tools.tool import Tool

from dockermcp.logging_config import logger

@Tool(
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
    output_schema={
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
                        'state': {'type': 'string'},
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
                        }
                    }
                }
            },
            'count': {'type': 'integer'}
        },
        'required': ['containers', 'count']
    }
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
        Dictionary containing container information and status
        
    Example:
        >>> list_containers(all_states=True, filters={"status": "running"})
        {
            "status": "success",
            "containers": [
                {
                    "id": "abc123",
                    "name": "my-container",
                    "status": "running",
                    "image": "alpine:latest",
                    "created": "2023-01-01T00:00:00Z"
                }
            ]
        }
    """
    try:
        # Convert empty dict to None for Docker SDK
        filters = filters or {}
        if not filters:
            filters = None
            
        client = docker.from_env()
        containers = client.containers.list(
            all=all_states,
            filters=filters
        )
        
        result = {
            "status": "success",
            "containers": [
                {
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else str(container.image.id),
                    "created": container.attrs["Created"],
                    "ports": container.ports,
                    "labels": container.labels,
                    "state": container.attrs["State"]
                }
                for container in containers
            ]
        }
        
        if not result["containers"]:
            result["message"] = "No containers found matching the criteria"
            
        return result
        
    except docker.errors.APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}
        
    except docker.errors.DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error listing containers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "message": error_msg}
