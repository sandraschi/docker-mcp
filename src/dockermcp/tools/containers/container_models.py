"""
Container models for Docker MCP.

This module contains Pydantic models for container-related requests and responses.
Compatible with FastMCP 2.12+.
"""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum, auto
from typing import (
    Any, Dict, List, Optional, Union, TypedDict, ClassVar, Literal, 
    TypeVar, Generic, Type, get_origin, get_args
)

# FastMCP imports
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolError

# Pydantic models
from pydantic import (
    BaseModel, Field, field_validator, model_validator, 
    ConfigDict, HttpUrl, field_serializer
)
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated, Self

# Type variable for generic models
T = TypeVar('T')

class ContainerState(str, Enum):
    """
    Container state enumeration.
    
    Attributes:
        CREATED: Container has been created but not started
        RUNNING: Container is currently running
        PAUSED: Container is paused
        RESTARTING: Container is in the process of restarting
        REMOVING: Container is being removed
        EXITED: Container has stopped
        DEAD: Container is dead (failed to start or crashed)
    """
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"
    
    @classmethod
    def from_docker_state(cls, docker_state: str) -> 'ContainerState':
        """Convert Docker state string to ContainerState enum."""
        docker_state = docker_state.lower()
        for state in cls:
            if state.value == docker_state:
                return state
        return cls.EXITED  # Default to EXITED for unknown states

class ContainerInfo(BaseModel):
    """
    Basic container information model.
    
    This model represents the essential information about a Docker container.
    """
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4e5f6",
                "name": "my-container",
                "image": "nginx:latest",
                "status": "Up 2 hours",
                "state": "running",
                "created": "2023-01-01T12:00:00Z",
                "ports": {"80/tcp": "0.0.0.0:8080"},
                "networks": ["bridge"]
            }
        }
    )
    
    id: str = Field(..., description="Container ID (64-character hex string)", min_length=12, max_length=64)
    name: str = Field(..., description="Container name (without leading /)", min_length=1)
    image: str = Field(..., description="Image name and tag (e.g., 'nginx:latest')")
    status: str = Field(..., description="Human-readable container status")
    state: ContainerState = Field(..., description="Container state")
    created: datetime = Field(..., description="Creation timestamp in UTC")
    ports: Dict[str, str] = Field(
        default_factory=dict,
        description="Port mappings in format {'container_port/proto': 'host:port'}"
    )
    networks: List[str] = Field(
        default_factory=list,
        description="List of network names the container is connected to"
    )
    
    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Ensure container name doesn't start with a slash."""
        if v.startswith('/'):
            return v[1:]
        return v
        
    @field_validator('id')
    def validate_id(cls, v: str) -> str:
        """Validate container ID format."""
        if not re.match(r'^[a-f0-9]+$', v.lower()):
            raise ValueError("Container ID must be a hex string")
        return v.lower()

class ContainerResponse(BaseModel):
    """Standard container operation response."""
    success: bool
    message: str
    container: Optional[ContainerInfo] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Container started successfully",
                "container": {
                    "id": "a1b2c3d4e5f6",
                    "name": "my-container",
                    "image": "nginx:latest",
                    "status": "running",
                    "state": "running",
                    "created": "2023-01-01T00:00:00Z"
                }
            }
        }
    )
    
    def model_dump_json(self, **kwargs):
        # Custom JSON serialization for datetime fields
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
            
        return super().model_dump_json(
            **kwargs,
            default=default_serializer
        )

class ListContainersRequest(BaseModel):
    """Request model for listing containers."""
    all_states: bool = Field(
        default=True,
        description="Include stopped containers"
    )

