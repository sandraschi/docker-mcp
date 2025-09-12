"""
Container listing functionality for Docker MCP.

This module provides tools for listing Docker containers with various filtering options.
It follows FastMCP 2.12+ standards for tool registration.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Annotated, Union
from datetime import datetime

import docker
from docker.errors import DockerException
from pydantic import BaseModel, Field, ConfigDict
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

class ContainerInfo(BaseModel):
    """Information about a Docker container."""
    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    status: str = Field(..., description="Container status")
    image: str = Field(..., description="Container image")
    created: str = Field(..., description="Creation timestamp")
    state: str = Field(..., description="Container state")
    labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "abc123",
                "name": "my-container",
                "status": "running",
                "image": "alpine:latest",
                "created": "2023-01-01T00:00:00Z",
                "state": "running",
                "labels": {"com.example.key": "value"}
            }
        }
    )

class ListContainersParams(BaseModel):
    """Parameters for listing Docker containers."""
    all_states: bool = Field(
        True,
        description="If True, include stopped containers"
    )
    filters: Optional[Dict[str, str]] = Field(
        None,
        description="Dictionary of filter key-value pairs"
    )

@mcp.tool(
    name="list_containers",
    description="List Docker containers with optional filtering"
)
async def list_containers(params: ListContainersParams) -> Dict[str, Any]:
    """
    List Docker containers with optional filtering.
    
    Args:
        params: ListContainersParams containing:
            - all_states: If True, include stopped containers
            - filters: Dictionary of filter key-value pairs
        
    Returns:
        Dictionary containing:
            - status: "success" or "error"
            - message: Status message
            - containers: List of container information dictionaries
            - error: Error message if any
            
    Raises:
        ToolError: If there's an error communicating with the Docker daemon
        
    Example:
        >>> from dockermcp.tools.containers.list_containers import ListContainersParams
        >>> params = ListContainersParams(all_states=True, filters={"status": "running"})
        >>> await list_containers(params)
                }
            ]
        }
    """
    try:
        client = docker.from_env()
        
        # Convert empty dict to None for Docker SDK
        filters = params.filters or {}
        if not filters:
            filters = None
            
        # Get containers from Docker
        containers = client.containers.list(
            all=params.all_states,
            filters=filters
        )
        
        # Process containers into response
        container_list = []
        for container in containers:
            container_inspect = container.attrs
            container_list.append(
                ContainerInfo(
                    id=container.id,
                    name=container.name,
                    status=container.status,
                    image=container.image.tags[0] if container.image.tags else container.image.id,
                    created=container_inspect['Created'],
                    state=container_inspect['State']['Status'],
                    labels=container_inspect.get('Config', {}).get('Labels', {})
                ).model_dump()
            )
            
        return {
            "status": "success",
            "message": f"Found {len(container_list)} containers",
            "containers": container_list
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": "Failed to list containers",
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error listing containers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": "Failed to list containers",
            "error": error_msg
        }
