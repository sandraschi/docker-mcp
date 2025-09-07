"""
Container logs streaming for Docker MCP.

This module provides tools for streaming container logs in real-time with
full support for FastMCP 2.12+ standards. It includes features for both
synchronous log retrieval and real-time log streaming with filtering options.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Union, AsyncGenerator, cast, TypeVar, Type

# Pydantic models
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator

# Docker SDK
import aiodocker
from aiodocker.exceptions import DockerError

# FastMCP imports
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Type variables
T = TypeVar('T', bound=BaseModel)

class LogStreamType(str, Enum):
    """
    Log stream types for container logs.
    
    Attributes:
        STDOUT: Standard output logs only
        STDERR: Standard error logs only
        ALL: Both standard output and error logs
    """
    STDOUT = "stdout"
    STDERR = "stderr"
    ALL = "all"
    
    @classmethod
    def get_description(cls, stream_type: 'LogStreamType') -> str:
        """Get a human-readable description of the stream type."""
        descriptions = {
            cls.STDOUT: "Standard output logs only",
            cls.STDERR: "Standard error logs only",
            cls.ALL: "Both standard output and error logs"
        }
        return descriptions.get(stream_type, f"Unknown stream type: {stream_type}")

class ContainerLogsRequest(BaseModel):
    """
    Request model for container logs.
    
    Attributes:
        container_id: ID or name of the container
        follow: Whether to follow log output (like tail -f)
        tail: Number of lines to show from the end of the logs
        since: Show logs since this timestamp or relative time
        until: Show logs before this timestamp or relative time
        timestamps: Include timestamps in the output
        stream_type: Which log streams to include
        include_raw: Whether to include raw log bytes in the response
        timeout: Timeout in seconds for the log stream
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "my-container",
                "follow": True,
                "tail": 100,
                "since": "5m",
                "timestamps": True,
                "stream_type": "all",
                "include_raw": False,
                "timeout": 30
            }
        }
    )
    
    container_id: str = Field(
        ...,
        min_length=1,
        description="ID or name of the container"
    )
    follow: bool = Field(
        default=True,
        description="Follow log output (like tail -f)"
    )
    tail: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Number of lines to show from the end of the logs (max: 10000)"
    )
    since: Optional[Union[datetime, str, int]] = Field(
        default=None,
        description="Show logs since this timestamp (ISO 8601), relative time (e.g., 5m, 2h), or Unix timestamp"
    )
    until: Optional[Union[datetime, str, int]] = Field(
        default=None,
        description="Show logs before this timestamp (ISO 8601), relative time, or Unix timestamp"
    )
    timestamps: bool = Field(
        default=False,
        description="Include timestamps in the log output"
    )
    stream_type: LogStreamType = Field(
        default=LogStreamType.ALL,
        description=f"Which log streams to include. Options: {', '.join([e.value for e in LogStreamType])}"
    )
    include_raw: bool = Field(
        default=False,
        description="Include raw log bytes in the response (for debugging)"
    )
    timeout: Optional[int] = Field(
        default=None,
        ge=1,
        le=3600,
        description="Timeout in seconds for the log stream (1-3600), None for no timeout"
    )
    
    @field_validator('container_id')
    @classmethod
    def validate_container_id(cls, v: str) -> str:
        """Validate container ID is not empty."""
        if not v.strip():
            raise ValueError("Container ID cannot be empty")
        return v.strip()
    
    @field_validator('since', 'until', mode='before')
    @classmethod
    def parse_timestamp(cls, v: Any) -> Any:
        """Parse timestamp from various formats."""
        if v is None or isinstance(v, (int, datetime)):
            return v
            
        if isinstance(v, str):
            # Try to parse as ISO 8601
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
                
            # Try to parse as relative time (e.g., 5m, 2h)
            if v.endswith(('s', 'm', 'h', 'd')):
                return v
                
            raise ValueError(f"Invalid timestamp format: {v}. Expected ISO 8601, relative time, or Unix timestamp")
            
        raise ValueError("Timestamp must be a string, datetime, or integer")
    # Removed duplicate fields that were causing validation issues
    
    @field_validator('since', 'until', pre=True)
    def parse_timestamp(cls, v):
        """Parse timestamp strings to datetime objects."""
        if isinstance(v, str):
            try:
                # Try parsing as ISO format
                return datetime.fromisoformat(v)
            except ValueError:
                try:
                    # Try parsing as Unix timestamp
                    return datetime.fromtimestamp(int(v))
                except (ValueError, TypeError):
                    pass
        return v

class LogEntry(BaseModel):
    """
    A single log entry from a container.
    
    Attributes:
        timestamp: When the log entry was created (if available)
        stream: Which stream the log came from ('stdout' or 'stderr')
        line: The log line content
        raw: Raw log bytes (if include_raw was True in the request)
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2023-01-01T12:00:00Z",
                "stream": "stdout",
                "line": "Server started on port 8080",
                "raw": "SGVsbG8gd29ybGQh"
            }
        }
    )
    
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When the log entry was created (if available)"
    )
    stream: str = Field(
        ...,
        pattern="^(stdout|stderr)$",
        description="Which stream the log came from ('stdout' or 'stderr')"
    )
    line: str = Field(
        ...,
        description="The log line content"
    )
    raw: Optional[bytes] = Field(
        default=None,
        description="Raw log bytes (if include_raw was True in the request)",
        exclude=True  # Don't include in JSON by default
    )
    
class ContainerLogsResponse(BaseModel):
    """
    Response model for container logs.
    
    Attributes:
        success: Whether the operation was successful
        message: Human-readable status message
        container_id: ID of the container
        logs: List of log entries (if successful)
        error: Error message if the operation failed
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Successfully retrieved logs",
                "container_id": "a1b2c3d4e5f6",
                "logs": [
                    {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "stream": "stdout",
                        "line": "Server started on port 8080"
                    }
                ]
            }
        }
    )
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable status message")
    container_id: str = Field(..., description="ID of the container")
    logs: List[LogEntry] = Field(
        default_factory=list,
        description="List of log entries (if successful)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the operation failed"
    )

