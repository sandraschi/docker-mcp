"""
Volume models for Docker MCP.

This module contains Pydantic models for volume-related requests and responses.
"""
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, ValidationInfo
from datetime import datetime
from enum import Enum

class VolumeDriver(str, Enum):
    """Supported volume drivers."""
    LOCAL = "local"
    NFS = "local"  # Uses local driver with nfs options
    CIFS = "local"  # Uses local driver with cifs options
    TMPFS = "tmpfs"
    BIND = "bind"
    NAMED_PIPE = "npipe"
    SSHFS = "vieux/sshfs"
    REXRAY = "rexray"
    AZURE_FILE = "azure_file"
    CONVOY = "convoy"
    PORTWORX = "pxd"
    GLUSTERFS = "glusterfs"
    CEPH = "ceph"
    LINSTOR = "linstor"
    STORAGE_OS = "storageos"
    HOST_PATH = "local"  # Uses local driver with specific options
    CONTAINER_STORAGE_MODULE = "csi"

class VolumeStatus(str, Enum):
    """Volume status enumeration."""
    CREATED = "created"
    MOUNTED = "mounted"
    UNMOUNTED = "unmounted"
    ERROR = "error"
    ORPHANED = "orphaned"
    REMOVING = "removing"
    UNKNOWN = "unknown"

class VolumeBackupConfig(BaseModel):
    """Configuration for volume backup operations."""
    enabled: bool = Field(
        default=False,
        description="Enable automatic backups"
    )
    schedule: Optional[str] = Field(
        None,
        description="Cron-style backup schedule (e.g., '0 0 * * *' for daily)"
    )
    retention_days: int = Field(
        7,
        ge=1,
        description="Number of days to retain backups"
    )
    backup_driver: str = Field(
        "local",
        description="Backup storage driver"
    )
    backup_driver_opts: Dict[str, str] = Field(
        default_factory=dict,
        description="Backup driver options"
    )

    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: Optional[str]) -> Optional[str]:
        if v and not all(x.isdigit() or x in ('*', ',', '-', '/') for x in v.replace(' ', '')):
            raise ValueError("Invalid cron schedule format")
        return v

class VolumeRestoreConfig(BaseModel):
    """Configuration for volume restore operations."""
    backup_id: Optional[str] = Field(
        None,
        description="Specific backup ID to restore from"
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Point-in-time to restore to"
    )
    force: bool = Field(
        False,
        description="Force restore even if target volume is not empty"
    )
    verify: bool = Field(
        True,
        description="Verify data integrity after restore"
    )

