"""
Container command execution for Docker MCP.

Provides tools for executing commands in running containers.
"""
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
import asyncio
import logging
from fastmcp.tools import Tool
from fastmcp.types import Param, Return, Stream
from pydantic import BaseModel, Field, field_validator, ConfigDict
from docker.models.containers import Container
import docker
import json

# Configure logging
logger = logging.getLogger(__name__)

class ExecStreamType(str, Enum):
    """Output stream types for command execution."""
    STDOUT = "stdout"
    STDERR = "stderr"
    BOTH = "both"

class ExecUser(str, Enum):
    """Special user values for command execution."""
    ROOT = "root"
    CONTAINER_DEFAULT = ""

class ContainerExecRequest(BaseModel):
    """Request model for container command execution."""
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    command: Union[str, List[str]] = Field(
        ...,
        description="Command to execute (string or list of args)"
    )
    user: Optional[Union[str, ExecUser]] = Field(
        default=ExecUser.CONTAINER_DEFAULT,
        description="User to run the command as (default: container's default user)"
    )
    workdir: Optional[str] = Field(
        default=None,
        description="Working directory inside the container"
    )
    environment: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables to set for the command"
    )
    stream: bool = Field(
        default=False,
        description="Stream command output in real-time"
    )
    stream_type: ExecStreamType = Field(
        default=ExecStreamType.BOTH,
        description="Which streams to capture (stdout, stderr, both)"
    )
    tty: bool = Field(
        default=False,
        description="Allocate a pseudo-TTY"
    )
    privileged: bool = Field(
        default=False,
        description="Run in privileged mode"
    )
    detach: bool = Field(
        default=False,
        description="Run in detached mode (returns immediately)"
    )

    @field_validator('command', pre=True)
    def parse_command(cls, v):
        """Parse command string into list if needed."""
        if isinstance(v, str):
            # Simple split that handles quoted strings
            import shlex
            return shlex.split(v)
        return v

class ExecResult(BaseModel):
    """Result of a command execution."""
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    output: str = ""
    success: bool = False

    def __init__(self, **data):
        super().__init__(**data)
        self.success = self.exit_code == 0
        if not self.output and self.stdout:
            self.output = self.stdout

class ContainerExecResponse(BaseModel):
    """Response model for container command execution."""
    success: bool
    message: str
    container_id: str
    command: Union[str, List[str]]
    result: Optional[ExecResult] = None
    error: Optional[str] = None

@Tool(
    name="execute_in_container",
    description="Execute a command inside a running container",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID or name of the container"
            },
            "command": {
                "type": ["string", "array"],
                "items": {"type": "string"},
                "description": "Command to execute (string or list of args)"
            },
            "user": {
                "type": "string",
                "default": "",
                "description": "User to run the command as (default: container's default user)"
            },
            "workdir": {
                "type": "string",
                "default": "",
                "description": "Working directory inside the container"
            },
            "environment": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "default": {},
                "description": "Environment variables to set for the command"
            },
            "stream": {
                "type": "boolean",
                "default": False,
                "description": "Stream command output in real-time"
            },
            "stream_type": {
                "type": "string",
                "enum": ["stdout", "stderr", "both"],
                "default": "both",
                "description": "Which streams to capture"
            },
            "tty": {
                "type": "boolean",
                "default": False,
                "description": "Allocate a pseudo-TTY"
            },
            "privileged": {
                "type": "boolean",
                "default": False,
                "description": "Run in privileged mode"
            },
            "detach": {
                "type": "boolean",
                "default": False,
                "description": "Run in detached mode (returns immediately)"
            }
        },
        "required": ["container_id", "command"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "container_id": {"type": "string"},
            "command": {"type": ["string", "array"]},
            "result": {
                "type": ["object", "null"],
                "properties": {
                    "exit_code": {"type": "integer"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                    "output": {"type": "string"},
                    "success": {"type": "boolean"}
                },
                "required": ["exit_code", "stdout", "stderr", "output", "success"]
            },
            "error": {"type": ["string", "null"]}
        },
        "required": ["success", "message", "container_id", "command"]
    },
    examples=[
        {
            "name": "Execute a simple command",
            "input": {
                "container_id": "my-container",
                "command": ["ls", "-la", "/app"],
                "user": "appuser"
            },
            "output": {
                "success": True,
                "message": "Command executed successfully",
                "container_id": "my-container",
                "command": ["ls", "-la", "/app"],
                "result": {
                    "exit_code": 0,
                    "stdout": "total 12\ndrwxr-xr-x 1 appuser appuser 4096 Jan  1 12:00 .\ndrwxr-xr-x 1 root    root    4096 Jan  1 11:00 ..\n-rw-r--r-- 1 appuser appuser  123 Jan  1 12:00 app.py",
                    "stderr": "",
                    "output": "total 12\ndrwxr-xr-x 1 appuser appuser 4096 Jan  1 12:00 .\ndrwxr-xr-x 1 root    root    4096 Jan  1 11:00 ..\n-rw-r--r-- 1 appuser appuser  123 Jan  1 12:00 app.py",
                    "success": True
                },
                "error": None
            }
        },
        {
            "name": "Run an interactive shell",
            "input": {
                "container_id": "my-container",
                "command": "/bin/bash",
                "tty": True,
                "stream": True
            },
            "output": {
                "success": True,
                "message": "Interactive shell started (streaming)",
                "container_id": "my-container",
                "command": "/bin/bash",
                "result": None,
                "error": None
            }
        }
    ]
)
async def execute_in_container(
    request: ContainerExecRequest
) -> Dict[str, Any]:
    container_id = request.container_id
    command = request.command
    user = request.user
    workdir = request.workdir
    environment = request.environment
    stream = request.stream
    stream_type = request.stream_type
    tty = request.tty
    privileged = request.privileged
    detach = request.detach
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
                    message=f'Failed to execute command in container {container_id}',
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