class CreateContainerRequest(BaseModel):
    """Request model for creating a container."""
    image: str = Field(
        ...,
        description="Docker image name (e.g., 'nginx:latest')",
        json_schema_extra={"example": "nginx:latest"}
    )
    name: str = Field(..., description="Container name")
    command: Optional[Union[str, List[str]]] = Field(
        None,
        description="Command to run in the container"
    )
    ports: Dict[str, str] = Field(
        default_factory=dict,
        description="Port mappings {'container_port': 'host_port'}"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
    volumes: Dict[str, str] = Field(
        default_factory=dict,
        description="Volume mounts {'host_path': 'container_path'}"
    )
    network: Optional[str] = Field(
        None,
        description="Network to connect to"
    )
    restart_policy: str = Field(
        "no",
        description="Restart policy (no, on-failure, unless-stopped, always)"
    )
    auto_remove: bool = Field(
        False,
        description="Automatically remove the container when it exits"
    )
    detach: bool = Field(
        True,
        description="Run container in the background"
    )
    tty: bool = Field(
        False,
        description="Allocate a pseudo-TTY"
    )
    stdin_open: bool = Field(
        False,
        description="Keep STDIN open even if not attached"
    )
    mem_limit: Optional[str] = Field(
        None,
        description="Memory limit (e.g., '1g' or '512m')"
    )
    cpu_shares: Optional[int] = Field(
        None,
        description="CPU shares (relative weight)"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Container labels"
    )

    @field_validator('image')
    @classmethod
    def validate_image(cls, v: str) -> str:
        if not v:
            raise ValueError("Image cannot be empty")
        return v.strip()  # Clean up any whitespace

    @field_validator('restart_policy')
    @classmethod
    def validate_restart_policy(cls, v: str) -> str:
        valid_policies = ["no", "on-failure", "unless-stopped", "always"]
        if v not in valid_policies:
            raise ValueError(f"Restart policy must be one of {valid_policies}")
        return v.lower()  # Ensure lowercase for consistency

class PruneContainersRequest(BaseModel):
    """Request model for pruning containers."""
    filters: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Filters to process on the prune list"
    )

class PruneContainersResponse(BaseModel):
    """Response model for pruning containers."""
    containers_deleted: List[str] = Field(
        default_factory=list,
        description="List of deleted container IDs"
    )
    space_reclaimed: int = Field(
        0,
        description="Disk space reclaimed in bytes"
    )

class ExecCommandRequest(BaseModel):
    """Request model for executing a command in a container."""
    container_id: str = Field(..., description="Container ID or name")
    command: Union[str, List[str]] = Field(..., description="Command to execute")
    user: Optional[str] = Field(None, description="User to run command as")
    workdir: Optional[str] = Field(None, description="Working directory")
    environment: Optional[Dict[str, str]] = Field(
        None,
        description="Environment variables"
    )
    detach: bool = Field(False, description="Run in detached mode")
    tty: bool = Field(False, description="Allocate a pseudo-TTY")
    privileged: bool = Field(False, description="Run in privileged mode")

class ExecCommandResponse(BaseModel):
    """Response model for executed command."""
    exit_code: int
    output: str
    error: Optional[str] = None

class ContainerTopRequest(BaseModel):
    """Request model for getting container top processes."""
    container_id: str = Field(..., description="Container ID or name")
    ps_args: Optional[str] = Field(
        default="-ef",
        description="Arguments to pass to ps (e.g., 'aux' or 'ef')"
    )
    stream: bool = Field(
        default=False,
        description="Stream the output continuously"
    )


class ContainerTopResponse(BaseModel):
    """Response model for container top processes."""
    success: bool
    message: str
    container_id: str
    processes: List[List[str]] = Field(
        default_factory=list,
        description="List of processes with their details"
    )
    titles: List[str] = Field(
        default_factory=list,
        description="Column titles for the process list"
    )
    error: Optional[str] = None


class InspectContainerRequest(BaseModel):
    """Request model for inspecting a container.
    
    This is an alias for ContainerInspectRequest for backward compatibility.
    """
    container_id: str = Field(..., description="Container ID or name")
    size: bool = Field(
        default=False,
        description="Return the size of container as fields SizeRw and SizeRootFs"
    )


class ContainerInspectRequest(InspectContainerRequest):
    """Request model for inspecting a container."""
    pass

class ContainerInspectResponse(BaseModel):
    """Response model for container inspection."""
    success: bool
    message: str
    container_id: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ContainerDetails(BaseModel):
    """Detailed container information."""
    id: str
    name: str
    image: str
    state: str
    status: str
    created: str
    path: str
    args: List[str]
    config: Dict[str, Any]
    host_config: Dict[str, Any]
    network_settings: Dict[str, Any]
    mounts: List[Dict[str, Any]]
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    
    def model_dump_json(self, **kwargs):
        # Custom JSON serialization for datetime fields
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
            
        return super().model_dump_json(
            **kwargs,
            default=default_serializer
        )

class ContainerStatsRequest(BaseModel):
    """Request model for getting container stats."""
    container_id: str = Field(..., description="Container ID or name")
    stream: bool = Field(False, description="Stream the output")

class ContainerStatsResponse(BaseModel):
    """Response model for container stats."""
    container_id: str
    name: str
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_io: Dict[str, Any]
    block_io: Dict[str, Any]
    pids: int
    timestamp: datetime