class VolumeInfo(BaseModel):
    """Volume information model with extended metadata."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "Name": "my_volume",
                "Driver": "local",
                "Status": "created",
                "CreatedAt": "2023-01-01T00:00:00Z"
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
    
    Name: str = Field(..., description="Name of the volume")
    Driver: str = Field(..., description="Volume driver used")
    Mountpoint: Optional[str] = Field(None, description="Path where the volume is mounted on the host")
    CreatedAt: Optional[datetime] = Field(None, description="When the volume was created")
    Status: VolumeStatus = Field(VolumeStatus.UNKNOWN, description="Current status of the volume")
    Labels: Dict[str, str] = Field(default_factory=dict, description="User-defined metadata")
    Options: Dict[str, Any] = Field(default_factory=dict, description="Driver-specific options")
    UsageData: Optional[Dict[str, Any]] = Field(None, description="Volume usage statistics")
    Scope: str = Field("local", description="Volume scope (local, global)")
    ClusterVolume: Optional[Dict[str, Any]] = Field(None, description="Cluster volume information")
    AccessMode: str = Field("rw", description="Volume access mode (rw, ro, rwz, etc.)")
    Capacity: Optional[int] = Field(None, description="Volume capacity in bytes")
    Available: Optional[int] = Field(None, description="Available space in bytes")
    Used: Optional[int] = Field(None, description="Used space in bytes")
    RefCount: int = Field(0, description="Number of containers using this volume")
    BackupConfig: Optional[VolumeBackupConfig] = Field(None, description="Backup configuration")
    Created: Optional[str] = Field(None, description="Legacy created timestamp")

class VolumeResponse(BaseModel):
    """Standard volume operation response."""
    success: bool
    message: str
    volume: Optional[VolumeInfo] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class VolumeListResponse(BaseModel):
    """Response model for listing volumes."""
    success: bool
    message: str
    volumes: List[VolumeInfo]
    total_size: int
    error: Optional[str] = None

class CreateVolumeRequest(BaseModel):
    """Request model for creating a volume with advanced options."""
    name: str = Field(
        ...,
        description="Name of the volume to create",
        min_length=2,
        max_length=255,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
    )
    driver: VolumeDriver = Field(
        default=VolumeDriver.LOCAL,
        description="Volume driver to use"
    )
    driver_opts: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to apply to the volume"
    )
    size: Optional[str] = Field(
        None,
        description="Volume size with unit (e.g., '10GB', '500MB')",
        pattern=r'^\d+[KMGTP]?B?$'
    )
    mount_opts: Optional[Dict[str, Any]] = Field(
        None,
        description="Mount options for the volume"
    )
    backup_config: Optional[VolumeBackupConfig] = Field(
        None,
        description="Backup configuration for the volume"
    )
    access_mode: str = Field(
        "rw",
        description="Volume access mode (rw, ro, rwz, etc.)",
        pattern=r'^r[owz]*$'
    )
    capacity: Optional[int] = Field(
        None,
        ge=1,
        description="Volume capacity in bytes"
    )
    availability_zone: Optional[str] = Field(
        None,
        description="Availability zone for the volume (for cloud providers)"
    )
    snapshot_id: Optional[str] = Field(
        None,
        description="ID of the snapshot to create the volume from"
    )
    clone_of: Optional[str] = Field(
        None,
        description="ID of the volume to clone"
    )

    @model_validator(mode='before')
    @classmethod
    def validate_driver_options(cls, values):
        if not isinstance(values, dict):
            return values
            
        driver = values.get('driver')
        driver_opts = values.get('driver_opts', {})
        
        if driver == VolumeDriver.NFS:
            if 'type' not in driver_opts:
                driver_opts['type'] = 'nfs'
            if 'o' not in driver_opts and 'device' not in driver_opts:
                raise ValueError("NFS volumes require either 'device' or 'o' option")
        
        elif driver == VolumeDriver.CIFS:
            if 'type' not in driver_opts:
                driver_opts['type'] = 'cifs'
            if 'o' not in driver_opts and 'device' not in driver_opts:
                raise ValueError("CIFS volumes require either 'device' or 'o' option")
        
        return values

class VolumeOperationRequest(BaseModel):
    """Base request model for volume operations."""
    volume_name: str = Field(
        ...,
        description="Name or ID of the volume"
    )
    timeout: int = Field(
        30,
        ge=5,
        le=300,
        description="Operation timeout in seconds"
    )

class RemoveVolumeRequest(VolumeOperationRequest):
    """Request model for removing a volume."""
    force: bool = Field(
        default=False,
        description="Force removal of the volume even if in use"
    )
    delete_backups: bool = Field(
        default=False,
        description="Delete associated backups when removing the volume"
    )
    confirm: bool = Field(
        default=False,
        description="Confirm deletion (required for volumes with data)"
    )

    @model_validator(mode='before')
    @classmethod
    def validate_confirmation(cls, values):
        if values.get('confirm') is False and values.get('force') is False:
            volume_name = values.get('volume_name', 'this volume')
            raise ValueError(
                f"Deletion of volume '{volume_name}' requires confirmation. "
                "Set confirm=True to confirm deletion."
            )
        return values

class VolumeInspectRequest(VolumeOperationRequest):
    """Request model for inspecting a volume."""
    include_usage: bool = Field(
        default=True,
        description="Include usage statistics in the response"
    )
    include_backups: bool = Field(
        default=False,
        description="Include information about volume backups"
    )
    include_mounts: bool = Field(
        default=True,
        description="Include information about where the volume is mounted"
    )

class PruneVolumesRequest(BaseModel):
    """Request model for pruning unused volumes."""
    filters: Optional[Dict[str, List[str]]] = Field(
        default_factory=dict,
        description="Filters to apply when pruning volumes"
    )
    dry_run: bool = Field(
        default=False,
        description="Only show what would be deleted"
    )
    include_unused: bool = Field(
        default=True,
        description="Include unused volumes"
    )
    include_anonymous: bool = Field(
        default=False,
        description="Include anonymous volumes"
    )
    min_age: str = Field(
        "24h",
        description="Minimum age of volumes to consider for pruning (e.g., '24h', '7d')",
        pattern=r'^\d+[smhdw]$'
    )
    
    @field_validator('min_age')
    @classmethod
    def validate_min_age(cls, v: str, info: ValidationInfo) -> str:
        if not any(v.endswith(unit) for unit in ['s', 'm', 'h', 'd', 'w']):
            raise ValueError("min_age must end with s, m, h, d, or w (seconds, minutes, hours, days, weeks)")
        return v

class VolumeInspectResponse(VolumeInfo):
    """Response model for volume inspection with extended information."""
    containers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Containers using this volume"
    )
    backups: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Available backups for this volume"
    )
    events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent events for this volume"
    )
    performance: Optional[Dict[str, Any]] = Field(
        None,
        description="Performance metrics for the volume"
    )
    health: Dict[str, Any] = Field(
        default_factory=dict,
        description="Health status of the volume"
    )
    replication: Optional[Dict[str, Any]] = Field(
        None,
        description="Replication status if this is a replicated volume"
    )

class VolumeBackupRequest(VolumeOperationRequest):
    """Request model for creating a volume backup."""
    name: Optional[str] = Field(
        None,
        description="Name for the backup (default: auto-generated)"
    )
    description: Optional[str] = Field(
        None,
        description="Description of the backup"
    )
    incremental: bool = Field(
        False,
        description="Create an incremental backup if possible"
    )
    compression: str = Field(
        "gzip",
        description="Compression algorithm to use (none, gzip, lz4, zstd)",
        pattern="^(none|gzip|lz4|zstd)$"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags to associate with the backup"
    )

class VolumeRestoreRequest(VolumeOperationRequest):
    """Request model for restoring a volume from a backup."""
    backup_id: Optional[str] = Field(
        None,
        description="ID of the backup to restore (default: latest)"
    )
    target_volume: Optional[str] = Field(
        None,
        description="Name of the target volume (default: original volume name)"
    )
    force: bool = Field(
        False,
        description="Force restore even if target volume exists and is not empty"
    )
    verify: bool = Field(
        True,
        description="Verify data integrity after restore"
    )

class VolumeCloneRequest(VolumeOperationRequest):
    """Request model for cloning a volume."""
    new_name: str = Field(
        ...,
        description="Name for the new volume"
    )
    readonly: bool = Field(
        False,
        description="Create a read-only clone"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional labels for the new volume"
    )

class VolumeResizeRequest(VolumeOperationRequest):
    """Request model for resizing a volume."""
    size: str = Field(
        ...,
        description="New size with unit (e.g., '20GB', '1TB')",
        pattern=r'^\d+[KMGTP]?B?$'
    )
    shrink_ok: bool = Field(
        False,
        description="Allow shrinking the volume (may result in data loss)"
    )

class VolumeExportRequest(VolumeOperationRequest):
    """Request model for exporting a volume to an archive."""
    output_path: str = Field(
        ...,
        description="Path where to save the exported archive"
    )
    compress: bool = Field(
        True,
        description="Compress the exported data"
    )
    include_metadata: bool = Field(
        True,
        description="Include volume metadata in the export"
    )

class VolumeImportRequest(VolumeOperationRequest):
    """Request model for importing data into a volume."""
    input_path: str = Field(
        ...,
        description="Path to the archive or directory to import"
    )
    cleanup: bool = Field(
        True,
        description="Remove files in the volume that are not in the import"
    )
    no_overwrite: bool = Field(
        False,
        description="Do not overwrite existing files"
    )
