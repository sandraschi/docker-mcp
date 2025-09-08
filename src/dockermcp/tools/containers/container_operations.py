"""
Core container operations for Docker MCP.

This module contains the core container operations that are used by other modules.
Compatible with FastMCP 2.12+.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

# FastMCP imports
from fastmcp.tools import tool as Tool
from fastmcp.exceptions import ToolError

# Pydantic models
from pydantic import BaseModel, Field

# Local imports
from dockermcp.logging_config import logger, configure_logging
from ..core.containers import ContainerManager
from .container_utils import (
    create_response,
    handle_error,
    container_mgr,
    run_docker_command,
)

# Re-export models for backward compatibility
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

# Configure logging
configure_logging()

# Type variables for generics
T = TypeVar('T', bound=BaseModel)
ContainerT = TypeVar('ContainerT', bound=BaseModel)

# Re-export container_mgr with proper type annotation
container_mgr: ContainerManager = cast(ContainerManager, container_mgr)

def get_tools() -> List[Tool]:
    """
    Return all tools in this module for registration.
    
    Returns:
        List of Tool objects that should be registered with FastMCP
    """
    # This module contains internal operations, no tools to register directly
    return []

def _process_log_chunk(
    log_chunk: bytes,
    include_timestamps: bool = False,
    timezone: str = 'UTC',
    filter_term: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Process a single log chunk into a structured format.
    
    This function parses raw Docker log chunks and converts them into a structured
    dictionary format. It handles both JSON and plain text log formats, and can
    optionally filter logs based on a search term.
    
    Args:
        log_chunk: Raw log chunk bytes from Docker's log stream
        include_timestamps: If True, includes timestamps in the output
        timezone: Timezone for timestamp conversion (default: 'UTC')
        filter_term: Optional term to filter logs by (case-insensitive)
        
    Returns:
        Dictionary containing structured log entry with the following keys:
        - timestamp: ISO 8601 formatted timestamp (if include_timestamps is True)
        - message: The log message content
        - stream: The log stream ('stdout' or 'stderr')
        - raw: The original raw log chunk
        
        Returns None if the log entry is filtered out by filter_term.
        
    Raises:
        ToolError: If there's an error processing the log chunk
        
    Example:
        >>> log_chunk = b'2023-01-01T12:00:00.000000000Z Hello, World!\n'
        >>> _process_log_chunk(log_chunk, include_timestamps=True)
        {
            'timestamp': '2023-01-01T12:00:00+00:00',
            'message': 'Hello, World!',
            'stream': 'stdout',
            'raw': b'2023-01-01T12:00:00.000000000Z Hello, World!\n'
        }
    """
    if not log_chunk:
        return None
        
    try:
        # Convert bytes to string and strip whitespace
        log_str = log_chunk.decode('utf-8', errors='replace').strip()
        if not log_str:
            return None
            
        # Check if log matches filter term (if provided)
        if filter_term and filter_term.lower() not in log_str.lower():
            return None
            
        # Parse the log line (format: '2023-01-01T12:00:00.000000000Z Hello, World!')
        timestamp = None
        message = log_str
        stream = 'stdout'  # Default stream
        
        # Extract timestamp if present and requested
        if ' ' in log_str and log_str[0].isdigit():
            try:
                # Try to parse timestamp (first part before space)
                timestamp_str, message = log_str.split(' ', 1)
                timestamp = datetime.fromisoformat(timestamp_str.rstrip('Z') + '+00:00')
                
                # Handle timezone conversion if needed
                if timezone.upper() != 'UTC':
                    # This is a placeholder - in a real implementation, you'd use pytz or zoneinfo
                    # to handle timezone conversion
                    pass
                    
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse timestamp from log: {e}")
                message = log_str  # Use the full string if timestamp parsing fails
        
        # Create the result dictionary
        result = {
            'message': message,
            'stream': stream,
            'raw': log_chunk
        }
        
        if include_timestamps and timestamp:
            result['timestamp'] = timestamp.isoformat()
            
        return result
        
    except Exception as e:
        error_msg = f"Error processing log chunk: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

