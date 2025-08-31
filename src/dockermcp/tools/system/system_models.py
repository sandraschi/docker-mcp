"""
System models for Docker MCP.

This module contains Pydantic models for system-related requests and responses.
"""
from typing import Dict, List, Optional, Any, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl, ConfigDict, ValidationInfo
from typing import Annotated
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
import re

class SystemResourceType(str, Enum):
    """Types of system resources that can be managed."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"

class SystemUpdateChannel(str, Enum):
    """Update channels for system components."""
    STABLE = "stable"
    EDGE = "edge"
    TEST = "test"
    NIGHTLY = "nightly"

class SystemComponent(str, Enum):
    """System components that can be updated or managed."""
    DOCKER_ENGINE = "docker_engine"
    CONTAINERD = "containerd"
    RUNC = "runc"
    DOCKER_COMPOSE = "docker_compose"
    DOCKER_MACHINE = "docker_machine"
    DOCKER_DESKTOP = "docker_desktop"
    ALL = "all"

class SystemHealthStatus(str, Enum):
    """Health status of system components."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    STARTING = "starting"
    STOPPED = "stopped"
    UNKNOWN = "unknown"

class ResourceUsage(BaseModel):
    """Base model for resource usage information."""
    used: int = Field(0, description="Amount of resource used in bytes")
    available: int = Field(0, description="Amount of resource available in bytes")
    total: int = Field(0, description="Total amount of resource in bytes")
    usage_percent: float = Field(0.0, description="Percentage of resource used (0-100)")
    
    model_config = ConfigDict()
    
    def model_dump_json(self, **kwargs):
        # Custom JSON serialization for float fields
        def serialize(obj):
            if isinstance(obj, float):
                return round(obj, 2) if obj is not None else None
            return obj
            
        # Create a dictionary with serialized values
        data = {
            'used': self.used,
            'available': self.available,
            'total': self.total,
            'usage_percent': round(self.usage_percent, 2) if self.usage_percent is not None else None
        }
        
        return super().model_dump_json(by_alias=True, exclude_none=True, **kwargs)

class SystemInfo(BaseModel):
    """System information model with extended metadata."""
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    
    def model_dump_json(self, **kwargs):
        # Custom JSON serialization for datetime fields
        from datetime import datetime
        
        # Get the default model dump
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Convert datetime fields to ISO format
        for field_name, field_value in data.items():
            if isinstance(field_value, datetime):
                data[field_name] = field_value.isoformat()
        
        # Convert to JSON
        import json
        return json.dumps(data, **kwargs)
    
    ID: str = Field(..., description="Unique identifier for the system")
    Name: str = Field(..., description="Name of the Docker host")
    ServerVersion: str = Field(..., description="Docker server version")
    KernelVersion: str = Field(..., description="Kernel version")
    OperatingSystem: str = Field(..., description="Operating system name")
    OSType: str = Field(..., description="Operating system type")
    Architecture: str = Field(..., description="System architecture")
    NCPU: int = Field(..., description="Number of CPUs")
    MemTotal: int = Field(..., description="Total memory in bytes")
    StorageDriver: str = Field(..., description="Storage driver in use")
    LoggingDriver: str = Field(..., description="Logging driver in use")
    CgroupDriver: str = Field(..., description="Cgroup driver in use")
    CgroupVersion: str = Field(..., description="Cgroup version")
    ContainerdCommit: Dict[str, str] = Field(default_factory=dict, description="Containerd commit information")
    RuncCommit: Dict[str, str] = Field(default_factory=dict, description="Runc commit information")
    InitCommit: Dict[str, str] = Field(default_factory=dict, description="Init commit information")
    SecurityOptions: List[str] = Field(default_factory=list, description="List of enabled security options")
    Labels: Dict[str, str] = Field(default_factory=dict, description="System labels")
    ExperimentalBuild: bool = Field(False, description="Whether experimental features are enabled")
    Debug: bool = Field(False, description="Whether debug mode is enabled")
    HTTPProxy: Optional[str] = Field(None, description="HTTP proxy configuration")
    HTTPSProxy: Optional[str] = Field(None, description="HTTPS proxy configuration")
    NoProxy: Optional[str] = Field(None, description="No proxy configuration")
    RegistryMirrors: List[str] = Field(default_factory=list, description="List of registry mirrors")
    LiveRestoreEnabled: bool = Field(False, description="Whether live restore is enabled")
    Isolation: Optional[str] = Field(None, description="Container isolation technology")
    DefaultRuntime: str = Field("runc", description="Default container runtime")
    Runtimes: Dict[str, Dict[str, str]] = Field(default_factory=dict, description="Available container runtimes")
    Init: bool = Field(False, description="Whether init is enabled for containers")
    Containerd: Dict[str, Any] = Field(default_factory=dict, description="Containerd configuration")
    Swarm: Dict[str, Any] = Field(default_factory=dict, description="Swarm configuration")
    Plugins: Dict[str, Any] = Field(default_factory=dict, description="Available plugins")
    Warnings: List[str] = Field(default_factory=list, description="System warnings")
    
    def get_cpu_count(self) -> int:
        """Get the number of CPU cores."""
        return self.NCPU
    
    def get_memory_info(self) -> Dict[str, int]:
        """Get memory information in a structured format."""
        return {
            'total': self.memory,
            'used': 0,  # Will be populated by system metrics
            'free': 0,  # Will be populated by system metrics
            'unit': 'bytes'
        }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage driver information."""
        return {
            'driver': self.storage_driver,
            'options': {}
        }

class SystemResponse(BaseModel):
    """Standard system operation response with extended metadata."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message about the operation result")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data related to the operation")
    error: Optional[str] = Field(None, description="Error message if the operation failed")
    error_type: Optional[str] = Field(None, description="Type of error that occurred")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Unique identifier for the request")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), 
                          description="Timestamp when the response was generated")
    
    model_config = ConfigDict()
    
    def model_dump_json(self, **kwargs):
        # Get the default model dump
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Convert datetime and timedelta fields to serializable formats
        from datetime import datetime, timedelta
        
        for field_name, field_value in data.items():
            if isinstance(field_value, datetime):
                data[field_name] = field_value.isoformat()
            elif isinstance(field_value, timedelta):
                data[field_name] = field_value.total_seconds()
        
        # Convert to JSON with proper serialization of all fields
        import json
        return json.dumps(data, **kwargs)
    
    @classmethod
    def success_response(
        cls,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> 'SystemResponse':
        """Create a success response.
        
        Args:
            message: Success message
            data: Optional data to include in the response
            request_id: Optional request ID for tracking
            
        Returns:
            SystemResponse: A success response object
        """
        return cls(
            success=True,
            message=message,
            data=data,
            request_id=request_id
        )
    
    @classmethod
    def error_response(
        cls,
        message: str,
        error_type: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        status_code: int = 500
    ) -> 'SystemResponse':
        """Create an error response.
        
        Args:
            message: Error message
            error_type: Type of error (e.g., 'ValidationError', 'NotFound')
            error_details: Additional error details
            request_id: Optional request ID for tracking
            status_code: HTTP status code for the error
            
        Returns:
            SystemResponse: An error response object
        """
        return cls(
            success=False,
            message=message,
            error=message,
            error_type=error_type,
            error_details=error_details,
            request_id=request_id
        )

class SystemPruneResponse(SystemResponse):
    """Response model for system prune operations."""
    reclaimed_space: Optional[int] = None
    deleted_objects: Optional[Dict[str, List[str]]] = None

class DiskUsage(ResourceUsage):
    """Disk usage information model."""
    mount_point: Optional[str] = Field(None, description="Mount point of the filesystem")
    filesystem: Optional[str] = Field(None, description="Filesystem type")
    inodes_used: Optional[int] = Field(None, description="Number of inodes used")
    inodes_total: Optional[int] = Field(None, description="Total number of inodes")
    inodes_usage_percent: Optional[float] = Field(None, description="Percentage of inodes used")
    read_only: bool = Field(False, description="Whether the filesystem is read-only")
    
    @field_validator('inodes_usage_percent', mode='before')
    @classmethod
    def calculate_inode_usage(cls, v, info):
        if v is not None:
            return v
        data = info.data
        if data.get('inodes_used') is not None and data.get('inodes_total') and data['inodes_total'] > 0:
            return (data['inodes_used'] / data['inodes_total']) * 100
        return None

class MemoryUsage(ResourceUsage):
    """Memory usage information model."""
    buffer: int = Field(0, description="Amount of memory used for buffers")
    cache: int = Field(0, description="Amount of memory used for cache")
    shared: int = Field(0, description="Amount of shared memory")
    swap_total: int = Field(0, description="Total swap space in bytes")
    swap_used: int = Field(0, description="Amount of swap space used in bytes")
    swap_usage_percent: float = Field(0.0, description="Percentage of swap space used")
    
    @field_validator('swap_usage_percent', mode='before')
    @classmethod
    def calculate_swap_usage(cls, v, info):
        if v is not None:
            return v
        data = info.data
        if data.get('swap_used') is not None and data.get('swap_total') and data['swap_total'] > 0:
            return (data['swap_used'] / data['swap_total']) * 100
        return 0.0

class CpuUsage(ResourceUsage):
    """CPU usage information model."""
    cores: int = Field(0, description="Number of CPU cores")
    cores_usage: List[float] = Field(
        default_factory=list,
        description="Usage percentage per CPU core (0-100)"
    )
    system_usage: float = Field(0.0, description="System CPU usage percentage")
    user_usage: float = Field(0.0, description="User CPU usage percentage")
    iowait: Optional[float] = Field(None, description="I/O wait percentage")
    load_average: Dict[str, float] = Field(
        default_factory=dict,
        description="System load averages for 1, 5, and 15 minutes"
    )
    
    @field_validator('usage_percent', mode='before')
    @classmethod
    def calculate_usage_percent(cls, v, info):
        if v is not None:
            return v
        # Calculate overall CPU usage as average of all cores
        data = info.data
        if data.get('cores_usage'):
            return sum(data['cores_usage']) / len(data['cores_usage'])
        return 0.0

class NetworkUsage(ResourceUsage):
    """Network interface usage information model."""
    interface: str = Field(..., description="Network interface name")
    bytes_sent: int = Field(0, description="Total bytes sent")
    bytes_recv: int = Field(0, description="Total bytes received")
    packets_sent: int = Field(0, description="Total packets sent")
    packets_recv: int = Field(0, description="Total packets received")
    errors_in: int = Field(0, description="Total receive errors")
    errors_out: int = Field(0, description="Total send errors")
    speed: Optional[int] = Field(
        None,
        description="Interface speed in bits per second"
    )
    mtu: Optional[int] = Field(
        None,
        description="Maximum Transmission Unit"
    )
    mac_address: Optional[str] = Field(
        None,
        description="MAC address of the interface"
    )
    ip_addresses: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of IP addresses with address families"
    )
    is_up: bool = Field(True, description="Whether the interface is up")
    duplex: Optional[str] = Field(
        None,
        description="Duplex mode (full, half, or unknown)",
        pattern="^(full|half|unknown)$"
    )

class SystemDiskUsageResponse(SystemResponse):
    """Response model for detailed disk usage information."""
    layers_size: int = Field(0, description="Total size of image layers in bytes")
    images: int = Field(0, description="Number of images")
    containers: int = Field(0, description="Number of containers")
    volumes: int = Field(0, description="Number of volumes")
    build_cache: int = Field(0, description="Size of build cache in bytes")
    builder_size: int = Field(0, description="Size used by the builder in bytes")
    total_usage: int = Field(0, description="Total disk usage in bytes")
    total_usage_human: str = Field("0B", description="Human-readable total disk usage")
    disk_usage: Dict[str, DiskUsage] = Field(
        default_factory=dict,
        description="Disk usage by mount point"
    )
    
    @field_validator('total_usage_human', mode='before')
    def format_total_usage(cls, v: str, info: ValidationInfo) -> str:
        if info.data and 'total_usage' in info.data:
            return format_size(info.data['total_usage'])
        return "0B"

class SystemInfoResponse(BaseModel):
    """Comprehensive system information response model."""
    
    system_status: SystemInfo = Field(..., description="Detailed system status information")
    containers: Dict[str, int] = Field(
            default_factory=lambda: {
                'total': 0,
                'running': 0,
                'paused': 0,
                'stopped': 0,
                'restarting': 0,
                'dead': 0
            },
            description="Container statistics"
        )
    images: int = Field(0, description="Number of images")
    volumes: int = Field(0, description="Number of volumes")
    networks: int = Field(0, description="Number of networks")
    server_version: str = Field(..., description="Docker server version")
    api_version: str = Field(..., description="Docker API version")
    min_api_version: str = Field(..., description="Minimum required API version")
    kernel_version: str = Field(..., description="Kernel version")
    operating_system: str = Field(..., description="Operating system name")
    os_type: str = Field(..., description="Operating system type")
    architecture: str = Field(..., description="System architecture")
    cpus: int = Field(0, description="Number of CPU cores")
    memory: MemoryUsage = Field(default_factory=MemoryUsage, description="Memory usage information")
    swap: MemoryUsage = Field(default_factory=MemoryUsage, description="Swap usage information")
    disk: DiskUsage = Field(default_factory=DiskUsage, description="Root disk usage information")
    cpu: CpuUsage = Field(default_factory=CpuUsage, description="CPU usage information")
    network: Dict[str, NetworkUsage] = Field(
            default_factory=dict,
            description="Network interfaces usage information"
        )
    storage_driver: str = Field(..., description="Storage driver in use")
    logging_driver: str = Field(..., description="Default logging driver")
    cgroup_driver: str = Field(..., description="Cgroup driver in use")
    cgroup_version: str = Field(..., description="Cgroup version")
    security_options: List[str] = Field(
            default_factory=list,
            description="List of enabled security options"
        )
    experimental_build: bool = Field(False, description="Whether experimental features are enabled")
    debug: bool = Field(False, description="Whether debug mode is enabled")
    registry_mirrors: List[str] = Field(
            default_factory=list,
            description="List of configured registry mirrors"
        )
    live_restore_enabled: bool = Field(False, description="Whether live restore is enabled")
    default_runtime: str = Field("runc", description="Default container runtime")
    runtimes: Dict[str, Dict[str, str]] = Field(
            default_factory=dict,
            description="Available container runtimes"
        )
    swarm: Dict[str, Any] = Field(
            default_factory=dict,
            description="Swarm mode information if enabled"
        )
    warnings: List[str] = Field(
            default_factory=list,
            description="System warnings and informational messages"
        )
    timestamp: datetime = Field(
            default_factory=datetime.utcnow,
            description="Timestamp when the information was collected"
        )
    uptime: timedelta = Field(
            default_factory=timedelta,
            description="System uptime"
        )
    model_config = ConfigDict()
    
    def model_dump_json(self, **kwargs):
        # Get the default model dump
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Convert datetime and timedelta fields to serializable formats
        from datetime import datetime, timedelta
        
        for field_name, field_value in data.items():
            if isinstance(field_value, datetime):
                data[field_name] = field_value.isoformat()
            elif isinstance(field_value, timedelta):
                data[field_name] = field_value.total_seconds()
        
        # Convert to JSON with proper serialization of all fields
        import json
        return json.dumps(data, **kwargs)
    def get_container_count(self, status: Optional[str] = None) -> int:
        """Get count of containers with optional status filter.
        
        Args:
            status: Container status to filter by (e.g., 'running', 'stopped')
            
        Returns:
            int: Number of containers matching the status filter, or total if no filter
        """
        if status:
            return self.containers.get(status.lower(), 0)
        return sum(self.containers.values())
        
    def get_resource_usage(self, resource_type: SystemResourceType) -> Dict[str, Any]:
        """Get usage information for a specific resource type.
        
        Args:
            resource_type: Type of resource to get usage for
            
        Returns:
            Dict with usage information for the specified resource
        """
        if resource_type == SystemResourceType.CPU:
            return self.cpu.dict()
        elif resource_type == SystemResourceType.MEMORY:
            return self.memory.dict()
        elif resource_type == SystemResourceType.DISK:
            return self.disk.dict()
        elif resource_type == SystemResourceType.NETWORK:
            return {k: v.dict() for k, v in self.network.items()}
        else:
            return {
                'error': f'Unsupported resource type: {resource_type}'
            }
    docker_root_dir: Optional[str] = None

class SystemPingResponse(SystemResponse):
    """Response model for system ping."""
    api_version: Optional[str] = None
    os: Optional[str] = None
    arch: Optional[str] = None
    kernel_version: Optional[str] = None
    build_time: Optional[str] = None

class SystemAuthRequest(BaseModel):
    """Request model for registry authentication with enhanced security."""
    username: str = Field(..., description="Username for authentication")
    password: str = Field(..., description="Password or access token")
    email: Optional[str] = Field(
            None,
            description="Email address associated with the account",
            pattern="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
    )
    serveraddress: str = Field(
        ...,
            description="Registry server address (e.g., https://index.docker.io/v1/)",
            pattern="^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/[a-zA-Z0-9._-]+)*$"
    )
    identity_token: Optional[str] = Field(
        None,
        description="Identity token for token-based authentication"
    )
    registry_token: Optional[str] = Field(
        None,
        description="Registry token for direct authentication"
    )
    auth: Optional[str] = Field(
        None,
        description="Base64-encoded auth configuration"
    )
    creds_store: Optional[str] = Field(
        None,
        description="Credential helper to use for storing credentials"
    )
    creds_store_opt: Optional[Dict[str, str]] = Field(
        None,
        description="Options for the credential helper"
    )
    
    @field_validator('serveraddress')
    def validate_server_address(cls, v: str, info: ValidationInfo) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Server address must start with http:// or https://")
        return v.rstrip('/')  # Remove trailing slash for consistency