@Tool.register(
    name="stream_container_logs",
    description="Stream logs from a Docker container in real-time with filtering options"
)
async def stream_container_logs(
    request: ContainerLogsRequest
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream logs from a Docker container in real-time.
    
    Args:
        request: ContainerLogsRequest with the following parameters:
            - container_id: ID or name of the container to stream logs from
            - follow: Whether to follow log output (like tail -f)
            - tail: Number of lines to show from the end of the logs
            - since: Show logs since this timestamp or relative time in seconds
            - until: Show logs before this timestamp or relative time in seconds
            - timestamps: Include timestamps in the output
            - stream_type: Which streams to include (stdout, stderr, or all)
            - include_raw: Whether to include raw log bytes in the response
            - timeout: Timeout in seconds for the log stream
            
    Yields:
        Dictionary with log entry details:
        {
            'container_id': str,
            'timestamp': datetime,
            'stream': str,  # 'stdout' or 'stderr'
            'line': str,    # The log line content
            'raw': bytes    # Raw log line bytes (if include_raw=True)
        }
        
    Raises:
        ToolError: If there's an error accessing the container logs
    """
    container_id = request.container_id
    
    try:
        # Initialize Docker client
        docker_client = aiodocker.Docker()
        
        # Get container logs
        logs = await docker_client.containers.log(
            container_id,
            stdout=request.stream_type in [LogStreamType.STDOUT, LogStreamType.ALL],
            stderr=request.stream_type in [LogStreamType.STDERR, LogStreamType.ALL],
            follow=request.follow,
            tail=request.tail,
            since=request.since,
            until=request.until,
            timestamps=request.timestamps
        )
        
        # Process and yield log entries
        async for log_line in logs:
            parsed = _parse_log_line(log_line, include_timestamps=request.timestamps)
            if parsed:
                yield {
                    'container_id': container_id,
                    **parsed,
                    'raw': log_line if request.include_raw else None
                }
                
    except aiodocker.DockerError as e:
        if 'No such container' in str(e):
            raise ToolError(f'Container not found: {container_id}') from e
        raise ToolError(f'Docker API error: {str(e)}') from e
    except Exception as e:
        raise ToolError(f'Unexpected error: {str(e)}') from e

def get_tools() -> List[Tool]:
    """
    Get all tools defined in this module for registration with FastMCP.
    
    Returns:
        List of Tool instances to register with FastMCP
        
    Example:
        >>> from dockermcp.tools.containers import container_logs
        >>> tools = container_logs.get_tools()
        >>> assert len(tools) == 1
        >>> assert tools[0].name == "stream_container_logs"
    """
    return [stream_container_logs]


def _parse_log_line(line: bytes, include_timestamps: bool = False) -> Optional[Dict[str, Any]]:
    """
    Parse a single log line from Docker's log format.
    
    Docker log format is typically 8 bytes of header followed by the log message:
    - First byte: Log type (1=stdout, 2=stderr)
    - Next 3 bytes: Reserved
    - Next 4 bytes: Message size (big-endian uint32)
    
    Args:
        line: Raw log line bytes from Docker
        include_timestamps: Whether to include timestamps in the output
        
    Returns:
        Dictionary with parsed log entry or None if line is invalid:
        {
            'timestamp': datetime,  # Only if include_timestamps=True
            'stream': str,         # 'stdout' or 'stderr'
            'line': str,           # The log line content
            'raw': bytes           # Original raw line
        }
        
    Raises:
        ValueError: If the log line format is invalid
    """
    """
    Parse a single log line from Docker's log format.
    
    Docker log format is typically 8 bytes of header followed by the log message:
    - First byte: Log type (1=stdout, 2=stderr)
    - Next 3 bytes: Reserved
    - Next 4 bytes: Message size (big-endian uint32)
    
    Args:
        line: Raw log line bytes from Docker
        include_timestamps: Whether to include timestamps in the output
        
    Returns:
        Dictionary with parsed log entry or None if line is invalid:
        {
            'timestamp': datetime,  # Only if include_timestamps=True
            'stream': str,         # 'stdout' or 'stderr'
            'line': str,           # The log line content
            'raw': bytes           # Original raw line
        }
        
    Raises:
        ValueError: If the log line format is invalid
    """
    try:
        # Docker log format: b'2021-01-01T00:00:00.000000000Z This is a log line\n'
        # Skip empty lines
        if not line.strip():
            return None
            
        timestamp = None
        stream = 'stdout'
        log_line = line.decode('utf-8', errors='replace').strip()
        
        # Check if this is a log with a timestamp
        if log_line.startswith('20'):  # Starts with year
            parts = log_line.split(' ', 1)
            if len(parts) == 2 and 'Z' in parts[0]:
                try:
                    timestamp_str = parts[0].split('.')[0]  # Remove nanoseconds
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                    log_line = parts[1].strip()
                except (ValueError, IndexError):
                    pass
        
        # Check if this is a stderr log (Docker prefixes with stderr)
        if log_line.startswith('stderr '):
            stream = 'stderr'
            log_line = log_line[6:].strip()
        
        return LogEntry(
            timestamp=timestamp if include_timestamps else None,
            stream=stream,
            line=log_line
        )
    except Exception as e:
        # If we can't parse the log line, return it as-is
        return LogEntry(
            stream='stdout',
            line=f'[Log parse error] {line}'
        )
