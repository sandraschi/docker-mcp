"""
Container logs functionality for Docker MCP.

This module provides tools for streaming container logs in real-time with
support for filtering by time, stream type, and more. It follows FastMCP 2.12+
standards for tool registration and error handling.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional, AsyncGenerator, Literal, Annotated

import docker
from docker.errors import DockerException, APIError, NotFound
from dockermcp.mcp_instance import mcp
from pydantic import Field, field_validator

from dockermcp.logging_config import logger

class LogStreamType(str, Enum):
    """Log stream types for container logs."""
    STDOUT = "stdout"
    STDERR = "stderr"
    ALL = "all"

@mcp.tool(
    name="get_container_logs",
    description="Retrieve logs from a Docker container with filtering options"
)
async def get_container_logs(
    container_id: Annotated[str, Field(description="ID or name of the container")],
    follow: Annotated[bool, Field(default=False, description="Follow log output (like tail -f)")],
    tail: Annotated[str, Field(default="100", description="Number of lines to show from the end of the logs (e.g., '100', 'all')")],
    since: Annotated[Optional[str], Field(default=None, description="Show logs since this timestamp (ISO 8601) or relative (e.g., 5m, 2h)")],
    until: Annotated[Optional[str], Field(default=None, description="Show logs before this timestamp (ISO 8601) or relative time")],
    timestamps: Annotated[bool, Field(default=False, description="Include timestamps in the log output")],
    stream_type: Annotated[str, Field(default="all", description="Which log streams to include (stdout, stderr, or all)")],
    timeout: Annotated[int, Field(default=60, description="Timeout in seconds for the log stream (1-3600)")]
) -> dict[str, Any]:
    """
    Retrieve logs from a Docker container with various filtering options.
    
    This function provides a flexible interface for retrieving container logs with support for:
    - Real-time log following (like tail -f)
    - Time-based filtering (since/until)
    - Stream filtering (stdout/stderr)
    - Configurable output format
    
    Args:
        container_id: ID or name of the container to get logs from
        follow: Whether to follow log output (like tail -f)
        tail: Number of lines to show from the end of the logs (e.g., "100", "all")
        since: Show logs since this timestamp (ISO 8601) or relative (e.g., 5m, 2h)
        until: Show logs before this timestamp (ISO 8601) or relative time
        timestamps: Include timestamps in the output
        stream_type: Which log streams to include (stdout, stderr, or all)
        timeout: Timeout in seconds for the log stream (1-3600)
        
    Returns:
        Dictionary with the log data and metadata
        
    Example:
        >>> await get_container_logs(
        ...     container_id="my-container",
        ...     tail="50",
        ...     since="5m",
        ...     stream_type="stdout"
        ... )
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "logs": [
                {
                    "timestamp": "2023-01-01T12:00:00Z",
                    "stream": "stdout",
                    "line": "Server started on port 8080"
                }
            ]
        }
    """
    try:
        # Validate stream_type
        try:
            stream_enum = LogStreamType(stream_type.lower())
        except ValueError:
            valid_types = [e.value for e in LogStreamType]
            raise ValueError(f"Invalid stream_type: {stream_type}. Must be one of: {', '.join(valid_types)}")
        
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "status": "error",
                "container_id": container_id,
                "error": f"Container not found: {container_id}"
            }
        
        # Prepare log parameters
        log_params = {
            'stdout': stream_enum in [LogStreamType.STDOUT, LogStreamType.ALL],
            'stderr': stream_enum in [LogStreamType.STDERR, LogStreamType.ALL],
            'follow': follow,
            'tail': tail,
            'since': since,
            'until': until,
            'timestamps': timestamps,
            'stream': follow  # Return a generator if following
        }
        
        # Clean up None values
        log_params = {k: v for k, v in log_params.items() if v is not None}
        
        # Get logs
        if follow:
            # For following logs, return a generator
            return {
                "status": "success",
                "container_id": container_id,
                "stream": _stream_logs(container, log_params, timeout)
            }
        else:
            # For one-time log retrieval, return the logs directly
            logs = container.logs(**log_params).decode('utf-8', errors='replace')
            return {
                "status": "success",
                "container_id": container_id,
                "logs": [
                    {
                        "timestamp": datetime.utcnow().isoformat() + 'Z',
                        "stream": stream_enum.value,
                        "line": line
                    }
                    for line in logs.splitlines()
                ]
            }
            
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error getting container logs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

async def _stream_logs(
    container: docker.models.containers.Container,
    log_params: dict[str, Any],
    timeout: int
) -> AsyncGenerator[str, None]:
    """
    Stream logs from a container with a timeout.
    
    Args:
        container: Docker container object
        log_params: Parameters for the logs() method
        timeout: Timeout in seconds
        
    Yields:
        Log entries as they arrive
    """
    try:
        # Start streaming logs
        log_stream = container.logs(**log_params, stream=True)
        
        # Process logs until timeout or container stops
        start_time = datetime.now()
        for log_chunk in log_stream:
            # Check for timeout
            if (datetime.now() - start_time).total_seconds() > timeout:
                logger.warning(f"Log stream timed out after {timeout} seconds")
                break
                
            try:
                # Parse the log line (Docker's log format)
                # Format: 8-byte header [STREAM_TYPE, 0, 0, 0, SIZE1, SIZE2, SIZE3, SIZE4] + log message
                if len(log_chunk) > 8:
                    stream_type = {1: 'stdout', 2: 'stderr'}.get(log_chunk[0], 'unknown')
                    log_line = log_chunk[8:].decode('utf-8', errors='replace').strip()
                    
                    if log_line:  # Skip empty lines
                        yield {
                            "timestamp": datetime.utcnow().isoformat() + 'Z',
                            "stream": stream_type,
                            "line": log_line
                        }
            except Exception as e:
                logger.error(f"Error parsing log chunk: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error in log stream: {str(e)}")
        yield {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "stream": "stderr",
            "line": f"Error in log stream: {str(e)}"
        }
    finally:
        # Cleanup
        if 'log_stream' in locals():
            try:
                log_stream.close()
            except:
                pass
