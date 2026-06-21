"""
Container logs functionality for Docker MCP.

This module provides tools for streaming container logs in real-time with
support for filtering by time, stream type, and more. It follows FastMCP 2.12+
standards for tool registration and error handling.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import docker
from docker.errors import APIError, DockerException, NotFound
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, field_validator

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

from .models import ContainerLogsResponse


class LogStreamType(StrEnum):
    """Log stream types for container logs."""

    STDOUT = "stdout"
    STDERR = "stderr"
    ALL = "all"


class ContainerLogsRequest(BaseModel):
    """Request model for container logs."""

    container_id: str = Field(..., description="ID or name of the container")
    follow: bool = Field(False, description="Follow log output (like tail -f)")
    tail: str = Field("100", description="Number of lines to show from the end (e.g., '100', 'all')")
    since: str | None = Field(None, description="Show logs since this timestamp (ISO 8601) or relative (e.g., 5m, 2h)")
    until: str | None = Field(None, description="Show logs before this timestamp (ISO 8601) or relative time")
    timestamps: bool = Field(False, description="Include timestamps in the log output")
    stream_type: str = Field("all", description="Which log streams to include (stdout, stderr, or all)")
    timeout: int = Field(60, ge=1, le=3600, description="Timeout in seconds for the log stream (1-3600)")

    @field_validator("stream_type")
    @classmethod
    def validate_stream_type(cls, v: str) -> str:
        """Validate the stream_type parameter."""
        try:
            return LogStreamType(v.lower()).value
        except ValueError:
            valid_types = [e.value for e in LogStreamType]
            raise ValueError(f"Invalid stream_type: {v}. Must be one of: {', '.join(valid_types)}") from None


class LogEntry(BaseModel):
    """A single log entry with timestamp and stream information."""

    timestamp: str
    stream: str
    line: str


@mcp.tool
async def get_container_logs(params: ContainerLogsRequest) -> ContainerLogsResponse:
    """
    Retrieve logs from a Docker container with various filtering options.

    This function provides a flexible interface for retrieving container logs with support for:
    - Real-time log following (like tail -f)
    - Time-based filtering (since/until)
    - Stream filtering (stdout/stderr)
    - Configurable output format

    Args:
        params: ContainerLogsRequest containing log retrieval parameters

    Returns:
        ContainerLogsResponse with the log data and metadata
    """
    try:
        # Initialize Docker client
        client = docker.from_env()

        try:
            container = client.containers.get(params.container_id)
        except NotFound as e:
            return ContainerLogsResponse.error_response(
                container_id=params.container_id,
                error=f"Container not found: {e!s}",
                message=f"Container {params.container_id} not found",
            )

        # Prepare log parameters
        log_params = {
            "stdout": params.stream_type in [LogStreamType.STDOUT, LogStreamType.ALL],
            "stderr": params.stream_type in [LogStreamType.STDERR, LogStreamType.ALL],
            "follow": params.follow,
            "tail": params.tail,
            "since": params.since,
            "until": params.until,
            "timestamps": params.timestamps,
            "stream": params.follow,  # Return a generator if following
        }

        # Clean up None values
        log_params = {k: v for k, v in log_params.items() if v is not None}

        # Get logs
        if params.follow:
            # For following logs, collect logs for a limited time
            logs = []
            try:
                async for log_entry in _stream_logs(container, log_params, params.timeout):
                    logs.append(log_entry)
                    if len(logs) >= 1000:  # Safety limit
                        break
            except TimeoutError:
                logger.info(f"Log stream timed out after {params.timeout} seconds")

            return ContainerLogsResponse.success(
                container_id=params.container_id, logs=logs, message=f"Collected {len(logs)} log entries"
            )
        else:
            # For one-time log retrieval
            try:
                raw_logs = container.logs(**log_params).decode("utf-8", errors="replace")
                logs = [
                    {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "stream": params.stream_type if params.stream_type != "all" else "stdout",
                        "line": line,
                    }
                    for line in raw_logs.splitlines()
                    if line.strip()
                ]

                return ContainerLogsResponse.success(
                    container_id=params.container_id, logs=logs, message=f"Retrieved {len(logs)} log entries"
                )
            except APIError as e:
                raise ToolError(f"Failed to get logs: {e!s}") from e

    except (DockerException, APIError) as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg, exc_info=True)
        return ContainerLogsResponse.error_response(
            container_id=params.container_id, error=error_msg, message="Failed to retrieve container logs"
        )
    except Exception as e:
        error_msg = f"Unexpected error: {e!s}"
        logger.error(error_msg, exc_info=True)
        return ContainerLogsResponse.error_response(
            container_id=params.container_id, error=error_msg, message="An unexpected error occurred"
        )


async def _stream_logs(container, log_params: dict[str, Any], timeout: int) -> AsyncGenerator[dict[str, str], None]:
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
        start_time = datetime.now(UTC)

        for log_chunk in log_stream:
            # Check for timeout
            if (datetime.now(UTC) - start_time).total_seconds() > timeout:
                logger.warning(f"Log stream timed out after {timeout} seconds")
                break

            try:
                # Parse the log line (Docker's log format)
                if len(log_chunk) > 8:
                    stream_type = {1: "stdout", 2: "stderr"}.get(log_chunk[0], "unknown")
                    log_line = log_chunk[8:].decode("utf-8", errors="replace").strip()

                    if log_line:  # Skip empty lines
                        yield {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "stream": stream_type,
                            "line": log_line,
                        }
            except Exception as e:
                logger.error(f"Error parsing log chunk: {e!s}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in log stream: {e!s}", exc_info=True)
        raise
    finally:
        # Ensure the log stream is properly closed
        if "log_stream" in locals():
            try:
                log_stream.close()
            except Exception as e:
                logger.warning(f"Error closing log stream: {e!s}")


# Register the tool with MCP
__all__ = ["get_container_logs"]
