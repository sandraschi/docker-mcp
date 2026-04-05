"""
Container command execution for Docker MCP.

This module provides tools for executing commands in running Docker containers
with support for both synchronous and streaming execution modes. It follows
FastMCP 2.12+ standards for tool registration and error handling.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

import docker
from docker.errors import APIError, DockerException, NotFound
from pydantic import Field

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

from .models import ContainerExecResponse


class StreamType(StrEnum):
    """Output stream types for command execution."""
    STDOUT = "stdout"
    STDERR = "stderr"
    BOTH = "both"

class ExecUser(StrEnum):
    """Special user values for command execution."""
    ROOT = "root"
    CONTAINER_DEFAULT = ""

@mcp.tool
async def execute_in_container(
    container_id: Annotated[str, Field(description="ID or name of the container")],
    command: Annotated[str | list[str], Field(description="Command to execute (string or list of arguments)")],
    user: Annotated[str, Field(description="User to run the command as (empty for container default, 'root' for root)", default="")],
    workdir: Annotated[str | None, Field(description="Working directory inside the container", default=None)],
    environment: Annotated[dict[str, str], Field(description="Environment variables for the command", default={})],
    privileged: Annotated[bool, Field(description="Run with extended privileges (use with caution)", default=False)],
    tty: Annotated[bool, Field(description="Allocate a pseudo-TTY (required for interactive commands)", default=False)],
    stream: Annotated[bool, Field(description="Stream command output in real-time", default=False)],
    stream_type: Annotated[str, Field(description="Which streams to capture (stdout, stderr, or both)", default="both")],
    detach: Annotated[bool, Field(description="Run command in background (returns immediately)", default=False)],
    stdin: Annotated[bool, Field(description="Open stdin for the command (required for interactive input)", default=False)],
    timeout: Annotated[int, Field(description="Timeout in seconds for command execution (1-3600)", default=60, ge=1, le=3600)]
) -> ContainerExecResponse:
    """
    Execute a command in a running Docker container.

    This function provides a flexible interface for executing commands in containers
    with support for both synchronous and streaming execution modes.

    Security Notes:
    - Avoid using privileged mode unless absolutely necessary
    - Always validate and sanitize command inputs
    - Use the principle of least privilege when specifying users
    - Be cautious with environment variables that may contain sensitive data

    Args:
        container_id: ID or name of the container
        command: Command to execute (string or list of arguments)
        user: User to run the command as (empty for container default, "root" for root)
        workdir: Working directory inside the container
        environment: Environment variables for the command
        privileged: Run with extended privileges (use with caution)
        tty: Allocate a pseudo-TTY (required for interactive commands)
        stream: Stream command output in real-time
        stream_type: Which streams to capture (stdout, stderr, or both)
        detach: Run command in background (returns immediately)
        stdin: Open stdin for the command (required for interactive input)
        timeout: Timeout in seconds for command execution (1-3600)

    Returns:
        ContainerExecResponse with command execution results or stream information

    Example:
        # Synchronous execution
        >>> result = await execute_in_container(
        ...     container_id="my-container",
        ...     command=["ls", "-l", "/app"],
        ...     stream=False
        ... )
        >>> print(result.output)  # Command output
        >>> print(result.exit_code)  # Exit code

        # Error handling
        >>> if result.status == 'error':
        ...     print(f"Error: {result.error}")
        ... else:
        ...     print(f"Success: {result.message}")
    """
    try:
        # Validate stream_type
        try:
            stream_type_enum = StreamType(stream_type.lower())
        except ValueError:
            valid_types = [e.value for e in StreamType]
            error_msg = f"Invalid stream_type: {stream_type}. Must be one of: {', '.join(valid_types)}"
            return ContainerExecResponse.error(
                error=error_msg,
                container_id=container_id,
                message=error_msg
            )

        # Initialize Docker client
        try:
            client = docker.from_env()
            container = client.containers.get(container_id)
        except NotFound:
            error_msg = f"Container not found: {container_id}"
            logger.error(error_msg)
            return ContainerExecResponse.error(
                error=error_msg,
                container_id=container_id,
                message=error_msg
            )

        # Prepare exec parameters
        exec_params = {
            'cmd': command if isinstance(command, list) else command.split(),
            'user': user if user != ExecUser.CONTAINER_DEFAULT else '',
            'workdir': workdir,
            'environment': environment or None,
            'privileged': privileged,
            'tty': tty,
            'stdin': stdin,
            'stdout': stream_type_enum in [StreamType.STDOUT, StreamType.BOTH],
            'stderr': stream_type_enum in [StreamType.STDERR, StreamType.BOTH],
            'detach': detach
        }

        # Clean up None values
        exec_params = {k: v for k, v in exec_params.items() if v is not None}

        # Execute the command
        exec_id = container.client.api.exec_create(container.id, **exec_params)

        if stream:
            # For streaming, return the generator
            return ContainerExecResponse.success(
                exec_id=exec_id['Id'],
                container_id=container_id,
                output="",  # No output for streaming mode
                message="Command execution started in streaming mode"
            )
        else:
            # For non-streaming execution, get the output directly
            if detach:
                container.client.api.exec_start(exec_id, stream=False, detach=True)
                return ContainerExecResponse.success(
                    exec_id=exec_id['Id'],
                    container_id=container_id,
                    output="",  # No output for detached mode
                    message="Command started in detached mode"
                )

            # Get the output and exit code
            result = container.client.api.exec_start(exec_id['Id'], stream=False, demux=True)
            stdout_data = result[0].decode('utf-8') if result[0] else ""
            stderr_data = result[1].decode('utf-8') if result[1] else ""

            # Get the exit code
            inspect_data = container.client.api.exec_inspect(exec_id['Id'])
            exit_code = inspect_data.get('ExitCode', -1)

            if exit_code == 0:
                return ContainerExecResponse.success(
                    exec_id=exec_id['Id'],
                    container_id=container_id,
                    output=stdout_data + (f"\n{stderr_data}" if stderr_data else ""),
                    exit_code=exit_code,
                    message="Command executed successfully"
                )
            return ContainerExecResponse.error(
                error=f"Command failed with exit code {exit_code}",
                container_id=container_id,
                exec_id=exec_id['Id'],
                message=stderr_data or "Command execution failed"
            )
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return ContainerExecResponse.error(
            error=error_msg,
            container_id=container_id,
            message="Docker API error"
        )

    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return ContainerExecResponse.error(
            error=error_msg,
            container_id=container_id,
            message="Docker daemon not available"
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error executing command in container {container_id}: {error_msg}")
        return ContainerExecResponse.error(
            error=error_msg,
            container_id=container_id,
            message=f"Failed to execute command: {error_msg}"
        )

async def _stream_exec_output(
    docker_client: docker.DockerClient,
    exec_id: str,
    timeout: int
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Stream command output from a Docker exec instance.

    Args:
        docker_client: Docker client instance
        exec_id: Exec instance ID
        timeout: Timeout in seconds

    Yields:
        Dictionary with stream data:
        {
            'type': 'stdout'|'stderr',
            'data': str,
            'timestamp': str (ISO 8601)
        }
    """
    try:
        # Start the exec instance with streaming
        socket = docker_client.api.exec_start(exec_id, socket=True)

        # Set a timeout for the entire stream
        start_time = datetime.now()

        try:
            while True:
                # Check for timeout
                if (datetime.now() - start_time).total_seconds() > timeout:
                    logger.warning(f"Command execution timed out after {timeout} seconds")
                    yield {
                        'type': 'stderr',
                        'data': f'Command timed out after {timeout} seconds',
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }
                    break

                # Read from the socket
                try:
                    data = socket._sock.recv(8192)
                    if not data:
                        break

                    # Parse the Docker stream format (8-byte header + data)
                    if len(data) > 8:
                        stream_type = {1: 'stdout', 2: 'stderr'}.get(data[0], 'stdout')
                        output = data[8:].decode('utf-8', errors='replace')

                        if output:
                            yield {
                                'type': stream_type,
                                'data': output,
                                'timestamp': datetime.utcnow().isoformat() + 'Z'
                            }

                    # Small sleep to prevent high CPU usage
                    await asyncio.sleep(0.01)

                except (BlockingIOError, TimeoutError):
                    await asyncio.sleep(0.1)
                    continue

        finally:
            # Clean up the socket
            try:
                socket.close()
            except:
                pass

    except Exception as e:
        logger.error(f"Error in command output stream: {str(e)}")
        yield {
            'type': 'stderr',
            'data': f'Error in command output stream: {str(e)}',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
