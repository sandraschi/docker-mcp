"""
Docker Compose data models for DockerMCP.

This module defines Pydantic models for Docker Compose operations.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl, ConfigDict, ValidationInfo

class ComposeServiceState(str, Enum):
    """Possible states of a Compose service."""
    RUNNING = "running"
    RESTARTING = "restarting"
    PAUSED = "paused"
    EXITED = "exited"
    DEAD = "dead"
    CREATED = "created"
    REMOVING = "removing"

class ComposeHealthStatus(str, Enum):
    """Health status of a Compose service."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    NONE = "none"

class ComposeRestartPolicy(str, Enum):
    """Restart policies for Compose services."""
    NO = "no"
    ALWAYS = "always"
    ON_FAILURE = "on-failure"
    UNLESS_STOPPED = "unless-stopped"

class ComposeDeploymentMode(str, Enum):
    """Deployment modes for Compose services."""
    REPLICATED = "replicated"
    GLOBAL = "global"

class ComposeVolumeType(str, Enum):
    """Types of volumes in Compose."""
    VOLUME = "volume"
    BIND = "bind"
    TMPFS = "tmpfs"
    NAMED_PIPE = "npipe"

class ComposeNetworkDriver(str, Enum):
    """Network drivers for Compose networks."""
    BRIDGE = "bridge"
    HOST = "host"
    OVERLAY = "overlay"
    MACVLAN = "macvlan"
    NONE = "none"

class ComposeVolume(BaseModel):
    """Model representing a Docker Compose volume."""
    name: str
    driver: Optional[str] = None
    driver_opts: Dict[str, str] = Field(default_factory=dict)
    external: bool = False
    name: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)

class ComposeNetwork(BaseModel):
    """Model representing a Docker Compose network."""
    name: str
    driver: ComposeNetworkDriver = ComposeNetworkDriver.BRIDGE
    driver_opts: Dict[str, str] = Field(default_factory=dict)
    attachable: bool = False
    enable_ipv6: bool = False
    ipam: Dict[str, Any] = Field(default_factory=dict)
    internal: bool = False
    external: bool = False
    name: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)

class ComposeService(BaseModel):
    """Model representing a Docker Compose service."""
    name: str
    image: Optional[str] = None
    build: Optional[Union[str, Dict[str, Any]]] = None
    command: Optional[Union[str, List[str]]] = None
    entrypoint: Optional[Union[str, List[str]]] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    env_file: Optional[Union[str, List[str]]] = None
    ports: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)
    networks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    depends_on: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    deploy: Dict[str, Any] = Field(default_factory=dict)
    restart: ComposeRestartPolicy = ComposeRestartPolicy.NO
    healthcheck: Dict[str, Any] = Field(default_factory=dict)
    labels: Dict[str, str] = Field(default_factory=dict)
    container_name: Optional[str] = None
    working_dir: Optional[str] = None
    user: Optional[str] = None
    working_dir: Optional[str] = None
    stop_grace_period: Optional[str] = None
    stop_signal: Optional[str] = None
    tty: bool = False
    stdin_open: bool = False
    privileged: bool = False
    read_only: bool = False
    shm_size: Optional[str] = None
    mem_limit: Optional[str] = None
    mem_reservation: Optional[str] = None
    cpus: Optional[float] = None
    cpu_shares: Optional[int] = None
    cpu_quota: Optional[int] = None
    cpuset: Optional[str] = None
    tmpfs: Optional[Union[str, List[str]]] = None
    cap_add: List[str] = Field(default_factory=list)
    cap_drop: List[str] = Field(default_factory=list)
    security_opt: List[str] = Field(default_factory=list)
    ulimits: Dict[str, Union[int, Dict[str, int]]] = Field(default_factory=dict)

class ComposeProject(BaseModel):
    """Model representing a Docker Compose project."""
    name: str
    services: Dict[str, ComposeService] = Field(default_factory=dict)
    volumes: Dict[str, Optional[Dict[str, Any]]] = Field(default_factory=dict)
    networks: Dict[str, Optional[Dict[str, Any]]] = Field(default_factory=dict)
    configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    secrets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    version: str = "3.8"

class ComposeConfig(BaseModel):
    """Model representing a Docker Compose configuration."""
    version: str
    services: Dict[str, Dict[str, Any]]
    volumes: Dict[str, Any] = Field(default_factory=dict)
    networks: Dict[str, Any] = Field(default_factory=dict)
    configs: Dict[str, Any] = Field(default_factory=dict)
    secrets: Dict[str, Any] = Field(default_factory=dict)