def _validate_container_identifier(
    container_id: Optional[str] = None, 
    container_name: Optional[str] = None
) -> str:
    """
    Validate that either container_id or container_name is provided, but not both.
    
    This function ensures that exactly one of container_id or container_name is provided
    and returns the provided identifier. This is a utility function used by other
    container operations to validate their input parameters.
    
    Args:
        container_id: The unique identifier of the container (64-character hex string)
        container_name: The name of the container (as specified in --name or auto-generated)
        
    Returns:
        str: The validated container identifier (either container_id or container_name)
        
    Raises:
        ValueError: If neither container_id nor container_name is provided,
                   or if both container_id and container_name are provided
        
    Example:
        >>> _validate_container_identifier(container_id="abc123")
        'abc123'
        >>> _validate_container_identifier(container_name="my-container")
        'my-container'
        >>> _validate_container_identifier()  # Raises ValueError
        >>> _validate_container_identifier("abc123", "my-container")  # Raises ValueError
    """
    if not container_id and not container_name:
        raise ValueError(
            "Container identification error: "
            "Either container_id or container_name must be provided"
        )
    if container_id and container_name:
        raise ValueError(
            "Container identification error: "
            "Only one of container_id or container_name should be provided"
        )
    return container_id or container_name or ""  # Type checker workaround

def _get_container_id(
    container_id: Optional[str] = None, 
    container_name: Optional[str] = None
) -> str:
    """
    Resolve a container identifier to a container ID.
    
    This function takes either a container ID or name and returns the corresponding
    container ID. If a name is provided, it performs a lookup to find the container ID.
    
    Args:
        container_id: The ID of the container (64-character hex string)
        container_name: The name of the container
        
    Returns:
        str: The container ID
        
    Raises:
        ToolError: If neither container_id nor container_name is provided,
                  if the container is not found, or if there's an error
                  accessing the Docker daemon
                  
    Example:
        >>> _get_container_id(container_id="abc123")
        'abc123'
        >>> _get_container_id(container_name="my-container")
        'abc123'  # Returns the actual container ID
    """
    # First validate the input parameters
    identifier = _validate_container_identifier(container_id, container_name)
    
    # If we already have an ID, return it directly
    if container_id:
        if len(container_id) == 64 and all(c in '0123456789abcdef' for c in container_id.lower()):
            return container_id
        logger.warning(
            "Container ID '%s' doesn't match the expected format (64-character hex string). "
            "Attempting to use it anyway.", container_id
        )
        return container_id
    
    # If we have a name, look up the container ID
    if container_name:
        try:
            # Look up container by name
            containers = container_mgr.list_containers(
                all=True,  # Include stopped containers
                filters={'name': [container_name]}
            )
            
            if not containers:
                raise ToolError(f"No container found with name: {container_name}")
                
            if len(containers) > 1:
                logger.warning(
                    "Multiple containers found with name '%s'. Using the first one.",
                    container_name
                )
                
            return containers[0].id
            
        except Exception as e:
            error_msg = f"Error looking up container by name '{container_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ToolError(error_msg) from e
    
    # This should never be reached due to _validate_container_identifier
    raise ToolError(
        "Container identification error: "
        "Either container_id or container_name must be provided"
    )

# Public API - these symbols will be available when importing from this module
__all__ = [
    # Container manager instance
    'container_mgr',
    
    # Core utility functions
    'create_response',
    'handle_error',
    'run_docker_command',
    'get_tools',
    
    # Internal utility functions (documented but considered implementation details)
    '_process_log_chunk',
    '_validate_container_identifier',
    '_get_container_id',
    
    # Re-exported models for convenience
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
]

# Module-level documentation
__doc__ = """
Container Operations Module
==========================

This module provides core container operations for the Docker MCP system.
It serves as a foundation for higher-level container management functionality.

Key Features:
- Log processing and streaming
- Container identification and validation
- Common utilities for container operations

Note: Most users should use the higher-level container tools rather than
calling these functions directly.
"""

