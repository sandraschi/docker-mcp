"""
Container command execution for Docker MCP.

This module provides tools for executing commands in running Docker containers
with full support for FastMCP 2.12+ standards. It includes features for both
synchronous and streaming command execution with comprehensive error handling,
logging, and security best practices.
"""
from __future__ import annotations

import asyncio
import logging
import traceback
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import (
    Dict, Any, Optional, List, Union, AsyncGenerator, 
    cast, TypeVar, Type, Callable, Awaitable, ParamSpec, Tuple
)
from contextlib import asynccontextmanager

# Pydantic models
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator, ValidationError

# Docker SDK
import aiodocker
import docker
from aiodocker.exceptions import DockerError
from aiodocker.execs import Exec
from docker.errors import APIError, NotFound, ImageNotFound, ContainerError

# FastMCP imports
from fastmcp.tools import Tool, tool

# Import custom exceptions
from .container_models import ContainerError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Type variables for type hints
T = TypeVar('T', bound=BaseModel)
P = ParamSpec('P')
R = TypeVar('R')

def handle_exec_errors(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """
    Decorator to handle Docker exec errors and standardize error responses.
    
    Args:
        func: The async function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except ValidationError as ve:
            error_msg = f"Command execution validation error: {str(ve)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from ve
        except NotFound as nf:
            error_msg = f"Container not found: {str(nf)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from nf
        except ContainerError as ce:
            error_msg = f"Container error during command execution: {str(ce)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from ce
        except APIError as ae:
            error_msg = f"Docker API error during command execution: {str(ae)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from ae
        except DockerError as de:
            error_msg = f"Docker error during command execution: {str(de)}"
            logger.error(f"{func.__name__} - {error_msg}")
            raise ContainerError(error_msg) from de
        except asyncio.CancelledError:
            logger.info("Command execution was cancelled")
            raise
        except Exception as e:
            error_msg = f"Unexpected error in {func.__name__}: {str(e)}"
            logger.error(f"{func.__name__} - {error_msg}\n{traceback.format_exc()}")
            raise ContainerError(f"Internal server error: {str(e)}") from e
    return wrapper

@asynccontextmanager
async def get_docker_client():
    """Context manager for Docker client with proper cleanup."""
    client = None
    try:
        client = docker.from_env()
        yield client
    except Exception as e:
        error_msg = f"Failed to initialize Docker client: {str(e)}"
        logger.error(error_msg)
        raise ContainerError(error_msg) from e
    finally:
        if client is not None:
            client.close()

class ExecStreamType(str, Enum):
    """
    Output stream types for command execution.
    
    Attributes:
        STDOUT: Capture only standard output
        STDERR: Capture only standard error
        BOTH: Capture both standard output and error
    """
    STDOUT = "stdout"
    STDERR = "stderr"
    BOTH = "both"
    
    @classmethod
    def get_description(cls, stream_type: 'ExecStreamType') -> str:
        """Get a human-readable description of the stream type."""
        descriptions = {
            cls.STDOUT: "Standard output only",
            cls.STDERR: "Standard error only",
            cls.BOTH: "Both standard output and error"
        }
        return descriptions.get(stream_type, f"Unknown stream type: {stream_type}")

class ExecUser(str, Enum):
    """
    Special user values for command execution.
    
    Attributes:
        ROOT: Run as root user
        CONTAINER_DEFAULT: Use the container's default user
    """
    ROOT = "root"
    CONTAINER_DEFAULT = ""

class ContainerExecRequest(BaseModel):
    """
    Request model for container command execution.
    
    Attributes:
        container_id: ID or name of the container
        command: Command to execute (string or list of args)
        user: User to run the command as
        workdir: Working directory inside the container
        environment: Environment variables for the command
        privileged: Run with extended privileges
        tty: Allocate a pseudo-TTY
        stream: Stream command output in real-time
        stream_type: Which streams to capture
        detach: Run command in background
        stdin: Open stdin for the command
        socket: Return connection to the command's socket
        demux: Return stdout and stderr separately
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "my-container",
                "command": ["ls", "-l", "/app"],
                "user": "root",
                "workdir": "/app",
                "environment": {"DEBUG": "true"},
                "privileged": False,
                "tty": False,
                "stream": True,
                "stream_type": "both",
                "detach": False,
                "stdin": False,
                "socket": False,
                "demux": True
            }
        }
    )
    
    container_id: str = Field(
        ...,
        min_length=1,
        description="ID or name of the container"
    )
    command: Union[str, List[str]] = Field(
        ...,
        description="Command to execute (string or list of arguments)",
        min_length=1
    )
    user: Union[str, ExecUser] = Field(
        default=ExecUser.CONTAINER_DEFAULT,
        description=f"User to run the command as. Can be a username or one of: {', '.join([e.value for e in ExecUser] + ['<username>'])}"
    )
    workdir: Optional[str] = Field(
        default=None,
        description="Working directory inside the container (default: container's working directory)"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set for the command"
    )
    privileged: bool = Field(
        default=False,
        description="Run the command with extended privileges (use with caution)"
    )
    tty: bool = Field(
        default=False,
        description="Allocate a pseudo-TTY (required for interactive commands)"
    )
    stream: bool = Field(
        default=False,
        description="Stream command output in real-time (useful for long-running commands)"
    )
    stream_type: ExecStreamType = Field(
        default=ExecStreamType.BOTH,
        description=f"Which streams to capture. Options: {', '.join([e.value for e in ExecStreamType])}"
    )
    detach: bool = Field(
        default=False,
        description="If true, the command will run in the background"
    )
    stdin: bool = Field(
        default=False,
        description="Open stdin for the command (required for interactive input)"
    )
    socket: bool = Field(
        default=False,
        description="Return connection to attach to the command's socket (advanced usage)"
    )
    demux: bool = Field(
        default=False,
        description="Return stdout and stderr separately (only applies when stream=False)"
    )
    
    @field_validator('container_id')
    @classmethod
    def validate_container_id(cls, v: str) -> str:
        """Validate container ID is not empty."""
        if not v.strip():
            raise ValueError("Container ID cannot be empty")
        return v.strip()
    
    @field_validator('command')
    @classmethod
    def validate_command(cls, v: Union[str, List[str]]) -> List[str]:
        """Convert command to list if it's a string."""
        if isinstance(v, str):
            return v.split()
        return v

