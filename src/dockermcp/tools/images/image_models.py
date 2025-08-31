"""
Image models for Docker MCP.

This module contains Pydantic models for image-related requests and responses.
"""
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, HttpUrl, FilePath, DirectoryPath, ConfigDict, ValidationInfo
from datetime import datetime
from enum import Enum

class ImageStatus(str, Enum):
    """Image status enumeration."""
    AVAILABLE = "available"
    PULLING = "pulling"
    BUILDING = "building"
    ERROR = "error"
    NOT_FOUND = "not_found"

class ImageInfo(BaseModel):
    """Image information model."""
    # Define fields that you expect in the image info
    Id: Optional[str] = None
    RepoTags: Optional[List[str]] = None
    RepoDigests: Optional[List[str]] = None
    Parent: Optional[str] = None
    Comment: Optional[str] = None
    Created: Optional[str] = None
    Container: Optional[str] = None
    ContainerConfig: Optional[Dict[str, Any]] = None
    DockerVersion: Optional[str] = None
    Author: Optional[str] = None
    Config: Optional[Dict[str, Any]] = None
    Architecture: Optional[str] = None
    Os: Optional[str] = None
    Size: Optional[int] = None
    VirtualSize: Optional[int] = None
    
    # Model configuration
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "Id": "sha256:...",
                "RepoTags": ["nginx:latest"],
                "Size": 1337,
                "Created": "2023-01-01T00:00:00Z"
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

class ImageResponse(BaseModel):
    """Standard image operation response."""
    success: bool
    message: str
    image: Optional[ImageInfo] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ImageListResponse(BaseModel):
    """Response model for listing images."""
    success: bool
    message: str
    images: List[ImageInfo]
    total_size: int
    error: Optional[str] = None

class PullImageRequest(BaseModel):
    """Request model for pulling an image."""
    repository: str = Field(
        ...,
        description="Repository name (e.g., 'nginx', 'ubuntu', 'library/redis')",
        json_schema_extra={"example": "nginx"}
    )
    tag: str = Field(
        default="latest",
        description="Image tag/version"
    )
    auth_config: Optional[Dict[str, str]] = Field(
        None,
        description="Authentication credentials for private registries"
    )
    platform: Optional[str] = Field(
        None,
        description="Platform in the format 'os[/arch[/variant]]' (e.g., 'linux/amd64')"
    )

class BuildImageRequest(BaseModel):
    """Request model for building an image."""
    path: str = Field(
        ...,
        description="Path to the directory containing the Dockerfile"
    )
    tag: str = Field(
        ...,
        description="Name and optionally a tag in 'name:tag' format"
    )
    dockerfile: Optional[str] = Field(
        None,
        description="Path to the Dockerfile (relative to the build context)"
    )
    buildargs: Optional[Dict[str, str]] = Field(
        None,
        description="Build-time variables"
    )
    labels: Optional[Dict[str, str]] = Field(
        None,
        description="Set metadata for the image"
    )
    nocache: bool = Field(
        default=False,
        description="Do not use cache when building the image"
    )
    rm: bool = Field(
        default=True,
        description="Remove intermediate containers after a successful build"
    )
    pull: bool = Field(
        default=False,
        description="Attempt to pull a newer version of the image"
    )

class ImageOperationRequest(BaseModel):
    """Base request model for image operations."""
    image: str = Field(
        ...,
        description="Image name or ID"
    )

class RemoveImageRequest(ImageOperationRequest):
    """Request model for removing an image."""
    force: bool = Field(
        default=False,
        description="Force removal of the image"
    )
    noprune: bool = Field(
        default=False,
        description="Do not delete untagged parents"
    )

class TagImageRequest(BaseModel):
    """Request model for tagging an image."""
    image: str = Field(
        ...,
        description="Image name or ID to tag"
    )
    repository: str = Field(
        ...,
        description="Repository name to tag the image with"
    )
    tag: Optional[str] = Field(
        "latest",
        description="Tag name (default: 'latest')"
    )
    force: bool = Field(
        default=False,
        description="Force tagging even if the tag already exists"
    )

class SearchImageRequest(BaseModel):
    """Request model for searching images in a registry."""
    term: str = Field(
        ...,
        description="Search term"
    )
    limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    filters: Optional[Dict[str, List[str]]] = Field(
        None,
        description="A JSON encoded value of the filters"
    )

class PruneImagesRequest(BaseModel):
    """Request model for pruning images."""
    filters: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Filters to process on the prune list"
    )
    dangling: bool = Field(
        default=True,
        description="When true, delete only unused and untagged images"
    )

class PruneImagesResponse(BaseModel):
    """Response model for pruning images."""
    images_deleted: List[str] = Field(
        default_factory=list,
        description="List of deleted image IDs"
    )
    space_reclaimed: int = Field(
        0,
        description="Disk space reclaimed in bytes"
    )

class ImageInspectRequest(ImageOperationRequest):
    """Request model for inspecting an image."""
    size: bool = Field(
        default=False,
        description="Return image size and virtual size"
    )

class ImageSaveRequest(ImageOperationRequest):
    """Request model for saving an image to a tar archive."""
    output_path: str = Field(
        ...,
        description="Path where to save the image tar archive"
    )
    format: Literal["tar", "tar.gz"] = Field(
        default="tar",
        description="Output format of the archive"
    )

class ImageLoadRequest(BaseModel):
    """Request model for loading an image from a tar archive."""
    input_path: str = Field(
        ...,
        description="Path to the tar archive to load"
    )
    quiet: bool = Field(
        default=False,
        description="Suppress verbose output"
    )

class ImageHistoryRequest(ImageOperationRequest):
    """Request model for getting image history."""
    all: bool = Field(
        default=False,
        description="Show all intermediate layers"
    )

class ImageExportRequest(ImageOperationRequest):
    """Request model for exporting a container filesystem."""
    output_path: str = Field(
        ...,
        description="Path where to save the exported filesystem"
    )
    chunk_size: int = Field(
        default=2097152,  # 2MB
        ge=1024,
        le=16777216,  # 16MB
        description="Chunk size for streaming the export"
    )

class ImageImportRequest(BaseModel):
    """Request model for importing a container filesystem."""
    source: str = Field(
        ...,
        description="URL or path to the source (file, directory, or URL)"
    )
    repository: str = Field(
        ...,
        description="Repository name for the imported image"
    )
    tag: str = Field(
        default="latest",
        description="Tag for the imported image"
    )
    message: Optional[str] = Field(
        None,
        description="Commit message for imported image"
    )
    changes: Optional[List[str]] = Field(
        None,
        description="Apply Dockerfile instructions to the image"
    )