def get_tools() -> List[Type[BaseModel]]:
    """
    Get all Pydantic models in this module that should be registered with FastMCP.
    
    Returns:
        List of Pydantic model classes to register
    """
    return [
        ContainerInfo,
        ContainerResponse,
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
        ListContainersRequest,
        StartContainerRequest,
        StopContainerRequest,
        RestartContainerRequest,
        RemoveContainerRequest,
        GetContainerLogsRequest,
        PruneContainersRequest,
        PruneContainersResponse,
        ExecCommandRequest,
        ExecCommandResponse,
        ContainerTopRequest,
        ContainerTopResponse,
        ContainerDetails
    ]

# ============================================================================
# Container Lifecycle Models
# =============================================================================

class ContainerAction(str, Enum):
    """Available container actions."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    REMOVE = "remove"
    PAUSE = "pause"
    UNPAUSE = "unpause"

class ContainerLifecycleRequest(BaseModel):
    """Request model for container lifecycle operations."""
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    action: ContainerAction = Field(
        ...,
        description="Action to perform on the container"
    )
    force: bool = Field(
        default=False,
        description="Force the action (e.g., force remove a running container)"
    )
    timeout: int = Field(
        default=10,
        ge=1,
        le=300,
        description="Timeout in seconds for stop/restart operations"
    )
    remove_volumes: bool = Field(
        default=False,
        description="Remove volumes when removing a container"
    )

class ContainerLifecycleResponse(BaseModel):
    """Response model for container lifecycle operations."""
    success: bool
    message: str
    container_id: str
    action: str
    state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ============================================================================
# Container Logs Models
# ============================================================================

class LogStreamType(str, Enum):
    """Log stream types."""
    STDOUT = "stdout"
    STDERR = "stderr"
    ALL = "all"

class LogEntry(BaseModel):
    """A single log entry."""
    timestamp: Optional[datetime] = None
    stream: str
    line: str

class ContainerLogsRequest(BaseModel):
    """Request model for container logs."""
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    follow: bool = Field(
        default=False,
        description="Follow log output (like tail -f)"
    )
    tail: Optional[int] = Field(
        default=None,
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
    stream_type: LogStreamType = Field(
        default=LogStreamType.ALL,
        description="Filter logs by stream type (stdout, stderr, all)"
    )
    
    @field_validator('since', 'until', mode='before')
    @classmethod
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

class ContainerLogsResponse(BaseModel):
    """Response model for container logs."""
    success: bool
    message: str
    container_id: str
    logs: List[LogEntry] = []
    error: Optional[str] = None

# ============================================================================
# Container Exec Models
# ============================================================================

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
        default=ExecUser.ROOT,
        description="User to run the command as (default: root)"
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
        description="If true, detach immediately and return without waiting for command completion"
    )
    
    @field_validator('command', mode='before')
    @classmethod
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
    
    def model_post_init(self, __context):
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

# ============================================================================
# Base Models (keep existing models below)
# ============================================================================

class ContainerOperationRequest(BaseModel):
    """Base request model for container operations."""
    container_name: str = Field(
        ...,
        description="Name or ID of the container"
    )

class StartContainerRequest(ContainerOperationRequest):
    """Request model for starting a container."""
    pass

class StopContainerRequest(ContainerOperationRequest):
    """Request model for stopping a container."""
    timeout: int = Field(
        default=10,
        ge=1,
        le=300,
        description="Seconds to wait before force killing the container"
    )

class RestartContainerRequest(StopContainerRequest):
    """Request model for restarting a container."""
    pass

class RemoveContainerRequest(ContainerOperationRequest):
    """Request model for removing a container."""
    force: bool = Field(
        default=False,
        description="Force removal of running container"
    )
    remove_volumes: bool = Field(
        default=False,
        description="Remove anonymous volumes associated with the container"
    )

class GetContainerLogsRequest(ContainerOperationRequest):
    """Request model for getting container logs."""
    follow: bool = Field(
        default=False,
        description="Follow log output"
    )
    tail: Optional[int] = Field(
        None,
        ge=1,
        description="Number of lines to show from the end of the logs"
    )
    since: Optional[str] = Field(
        None,
        description="Show logs since timestamp or relative time (e.g., 2m for 2 minutes)"
    )
    until: Optional[str] = Field(
        None,
        description="Show logs before timestamp or relative time"
    )
    timestamps: bool = Field(
        default=False,
        description="Show timestamps"
    )
