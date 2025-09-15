"""
Container image management for Docker MCP.

This module provides tools for managing Docker images including listing, pulling,
building, and removing images. It follows FastMCP 2.12+ standards for tool registration
and error handling.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import tarfile
import tempfile
from datetime import datetime
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple

import docker
from docker.errors import (
    DockerException, APIError, ImageNotFound, BuildError, 
    ContainerError, NotFound
)
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, field_validator, HttpUrl

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import get_mcp

# Get the shared FastMCP instance
mcp = get_mcp()

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

@mcp.tool()
async def list_images(
    name: Optional[str] = None,
    all: bool = False,
    filters: Dict[str, str] = {},
    digests: bool = False
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
                        image.attrs['Created']
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
        raise ToolError(error_msg)
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        raise ToolError("Docker daemon not available")
        
    except Exception as e:
        error_msg = f"Unexpected error listing images: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg)

@mcp.tool()
async def pull_image(
    repository: str,
    tag: str = 'latest',
    auth: Optional[Dict[str, str]] = None,
    platform: Optional[str] = None,
    all_tags: bool = False,
    policy: str = 'if-not-present'
) -> Dict[str, Any]:
    """
    Pull a Docker image from a registry.
    
    Args:
        repository: Repository name (and optionally a tag or digest)
        tag: Tag to pull (default: latest)
        auth: Authentication credentials
        platform: Platform in the format os[/arch[/variant]]
        all_tags: Download all tagged images in the repository
        policy: When to pull the image (always, if-not-present, never)
        
    Returns:
        Dictionary with the pull results
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Check if image already exists
        image_tag = f"{repository}:{tag}" if tag and ':' not in repository else repository
        
        if policy == ImagePullPolicy.IF_NOT_PRESENT:
            try:
                existing_image = client.images.get(image_tag)
                return {
                    'status': 'success',
                    'message': f'Image already exists: {image_tag}',
                    'image_id': existing_image.id,
                    'repository': repository,
                    'tag': tag,
                    'digest': existing_image.attrs.get('RepoDigests', [None])[0],
                    'platform': platform,
                    'cached': True
                }
            except (ImageNotFound, APIError):
                pass  # Image doesn't exist, continue with pull
        elif policy == ImagePullPolicy.NEVER:
            # Try to get the local image
            try:
                existing_image = client.images.get(image_tag)
                return {
                    'status': 'success',
                    'message': f'Using local image: {image_tag}',
                    'image_id': existing_image.id,
                    'repository': repository,
                    'tag': tag,
                    'digest': existing_image.attrs.get('RepoDigests', [None])[0],
                    'platform': platform,
                    'cached': True
                }
            except (ImageNotFound, APIError) as e:
                raise ToolError(f'Image not found locally and pull policy is "never": {str(e)}')
        
        # Prepare auth config
        auth_config = None
        if auth:
            auth_config = {
                'username': auth.get('username', ''),
                'password': auth.get('password', ''),
                'email': auth.get('email', ''),
                'registry': auth.get('registry', '')
            }
        
        # Pull the image using high-level API
        try:
            image = client.images.pull(repository, tag=tag, auth_config=auth_config, platform=platform, all_tags=all_tags)
            
            return {
                'status': 'success',
                'image_id': image.id,
                'repository': repository,
                'tag': tag,
                'digest': image.attrs.get('RepoDigests', [None])[0],
                'platform': platform
            }
            
        except Exception as e:
            error_msg = f"Error during image pull: {str(e)}"
            logger.error(error_msg)
            raise ToolError(error_msg)
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        raise ToolError(error_msg)
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        raise ToolError("Docker daemon not available")
        
    except Exception as e:
        error_msg = f"Unexpected error pulling image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg)

@mcp.tool()
async def build_image(
    path: str,
    dockerfile: str = 'Dockerfile',
    tag: Optional[str] = None,
    buildargs: Dict[str, str] = {},
    labels: Dict[str, str] = {},
    nocache: bool = False,
    rm: bool = True,
    forcerm: bool = False,
    pull: bool = False,
    platform: Optional[str] = None,
    target: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a Docker image from a Dockerfile.
    
    Args:
        path: Path to the directory containing the Dockerfile
        dockerfile: Name of the Dockerfile (default: Dockerfile)
        tag: Name and optionally a tag in the 'name:tag' format
        buildargs: Build-time variables
        labels: Set metadata for the image
        nocache: Do not use cache when building the image
        rm: Remove intermediate containers after a successful build
        forcerm: Always remove intermediate containers
        pull: Attempt to pull a newer version of the image
        platform: Platform in the format os[/arch[/variant]]
        target: Set the target build stage to build
        
    Returns:
        Dictionary with the build results
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Build the image
        try:
            image, logs = client.images.build(
                path=path,
                dockerfile=dockerfile,
                tag=tag,
                buildargs=buildargs,
                labels=labels,
                nocache=nocache,
                rm=rm,
                forcerm=forcerm,
                pull=pull,
                platform=platform,
                target=target
            )
            
            # Process logs
            build_logs = []
            for log in logs:
                if 'stream' in log:
                    build_logs.append({'stream': log['stream'].strip()})
                elif 'error' in log:
                    build_logs.append({'error': log['error'].strip()})
            
            return {
                'status': 'success',
                'image_id': image.id,
                'tag': tag,
                'logs': build_logs
            }
            
        except Exception as e:
            error_msg = f"Error during image build: {str(e)}"
            logger.error(error_msg)
            raise ToolError(error_msg)
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        raise ToolError(error_msg)
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        raise ToolError("Docker daemon not available")
        
    except Exception as e:
        error_msg = f"Unexpected error building image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg)

@mcp.tool()
async def remove_image(
    image: str,
    force: bool = False,
    noprune: bool = False
) -> Dict[str, Any]:
    """
    Remove a Docker image.
    
    Args:
        image: Image ID or name (optionally with tag)
        force: Force removal of the image even if it is being used
        noprune: Do not delete untagged parent images
        
    Returns:
        Dictionary with the removal results
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the image
        try:
            img = client.images.get(image)
        except ImageNotFound:
            raise ToolError(f'Image not found: {image}')
        
        # Remove the image
        result = client.images.remove(
            image=image,
            force=force,
            noprune=noprune
        )
        
        # Process the result
        if isinstance(result, list):
            # For newer Docker versions, result is a list of dicts
            untagged = [item.get('Untagged') for item in result if 'Untagged' in item]
            deleted = [item.get('Deleted') for item in result if 'Deleted' in item]
        else:
            # For older Docker versions, result is a dict
            untagged = result.get('Untagged', [])
            deleted = result.get('Deleted', [])
        
        return {
            'status': 'success',
            'image': image,
            'untagged': untagged,
            'deleted': deleted
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        raise ToolError(error_msg)
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        raise ToolError("Docker daemon not available")
        
    except Exception as e:
        error_msg = f"Unexpected error removing image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg)