class ExecResult(BaseModel):
    """
    Result of a command execution.
    
    Attributes:
        exit_code: The exit code of the command (0 = success, non-zero = error)
        stdout: Standard output from the command
        stderr: Standard error from the command
        output: Combined stdout and stderr (stdout if both are empty)
        success: Whether the command exited with code 0
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exit_code": 0,
                "stdout": "file1.txt\nfile2.txt\n",
                "stderr": "",
                "output": "file1.txt\nfile2.txt\n",
                "success": True
            }
        }
    )
    
    exit_code: int = Field(..., description="The exit code of the command (0 = success, non-zero = error)")
    stdout: str = Field(default="", description="Standard output from the command")
    stderr: str = Field(default="", description="Standard error from the command")
    output: str = Field(default="", description="Combined stdout and stderr (stdout if both are empty)")
    success: bool = Field(default=False, description="Whether the command exited with code 0")
    
    def __init__(self, **data):
        """Initialize ExecResult with automatic success and output handling."""
        super().__init__(**data)
        self.success = self.exit_code == 0
        if not self.output and self.stdout:
            self.output = self.stdout

class ContainerExecResponse(BaseModel):
    """
    Response model for container command execution.
    
    Attributes:
        success: Whether the command execution was successful
        message: Human-readable status message
        container_id: ID of the container
        command: The command that was executed
        result: Detailed execution results (if successful)
        error: Error message if execution failed
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Command executed successfully",
                "container_id": "a1b2c3d4e5f6",
                "command": ["ls", "-l"],
                "result": {
                    "exit_code": 0,
                    "stdout": "total 4\ndrwxr-xr-x 2 root root 4096 Jan 1 00:00 app\n",
                    "stderr": "",
                    "output": "total 4\ndrwxr-xr-x 2 root root 4096 Jan 1 00:00 app\n",
                    "success": True
                }
            }
        }
    )
    
    success: bool = Field(..., description="Whether the command execution was successful")
    message: str = Field(..., description="Human-readable status message")
    container_id: str = Field(..., description="ID of the container")
    command: Union[str, List[str]] = Field(..., description="The command that was executed")
    result: Optional[ExecResult] = Field(
        default=None,
        description="Detailed execution results (only present if successful)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the execution failed"
    )

@tool(
    name="execute_in_container",
    description=(
        "Execute a command in a running container with comprehensive error handling. "
        "Supports both synchronous and streaming execution modes, environment variables, "
        "working directory configuration, and user impersonation."
    ),
    args_schema=ContainerExecRequest,
    return_schema=ContainerExecResponse,
    examples=[
        {
            "container_id": "my-container",
            "command": ["ls", "-l", "/app"],
            "user": "appuser",
            "workdir": "/app",
            "environment": {"DEBUG": "true"},
            "privileged": False,
            "stream": True
        },
        {
            "container_id": "another-container",
            "command": "whoami",
            "stream": False
        }
    ]
)
@handle_exec_errors
async def execute_in_container(
    request: ContainerExecRequest
) -> Union[ContainerExecResponse, AsyncGenerator[Dict[str, Any], None]]:
    """
    Execute a command in a running container with comprehensive error handling.
    
    This function provides a robust interface for executing commands in containers
    with support for:
    - Both synchronous and streaming execution modes
    - Environment variable configuration
    - Working directory specification
    - User impersonation
    - Privileged execution (with proper security considerations)
    - Real-time output streaming
    - Comprehensive error handling and logging
    
    Security Notes:
    - Avoid using privileged mode unless absolutely necessary
    - Always validate and sanitize command inputs
    - Use the principle of least privilege when specifying users
    - Be cautious with environment variables that may contain sensitive data
    
    Args:
        request: ContainerExecRequest with the following parameters:
            - container_id: ID or name of the container
            - command: Command to execute (string or list of args)
            - user: User to run the command as (default: container's default user)
            - workdir: Working directory inside the container
            - environment: Environment variables to set for the command
            - privileged: Run the command with extended privileges (use with caution)
            - tty: Allocate a pseudo-TTY (required for interactive commands)
            - stream: Whether to stream the command output in real-time
            - stream_type: Which streams to capture (stdout, stderr, or both)
            - detach: If true, run the command in the background
            - stdin: Open stdin (required for interactive input)
            - socket: Return connection to attach to the command's socket (advanced)
            - demux: Return stdout and stderr separately (when stream=False)
            
    Returns:
        If stream=True, yields dictionaries with command output in real-time.
        If stream=False, returns a ContainerExecResponse with the full command results.
        
        Example response when stream=False:
        {
            'success': True,
            'message': 'Command executed successfully',
            'container_id': 'a1b2c3d4e5f6',
            'command': ['ls', '-l', '/app'],
            'result': {
                'exit_code': 0,
                'stdout': 'total 4\ndrwxr-xr-x 2 root root 4096 Jan 1 00:00 app\n',
                'stderr': '',
                'output': 'total 4\ndrwxr-xr-x 2 root root 4096 Jan 1 00:00 app\n',
                'success': True
            }
        }
        
        When stream=True, yields dictionaries with the format:
        {
            'type': 'stdout'|'stderr',
            'data': 'output data',
            'timestamp': 'ISO-8601 timestamp'
        }
        
    Raises:
        ToolException: If there's an error executing the command or the container is not found
        
    Example:
        # Synchronous execution
        response = await execute_in_container(ContainerExecRequest(
            container_id='my-container',
            command=['ls', '-l', '/app'],
            stream=False
        ))
        
        # Streaming execution
        async for chunk in execute_in_container(ContainerExecRequest(
            container_id='my-container',
            command=['tail', '-f', '/var/log/app.log'],
            stream=True
        )):
            logger.info(f"{chunk['type']}: {chunk['data']}")
    """
    logger.info(
        f"Executing command in container {request.container_id}: {request.command}"
        f" (user={request.user}, workdir={request.workdir}, privileged={request.privileged})"
    )
    # Extract parameters from request
    container_id = request.container_id
    command = request.command
    user = request.user.value if hasattr(request.user, 'value') else request.user
    workdir = request.workdir
    environment = request.environment or {}
    detach = request.detach
    tty = request.tty
    stream = request.stream
    stdin = request.stdin
    socket = request.socket
    demux = request.demux
    output_type = request.output_type.value if hasattr(request.output_type, 'value') else request.output_type
    privileged = request.privileged
    stream_type = request.stream_type
    """
    Execute a command inside a container.
    
    Args:
        container_id: ID or name of the container
        command: Command to execute (string or list of args)
        user: User to run the command as
        workdir: Working directory inside the container
        environment: Environment variables to set
        stream: Stream command output in real-time
        stream_type: Which streams to capture (stdout, stderr, both)
        tty: Allocate a pseudo-TTY
        privileged: Run in privileged mode
        detach: If true, detach immediately and return without waiting for command completion
        
    Returns:
        Dictionary with command execution results
    """
    client = docker.from_env()
    
    try:
        container = client.containers.get(container_id)
        
        # Prepare environment variables
        env_list = None
        if environment:
            env_list = [f"{k}={v}" for k, v in environment.items()]
        
        # Prepare user
        user_str = str(user) if user != ExecUser.CONTAINER_DEFAULT else ""
        
        # Create exec instance
        exec_id = container.client.api.exec_create(
            container.id,
            command,
            user=user_str,
            workdir=workdir,
            environment=env_list,
            tty=tty,
            privileged=privileged,
            stdout=stream_type in [ExecStreamType.STDOUT, ExecStreamType.BOTH],
            stderr=stream_type in [ExecStreamType.STDERR, ExecStreamType.BOTH],
            stdin=False
        )
        
        # Start the exec instance
        if detach:
            container.client.api.exec_start(exec_id['Id'], detach=True)
            return ContainerExecResponse(
                success=True,
                message=f'Command started in detached mode in container {container_id}',
                container_id=container_id,
                command=command,
                result=ExecResult(
                    exit_code=0,
                    stdout="",
                    stderr="",
                    output="Command running in detached mode"
                )
            ).model_dump()
        
        if stream:
            # Stream output in real-time
            output = []
            result = ExecResult(exit_code=0, stdout="", stderr="", output="")
            stdout_data = []
            stderr_data = []
            
            for line in container.client.api.exec_start(
                exec_id['Id'],
                stream=True,
                demux=True
            ):
                if line[0]:  # stdout
                    line_str = line[0].decode('utf-8', errors='replace')
                    stdout_data.append(line_str)
                    output.append(line_str)
                    
                if line[1]:  # stderr
                    line_str = line[1].decode('utf-8', errors='replace')
                    stderr_data.append(line_str)
                    output.append(line_str)
            
            # Get exit code
            inspect = container.client.api.exec_inspect(exec_id['Id'])
            exit_code = inspect.get('ExitCode', -1)
            
            result = ExecResult(
                exit_code=exit_code,
                stdout=''.join(stdout_data),
                stderr=''.join(stderr_data),
                output=''.join(output)
            )
            
            return {
                'success': result.success,
                'message': f'Command executed in container {container_id} with exit code {exit_code}',
                'container_id': container_id,
                'command': command,
                'result': result.dict()
            }
        else:
            try:
                result_output = container.client.api.exec_start(
                    exec_id['Id'],
                    stream=False,
                    tty=tty
                )
                
                # Get the exit code
                inspect_data = container.client.api.exec_inspect(exec_id['Id'])
                exit_code = inspect_data.get('ExitCode', -1)
                
                # Prepare response
                result = ExecResult(
                    exit_code=exit_code,
                    stdout=result_output if exit_code == 0 else "",
                    stderr=result_output if exit_code != 0 else "",
                    output=result_output
                )
                
                response = ContainerExecResponse(
                    success=exit_code == 0,
                    message=f'Command executed with exit code {exit_code} in container {container_id}',
                    container_id=container_id,
                    command=command,
                    result=result,
                    error=None if exit_code == 0 else f'Command failed with exit code {exit_code}'
                )
                
                # Use model_dump() for proper JSON serialization
                return response.model_dump()
                
            except Exception as e:
                logger.error(f"Error executing command in container: {e}", exc_info=True)
                return ContainerExecResponse(
                    success=False,
                    message=f'Failed to execute command in container {container_id}: {str(e)}',
                    container_id=container_id,
                    command=command,
                    error=str(e)
                ).model_dump()
            
    except docker.errors.NotFound:
        error_msg = f"Container {container_id} not found"
        logger.error(error_msg, exc_info=True)
        return ContainerExecResponse(
            success=False,
            message=error_msg,
            container_id=container_id,
            command=command,
            error="Container not found"
        ).model_dump()
    except docker.errors.APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerExecResponse(
            success=False,
            message=error_msg,
            container_id=container_id,
            command=command,
            error=str(e)
        ).model_dump()
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerExecResponse(
            success=False,
            message=error_msg,
            container_id=container_id,
            command=command,
            error=str(e)
        ).model_dump()