class SystemAuthResponse(SystemResponse):
    """Response model for authentication with detailed token information."""
    status: str = Field(
        ...,
        description="Status of the authentication request",
        json_schema_extra={"example": "Login Succeeded"}
    )
    identity_token: Optional[str] = Field(
        None,
        description="JWT token for authenticated session"
    )
    expires_in: Optional[int] = Field(
        None,
        description="Number of seconds until the token expires"
    )
    refresh_token: Optional[str] = Field(
        None,
        description="Refresh token for obtaining new access tokens"
    )
    registry_url: Optional[str] = Field(
        None,
        description="URL of the authenticated registry"
    )
    username: Optional[str] = Field(
        None,
        description="Authenticated username"
    )
    email: Optional[str] = Field(
        None,
        description="Email associated with the authenticated account"
    )
    server_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional information about the registry"
    )
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = ["Login Succeeded", "Login in progress", "Login failed"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v

class SystemPruneRequest(BaseModel):
    """Request model for system prune."""
    prune_volumes: bool = Field(
        default=False,
        description="Prune volumes as well"
    )
    prune_build_cache: bool = Field(
        default=True,
        description="Prune build cache"
    )
    prune_networks: bool = Field(
        default=True,
        description="Prune networks"
    )
    prune_containers: bool = Field(
        default=True,
        description="Prune stopped containers"
    )
    prune_images: bool = Field(
        default=False,
        description="Prune unused images"
    )
    prune_containers_all: bool = Field(
        default=False,
        description="Prune all containers (including running ones)"
    )

class SystemEventsRequest(BaseModel):
    """Request model for system events."""
    since: Optional[str] = Field(
        None,
        description="Show events since this timestamp"
    )
    until: Optional[str] = Field(
        None,
        description="Show events before this timestamp"
    )
    filters: Optional[Dict[str, List[str]]] = Field(
        None,
        description="JSON encoded filter values"
    )

class SystemEventsResponse(SystemResponse):
    """Response model for system events."""
    events: List[Dict[str, Any]] = []

class SystemDataUsageResponse(SystemResponse):
    """Response model for system data usage information."""
    layers_size: int = 0
    images: List[Dict[str, Any]] = []
    containers: List[Dict[str, Any]] = []
    volumes: List[Dict[str, Any]] = []
    build_cache: List[Dict[str, Any]] = []
    builder_size: int = 0
