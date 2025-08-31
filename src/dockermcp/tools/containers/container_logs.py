"""
Container logs streaming for Docker MCP.

Provides tools for streaming container logs in real-time.
"""
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from datetime import datetime
import json
import logging
from fastmcp.tools import Tool
from fastmcp.types import Param, Return, Stream
from pydantic import BaseModel, Field, field_validator, ConfigDict
from docker.models.containers import Container
import docker
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

class LogStreamType(str, Enum):
    """Log stream types."""
    STDOUT = "stdout"
    STDERR = "stderr"
    ALL = "all"

class ContainerLogsRequest(BaseModel):
    """Request model for container logs."""
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    follow: bool = Field(
        default=True,
        description="Follow log output (like tail -f)"
    )
    tail: Optional[int] = Field(
        default=100,
        ge=1,
        description="Number of lines to show from the end of the logs"
    )
    since: Optional[Union[datetime, int]] = Field(
        default=None,
        description="Show logs since this timestamp or relative time in seconds"
    )
    until: Optional[Union[datetime, int]] = Field(
        default=None,
        description="Show logs before this timestamp or relative time in seconds"
    )
    timestamps: bool = Field(
        default=False,
        description="Show timestamps in logs"
    )
    stream_type: str = Field(
        default="all",
        description="Filter logs by stream type (stdout, stderr, all)"
    )
    
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
    """A single log entry."""
    timestamp: Optional[datetime] = None
    stream: str
    line: str
    
class ContainerLogsResponse(BaseModel):
    """Response model for container logs."""
    success: bool
    message: str
    container_id: str
    logs: List[LogEntry] = []
    error: Optional[str] = None

@Tool(
    name="stream_container_logs",
    description="Stream logs from a container in real-time",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID or name of the container"
            },
            "follow": {
                "type": "boolean",
                "default": True,
                "description": "Follow log output (like tail -f)"
            },
            "tail": {
                "type": "integer",
                "minimum": 1,
                "default": 100,
                "description": "Number of lines to show from the end of the logs"
            },
            "since": {
                "type": ["string", "integer", "null"],
                "default": None,
                "description": "Show logs since this timestamp (ISO format) or relative time in seconds"
            },
            "until": {
                "type": ["string", "integer", "null"],
                "default": None,
                "description": "Show logs before this timestamp (ISO format) or relative time in seconds"
            },
            "timestamps": {
                "type": "boolean",
                "default": False,
                "description": "Show timestamps in logs"
            },
            "stream_type": {
                "type": "string",
                "enum": ["stdout", "stderr", "all"],
                "default": "all",
                "description": "Filter logs by stream type"
            }
        },
        "required": ["container_id"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "container_id": {"type": "string"},
            "logs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": ["string", "null"], "format": "date-time"},
                        "stream": {"type": "string"},
                        "line": {"type": "string"}
                    },
                    "required": ["stream", "line"]
                }
            },
            "error": {"type": ["string", "null"]}
        },
        "required": ["success", "message", "container_id", "logs"]
    },
    examples=[
        {
            "name": "Stream logs with default settings",
            "input": {
                "container_id": "my-container"
            },
            "output": {
                "success": True,
                "message": "Streaming logs for container my-container",
                "container_id": "my-container",
                "logs": [
                    {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "stream": "stdout",
                        "line": "Log message 1"
                    },
                    {
                        "timestamp": "2023-01-01T12:00:01Z",
                        "stream": "stderr",
                        "line": "Error message 1"
                    }
                ],
                "error": None
            }
        },
        {
            "name": "Get last 50 logs without following",
            "input": {
                "container_id": "my-container",
                "follow": False,
                "tail": 50
            },
            "output": {
                "success": True,
                "message": "Retrieved logs for container my-container",
                "container_id": "my-container",
                "logs": [
                    {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "stream": "stdout",
                        "line": "Log message 1"
                    }
                ],
                "error": None
            }
        }
    ]
)
async def stream_container_logs(
    container_id: str = Param(..., description="ID or name of the container"),
    follow: bool = Param(True, description="Follow log output (like tail -f)"),
    tail: Optional[int] = Param(100, description="Number of lines to show from the end of the logs"),
    since: Optional[Union[datetime, int]] = Param(None, description="Show logs since this timestamp or relative time in seconds"),
    until: Optional[Union[datetime, int]] = Param(None, description="Show logs before this timestamp or relative time in seconds"),
    timestamps: bool = Param(False, description="Show timestamps in logs"),
    stream_type: str = Param("all", description="Filter logs by stream type (stdout, stderr, all)")
) -> Return[Dict[str, Any]]:
    """
    Stream logs from a container.
    
    Args:
        container_id: ID or name of the container
        follow: Follow log output (like tail -f)
        tail: Number of lines to show from the end of the logs
        since: Show logs since this timestamp or relative time in seconds
        until: Show logs before this timestamp or relative time in seconds
        timestamps: Show timestamps in logs
        stream_type: Filter logs by stream type (stdout, stderr, all)
        
    Yields:
        Dictionary with log entries and metadata
    """
    client = docker.from_env()
    
    try:
        container = client.containers.get(container_id)
        
        # Convert timestamps to Unix timestamps if they're datetime objects
        since_ts = since.timestamp() if isinstance(since, datetime) else since
        until_ts = until.timestamp() if isinstance(until, datetime) else until
        
        # Get logs from the container
        logs = container.logs(
            stdout=stream_type in [LogStreamType.STDOUT, LogStreamType.ALL],
            stderr=stream_type in [LogStreamType.STDERR, LogStreamType.ALL],
            stream=follow,
            tail=tail,
            since=since_ts,
            until=until_ts,
            timestamps=timestamps,
            follow=follow
        )
        
        if not follow:
            # For non-streaming, return all logs at once
            logs = [logs] if not isinstance(logs, list) else logs
            
            for line in logs:
                if not line:
                    continue
                    
                # Parse the log line (format: b'2021-01-01T00:00:00.000000000Z This is a log line\n')
                log_entry = _parse_log_line(line, timestamps)
                if log_entry:
                    yield {
                        'success': True,
                        'container_id': container_id,
                        'log': log_entry.dict()
                    }
        else:
            # For streaming, yield logs as they come in
            for line in logs:
                if not line:
                    continue
                    
                log_entry = _parse_log_line(line, timestamps)
                if log_entry:
                    yield {
                        'success': True,
                        'container_id': container_id,
                        'log': log_entry.dict()
                    }
                    
    except docker.errors.NotFound:
        yield {
            'success': False,
            'container_id': container_id,
            'error': 'Container not found'
        }
    except docker.errors.APIError as e:
        yield {
            'success': False,
            'container_id': container_id,
            'error': f'Docker API error: {str(e)}'
        }
    except Exception as e:
        yield {
            'success': False,
            'container_id': container_id,
            'error': f'Unexpected error: {str(e)}'
        }

def _parse_log_line(line: bytes, include_timestamps: bool = False) -> Optional[LogEntry]:
    """Parse a single log line from Docker's log format."""
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
