"""
Docker Reconnect Tool - Handles reconnection to Docker daemon.

This module provides functionality to attempt reconnection to the Docker daemon
if the connection is lost.
"""

import asyncio
import logging

from pydantic import BaseModel, Field

from dockermcp.docker_context import docker_available, retry_docker_connection
from dockermcp.mcp_instance import mcp
from dockermcp.tools import ToolResponse

logger = logging.getLogger(__name__)


class ReconnectDockerParams(BaseModel):
    """Parameters for the reconnect_docker tool."""

    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum number of retry attempts")
    retry_delay: float = Field(default=1.0, gt=0, le=60.0, description="Delay between retry attempts in seconds")


class ReconnectDockerResponse(BaseModel):
    """Response model for the reconnect_docker tool."""

    success: bool = Field(..., description="Whether reconnection was successful")
    message: str = Field(..., description="Status message")
    docker_available: bool = Field(..., description="Whether Docker is now available")


@mcp.tool
async def reconnect_docker(params: ReconnectDockerParams) -> ToolResponse[ReconnectDockerResponse]:
    """
    Attempt to reconnect to the Docker daemon.

    Args:
        params: ReconnectDockerParams containing:
            - max_retries: Maximum number of retry attempts (default: 3)
            - retry_delay: Delay between retry attempts in seconds (default: 1.0)

    Returns:
        ToolResponse containing the reconnection status
    """
    try:
        if docker_available:
            return ToolResponse.from_success(
                message="Docker is already available",
                data=ReconnectDockerResponse(
                    success=True, message="Docker is already available", docker_available=True
                ),
            )

        success = False
        for attempt in range(1, params.max_retries + 1):
            try:
                if retry_docker_connection():
                    success = True
                    break
                logger.warning(f"Reconnection attempt {attempt}/{params.max_retries} failed")
                if attempt < params.max_retries:
                    await asyncio.sleep(params.retry_delay)
            except Exception as e:
                logger.error(f"Error during reconnection attempt {attempt}: {e!s}")
                if attempt < params.max_retries:
                    await asyncio.sleep(params.retry_delay)

        if success:
            return ToolResponse.from_success(
                message="Successfully reconnected to Docker daemon",
                data=ReconnectDockerResponse(
                    success=True, message="Successfully reconnected to Docker daemon", docker_available=True
                ),
            )
        else:
            return ToolResponse.from_error(
                message=f"Failed to reconnect to Docker daemon after {params.max_retries} attempts",
                error=Exception("Docker reconnection failed"),
            )

    except Exception as e:
        error_msg = f"Error in reconnect_docker: {e!s}"
        logger.error(error_msg, exc_info=True)
        return ToolResponse.from_error(error_msg, e)


def register_tool():
    """Register the Docker reconnect tool with the MCP server.

    Returns:
        List of tool functions to register
    """
    return [reconnect_docker]