class ComposeUpRequest(BaseModel):
    """Request model for compose_up tool."""
    project_name: str
    file_path: Optional[str] = None
    files: Optional[List[str]] = None
    env_file: Optional[str] = None
    env_files: Optional[List[str]] = None
    profiles: Optional[List[str]] = None
    services: Optional[List[str]] = None
    detach: bool = True
    build: bool = False
    no_build: bool = False
    force_recreate: bool = False
    always_recreate_deps: bool = False
    no_recreate: bool = False
    renew_anon_volumes: bool = False
    remove_orphans: bool = False
    no_deps: bool = False
    timeout: Optional[int] = 10
    exit_code_from: Optional[str] = None
    scale: Optional[Dict[str, int]] = None
    no_color: bool = True
    quiet_pull: bool = False
    no_log_prefix: bool = False
    log_level: str = "info"
    output_json: bool = Field(default=False, alias="json")
    parallel: int = 1
    dry_run: bool = False

class ComposeDownRequest(BaseModel):
    """Request model for compose_down tool."""
    project_name: str
    file_path: Optional[str] = None
    files: Optional[List[str]] = None
    env_file: Optional[str] = None
    env_files: Optional[List[str]] = None
    remove_orphans: bool = False
    rmi: Optional[str] = None
    timeout: Optional[int] = 10
    volumes: bool = False
    remove_volumes: bool = False
    remove_all: bool = False
    dry_run: bool = False

class ComposeBuildRequest(BaseModel):
    """Request model for compose_build tool."""
    project_name: str
    file_path: Optional[str] = None
    files: Optional[List[str]] = None
    env_file: Optional[str] = None
    env_files: Optional[List[str]] = None
    services: Optional[List[str]] = None
    no_cache: bool = False
    pull: bool = False
    force_rm: bool = False
    memory: Optional[str] = None
    build_args: Dict[str, str] = Field(default_factory=dict)
    compress: bool = False
    parallel: bool = True
    progress: str = "auto"
    quiet: bool = False
    no_rm: bool = False
    dry_run: bool = False

class ComposeLogsRequest(BaseModel):
    """Request model for compose_logs tool."""
    project_name: str
    file_path: Optional[str] = None
    files: Optional[List[str]] = None
    env_file: Optional[str] = None
    env_files: Optional[List[str]] = None
    services: Optional[List[str]] = None
    follow: bool = False
    tail: Optional[Union[str, int]] = "all"
    no_color: bool = True
    no_log_prefix: bool = False
    since: Optional[str] = None
    until: Optional[str] = None
    timestamps: bool = False
    dry_run: bool = False

class ComposePsRequest(BaseModel):
    """Request model for compose_ps tool."""
    project_name: str
    file_path: Optional[str] = None
    files: Optional[List[str]] = None
    services: Optional[List[str]] = None
    all: bool = False
    filter: Optional[str] = None
    format: Optional[str] = None
    quiet: bool = False
    status: Optional[List[str]] = None
    dry_run: bool = False

class ComposeResponse(BaseModel):
    """Base response model for Compose operations."""
    success: bool
    message: str
    project_name: str
    command: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    services: Optional[Dict[str, Dict[str, Any]]] = None
    networks: Optional[Dict[str, Dict[str, Any]]] = None
    volumes: Optional[Dict[str, Dict[str, Any]]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate the duration of the operation in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "project_name": "myapp",
                "command": "up",
                "exit_code": 0,
                "services": {
                    "web": {"status": "running", "health": "healthy"}
                },
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-01T00:00:10Z"
            }
        }
    )
    
    def model_dump_json(self, **kwargs):
        """Custom JSON serialization for the response model."""
        # Custom JSON serialization for datetime and timedelta fields
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, timedelta):
                return obj.total_seconds()
            raise TypeError(f"Type {type(obj)} not serializable")
            
        return super().model_dump_json(
            **kwargs,
            default=default_serializer
        )
        
        # Apply serialization to all fields
        for key, value in data.items():
            if isinstance(value, (datetime, timedelta)):
                data[key] = serialize(value)
            elif isinstance(value, dict):
                data[key] = {k: serialize(v) for k, v in value.items()}
            elif isinstance(value, list):
                data[key] = [serialize(v) for v in value]
                
        import json
        return json.dumps(data, **kwargs)
