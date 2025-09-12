"""
Docker Image Management for FastMCP 2.12+

This module provides comprehensive tools for managing Docker images including:
- Listing and searching images
- Pulling images from registries
- Building images from Dockerfiles
- Tagging and pushing images
- Managing image history and layers
- Cleaning up unused images
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import tarfile
import tempfile
from datetime import datetime
from enum import Enum
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Optional, Union, BinaryIO, Tuple, Generator, Annotated

import docker
from docker.errors import (
    DockerException, APIError, ImageNotFound, BuildError, 
    ContainerError, NotFound, InvalidRepository, InvalidVersion
)
from dockermcp.mcp_instance import mcp
from pydantic import Field, validator, HttpUrl, AnyUrl

from dockermcp.logging_config import logger

class ImagePullPolicy(str, Enum):
    """Policy for pulling container images."""
    ALWAYS = "always"
    IF_NOT_PRESENT = "if-not-present"
    NEVER = "never"

class ImageBuildStatus(str, Enum):
    """Status of an image build operation."""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ImagePullProgress(BaseModel):
    """Progress information for an image pull operation."""
    id: Optional[str] = Field(None, description="Image or layer ID")
    status: Optional[str] = Field(None, description="Status message")
    progress: Optional[str] = Field(None, description="Progress bar")
    progress_detail: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed progress information"
    )
    error: Optional[str] = Field(None, description="Error message if any")

class ImageBuildResult(BaseModel):
    """Result of an image build operation."""
    image_id: Optional[str] = Field(None, description="ID of the built image")
    logs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Build output logs"
    )
    status: ImageBuildStatus = Field(
        default=ImageBuildStatus.SUCCESS,
        description="Build status"
    )
    error: Optional[str] = Field(None, description="Error message if build failed")

class ImageLayer(BaseModel):
    """Represents a layer in a Docker image."""
    id: str = Field(..., description="Layer ID")
    created: Optional[datetime] = Field(None, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Command that created the layer")
    size: int = Field(0, description="Size of the layer in bytes")
    comment: Optional[str] = Field(None, description="Optional comment")
    empty_layer: bool = Field(False, description="Whether this is an empty layer")

class ImageHistoryItem(BaseModel):
    """Represents an entry in the image history."""
    id: str = Field(..., description="Layer ID")
    created: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="Command that created this layer")
    size: int = Field(0, description="Size of this layer in bytes")
    comment: str = Field("", description="Comment for this layer")
    tags: List[str] = Field(default_factory=list, description="Tags for this layer")

class ImageSearchResult(BaseModel):
    """Result of an image search operation."""
    name: str = Field(..., description="Image name")
    description: str = Field("", description="Image description")
    is_official: bool = Field(False, description="Whether this is an official image")
    is_automated: bool = Field(False, description="Whether this is an automated build")
    star_count: int = Field(0, description="Number of stars")
    pull_count: int = Field(0, description="Number of pulls")

class ImagePruneResult(BaseModel):
    """Result of an image prune operation."""
    images_deleted: List[str] = Field(
        default_factory=list,
        description="List of deleted image IDs"
    )
    space_reclaimed: int = Field(
        0,
        description="Disk space reclaimed in bytes"
    )

@mcp.tool(
    name="list_images",
    description="List Docker images with filtering options"
)
async def list_images(
    name: Annotated[Optional[str], Field(description="Filter by image name or name:tag")] = None,
    all: Annotated[bool, Field(default=False, description="Show all images (default hides intermediate images)")] = False,
    filters: Annotated[Dict[str, str], Field(default_factory=dict, description="Filter output based on conditions provided (e.g., `{'dangling': ['true']}`)")] = {},
    digests: Annotated[bool, Field(default=False, description="Show image digests")] = False
) -> Dict[str, Any]:
    """
    List Docker images with filtering options.
    
    This function lists all Docker images available on the host, with various
    filtering options to narrow down the results.
    
    Args:
        name: Filter by image name or name:tag
        all: Show all images (default hides intermediate images)
        filters: Filter output based on conditions provided
        digests: Show image digests
        
    Returns:
        Dictionary with list of images and metadata
        
    Example:
        >>> await list_images(
        ...     name="nginx",
        ...     filters={"dangling": ["false"]},
        ...     digests=True
        ... )
        {
            "status": "success",
            "images": [
                {
                    "id": "sha256:2d389e545974d4a93d7f3b91f433c5a1a8e4f971e2c8f8a8a8f8a8f8a8f8a8f8a",
                    "repo_tags": ["nginx:latest"],
                    "repo_digests": ["nginx@sha256:..."],
                    "created": "2023-01-01T12:00:00Z",
                    "size": 1337000000,
                    "virtual_size": 1337000000,
                    "labels": {"maintainer": "NGINX Docker Maintainers"},
                    "os": "linux",
                    "architecture": "amd64",
                    "docker_version": "20.10.7"
                }
            ],
            "count": 1
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Apply name filter if provided
        if name:
            filters['reference'] = [name]
        
        # Get images
        images = client.images.list(all=all, filters=filters)
        
        # Prepare response
        image_list = []
        
        for image in images:
            # Get detailed information for each image
            try:
                image_info = {
                    'id': image.id,
                    'repo_tags': image.tags if hasattr(image, 'tags') else [],
                    'repo_digests': image.attrs.get('RepoDigests', []),
                    'created': datetime.fromtimestamp(
                        image.attrs['Created'],
                        tz=datetime.timezone.utc
                    ).isoformat(),
                    'size': image.attrs['Size'],
                    'virtual_size': image.attrs.get('VirtualSize', image.attrs['Size']),
                    'labels': image.labels,
                    'os': image.attrs.get('Os'),
                    'architecture': image.attrs.get('Architecture'),
                    'docker_version': image.attrs.get('DockerVersion')
                }
                
                # Only include digests if requested
                if not digests:
                    image_info.pop('repo_digests', None)
                
                image_list.append(image_info)
                
            except Exception as e:
                logger.warning(f"Error processing image {image.id}: {str(e)}")
                continue
        
        return {
            'status': 'success',
            'images': image_list,
            'count': len(image_list)
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error listing images: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@mcp.tool()
async def get_image_history(image_id: str) -> Dict[str, Any]:
    """
    Get the history of a Docker image.
    
    This function retrieves the history of a Docker image, showing all layers
    and their metadata.
    
    Args:
        image_id: Image ID or name (optionally with tag)
        
    Returns:
        Dictionary with image history and metadata
        
    Example:
        >>> await get_image_history("nginx:alpine")
        {
            "status": "success",
            "image_id": "sha256:...",
            "history": [
                {
                    "id": "sha256:...",
                    "created": "2023-01-01T12:00:00Z",
                    "created_by": "/bin/sh -c #(nop) ADD file:...",
                    "size": 5494532,
                    "comment": "",
                    "tags": ["nginx:alpine"]
                },
                ...
            ],
            "total_size": 21500000,
            "layer_count": 5
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the image
        try:
            image = client.images.get(image_id)
        except ImageNotFound:
            return {
                'status': 'error',
                'error': f'Image not found: {image_id}'
            }
        
        # Get the image history
        history = image.history()
        
        # Process the history
        history_list = []
        total_size = 0
        
        for item in history:
            history_item = {
                'id': item['Id'],
                'created': datetime.fromtimestamp(item['Created']).isoformat(),
                'created_by': item.get('CreatedBy', ''),
                'size': item.get('Size', 0),
                'comment': item.get('Comment', ''),
                'tags': item.get('Tags', [])
            }
            history_list.append(history_item)
            total_size += item.get('Size', 0)
        
        return {
            'status': 'success',
            'image_id': image.id,
            'history': history_list,
            'total_size': total_size,
            'layer_count': len(history_list)
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error getting image history: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@mcp.tool(
    name="tag_image",
    description="Tag a Docker image"
)
async def tag_image(
    image_id: Annotated[str, Field(description="Source image ID or name (optionally with tag)")],
    repository: Annotated[str, Field(description="Repository to tag the image with")],
    tag: Annotated[str, Field(default="latest", description="Tag to apply to the image")] = "latest",
    force: Annotated[bool, Field(default=False, description="Force tagging even if the tag already exists")] = False
) -> Dict[str, Any]:
    """
    Tag a Docker image.
    
    This function adds a tag to an existing Docker image.
    
    Args:
        image_id: Source image ID or name (optionally with tag)
        repository: Repository to tag the image with
        tag: Tag to apply to the image
        force: Force tagging even if the tag already exists
        
    Returns:
        Dictionary with the tagging result
        
    Example:
        >>> await tag_image("nginx:alpine", "myregistry.example.com/myapp", "v1.0.0")
        {
            "status": "success",
            "source_image": "nginx:alpine",
            "target_image": "myregistry.example.com/myapp:v1.0.0"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the source image
        try:
            image = client.images.get(image_id)
        except ImageNotFound:
            return {
                'status': 'error',
                'error': f'Source image not found: {image_id}'
            }
        
        # Construct the target image reference
        target_ref = f"{repository}:{tag}" if tag else repository
        
        # Check if the target tag already exists
        if not force:
            try:
                existing = client.images.get(target_ref)
                if existing.id != image.id:
                    return {
                        'status': 'error',
                        'error': f'Tag {target_ref} already exists and points to a different image',
                        'existing_image_id': existing.id
                    }
            except ImageNotFound:
                pass  # Target doesn't exist, which is fine
        
        # Tag the image
        result = image.tag(repository=repository, tag=tag, force=force)
        
        if not result:
            return {
                'status': 'error',
                'error': f'Failed to tag image {image_id} as {target_ref}'
            }
        
        return {
            'status': 'success',
            'source_image': image_id,
            'target_image': target_ref
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'image_id': image_id,
            'target': f"{repository}:{tag}"
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'image_id': image_id
        }
        
    except Exception as e:
        error_msg = f"Unexpected error tagging image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }

@mcp.tool(
    name="search_images",
    description="Search Docker Hub for images"
)
async def search_images(
    term: Annotated[str, Field(description="Search term")],
    limit: Annotated[int, Field(description="Maximum number of results to return (1-100)", default=25, minimum=1, maximum=100)],
    filters: Annotated[Dict[str, str], Field(description="Additional filters (e.g., {'is-official': 'true'}", default={})]
) -> Dict[str, Any]:
    """
    Search Docker Hub for images.
    
    This function searches the Docker Hub registry for images matching
    the specified search term and filters.
    
    Args:
        term: Search term (e.g., 'nginx', 'python')
        limit: Maximum number of results to return (1-100)
        filters: Additional filters (e.g., {'is-official': 'true'})
        
    Returns:
        Dictionary with search results
        
    Example:
        >>> await search_images("nginx", limit=3, filters={"is-official": "true"})
        {
            "status": "success",
            "results": [
                {
                    "name": "nginx",
                    "description": "Official build of Nginx.",
                    "is_official": true,
                    "is_automated": false,
                    "star_count": 15000,
                    "pull_count": 1000000000
                },
                ...
            ],
            "count": 3
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Validate limit
        limit = max(1, min(100, limit))  # Ensure limit is between 1 and 100
        
        # Search for images
        results = client.images.search(term=term, limit=limit, filters=filters)
        
        # Process results
        result_list = []
        
        for item in results:
            result_list.append({
                'name': item['name'],
                'description': item.get('description', ''),
                'is_official': item.get('is_official', False),
                'is_automated': item.get('is_automated', False),
                'star_count': item.get('star_count', 0),
                'pull_count': item.get('pull_count', 0)
            })
        
        return {
            'status': 'success',
            'results': result_list,
            'count': len(result_list)
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'term': term
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error searching images: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'term': term
        }

@mcp.tool(
    name="prune_images",
    description="Remove unused Docker images"
)
async def prune_images(
    filters: Annotated[Dict[str, str], Field(description="Filters to process on the prune (e.g., {'dangling': ['true']}", default={})],
    dry_run: Annotated[bool, Field(description="If true, only show what would be deleted", default=False)]
) -> Dict[str, Any]:
    """
    Remove unused Docker images.
    
    This function removes unused (dangling) images, or images matching the
    specified filters.
    
    Args:
        filters: Filters to process on the prune
        dry_run: If true, only show what would be deleted
        
    Returns:
        Dictionary with prune results
        
    Example:
        >>> await prune_images(filters={"dangling": ["true"]})
        {
            "status": "success",
            "images_deleted": [
                {
                    "deleted": "sha256:...",
                    "untagged": ["none:none"]
                },
                ...
            ],
            "space_reclaimed": 123456789,
            "message": "Pruned 3 images (117.7 MB)"
        }
    """
    try:
        if dry_run:
            # For dry run, we'll just list the images that would be removed
            client = docker.from_env()
            dangling_images = client.images.list(filters={'dangling': True})
            
            # Calculate total size
            total_size = sum(img.attrs['Size'] for img in dangling_images)
            
            return {
                'status': 'success',
                'dry_run': True,
                'images_that_would_be_deleted': [img.id for img in dangling_images],
                'space_that_would_be_reclaimed': total_size,
                'count': len(dangling_images),
                'message': f'Would remove {len(dangling_images)} images ({total_size/1024/1024:.1f} MB)'
            }
        
        # Initialize Docker client
        client = docker.from_env()
        
        # Prune images
        result = client.images.prune(filters=filters)
        
        # Process the result
        images_deleted = result.get('ImagesDeleted', [])
        space_reclaimed = result.get('SpaceReclaimed', 0)
        
        return {
            'status': 'success',
            'images_deleted': images_deleted,
            'space_reclaimed': space_reclaimed,
            'count': len(images_deleted),
            'message': f'Pruned {len(images_deleted)} images ({space_reclaimed/1024/1024:.1f} MB)'
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error pruning images: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }
