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
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, validator, HttpUrl

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

@Tool(
    name="list_images",
    description="List Docker images",
    parameters={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'default': None,
                'description': 'Filter by image name or name:tag'
            },
            'all': {
                'type': 'boolean',
                'default': False,
                'description': 'Show all images (default hides intermediate images)'
            },
            'filters': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Filter output based on conditions provided (e.g., `{"dangling":["true"]}`)'
            },
            'digests': {
                'type': 'boolean',
                'default': False,
                'description': 'Show image digests'
            }
        }
    }
)
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

@Tool(
    name="pull_image",
    description="Pull a Docker image from a registry",
    parameters={
        'type': 'object',
        'properties': {
            'repository': {
                'type': 'string',
                'description': 'Repository name (and optionally a tag or digest)'
            },
            'tag': {
                'type': 'string',
                'default': 'latest',
                'description': 'Tag to pull (default: latest)'
            },
            'auth': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'},
                    'email': {'type': 'string'},
                    'registry': {'type': 'string'}
                },
                'additionalProperties': False,
                'description': 'Authentication credentials'
            },
            'platform': {
                'type': 'string',
                'default': None,
                'description': 'Platform in the format os[/arch[/variant]] (e.g., linux/amd64)'
            },
            'all_tags': {
                'type': 'boolean',
                'default': False,
                'description': 'Download all tagged images in the repository'
            },
            'policy': {
                'type': 'string',
                'enum': [e.value for e in ImagePullPolicy],
                'default': 'if-not-present',
                'description': 'When to pull the image (always, if-not-present, never)'
            }
        },
        'required': ['repository']
    }
)
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
    
    This function pulls a Docker image from a registry with support for authentication,
    platform selection, and pull policies.
    
    Args:
        repository: Repository name (and optionally a tag or digest)
        tag: Tag to pull (default: latest)
        auth: Authentication credentials
        platform: Platform in the format os[/arch[/variant]]
        all_tags: Download all tagged images in the repository
        policy: When to pull the image (always, if-not-present, never)
        
    Returns:
        Dictionary with the pull results
        
    Example:
        >>> await pull_image(
        ...     repository="nginx",
        ...     tag="alpine",
        ...     auth={"username": "user", "password": "pass"},
        ...     platform="linux/amd64"
        ... )
        {
            "status": "success",
            "image_id": "sha256:...",
            "repository": "nginx",
            "tag": "alpine",
            "digest": "sha256:...",
            "platform": "linux/amd64",
            "progress": [
                {"status": "Pulling from library/nginx", "id": "alpine"},
                {"status": "Digest: sha256:..."},
                {"status": "Status: Downloaded newer image for nginx:alpine"}
            ]
        }
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
                return {
                    'status': 'error',
                    'error': f'Image not found locally and pull policy is "never": {str(e)}',
                    'repository': repository,
                    'tag': tag
                }
        
        # Prepare auth config
        auth_config = None
        if auth:
            auth_config = {
                'username': auth.get('username', ''),
                'password': auth.get('password', ''),
                'email': auth.get('email', ''),
                'registry': auth.get('registry', '')
            }
            
            # If registry is provided, remove it from the repository
            if auth.get('registry') and repository.startswith(auth['registry']):
                repository = repository[len(auth['registry']) + 1:]
        
        # Pull the image
        pull_kwargs = {
            'repository': repository,
            'tag': tag,
            'auth_config': auth_config,
            'platform': platform,
            'all_tags': all_tags,
            'decode': True
        }
        
        # Remove None values
        pull_kwargs = {k: v for k, v in pull_kwargs.items() if v is not None}
        
        # Execute the pull and capture the output
        progress = []
        try:
            # Low-level API for better progress tracking
            api_client = docker.APIClient()
            pull_logs = api_client.pull(
                repository=repository,
                tag=tag,
                auth_config=auth_config,
                platform=platform,
                all_tags=all_tags,
                stream=True,
                decode=True
            )
            
            # Process the pull logs
            for log in pull_logs:
                progress.append(log)
                logger.debug(f"Docker pull: {log}")
            
            # Get the pulled image
            if all_tags:
                # For all_tags, we can't easily determine which tags were pulled
                image_id = f"{repository}:*"
                digest = "multiple"
            else:
                image_ref = f"{repository}:{tag}" if tag and ':' not in repository else repository
                try:
                    image = client.images.get(image_ref)
                    image_id = image.id
                    digest = image.attrs.get('RepoDigests', [None])[0]
                except (ImageNotFound, APIError):
                    # Try to find the image by digest from the pull logs
                    image_id = next(
                        (log.get('id') for log in reversed(progress) 
                         if 'id' in log and 'digest' in log),
                        None
                    )
                    digest = next(
                        (log.get('digest') for log in reversed(progress) 
                         if 'digest' in log),
                        None
                    )
                    
                    if not image_id:
                        return {
                            'status': 'error',
                            'error': 'Failed to determine pulled image ID',
                            'repository': repository,
                            'tag': tag,
                            'progress': progress
                        }
        except Exception as e:
            error_msg = f"Error during image pull: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'error': error_msg,
                'repository': repository,
                'tag': tag,
                'progress': progress
            }
        finally:
            try:
                api_client.close()
            except:
                pass
        
        return {
            'status': 'success',
            'image_id': image_id,
            'repository': repository,
            'tag': tag,
            'digest': digest,
            'platform': platform,
            'progress': progress
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'repository': repository,
            'tag': tag
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'repository': repository,
            'tag': tag
        }
        
    except Exception as e:
        error_msg = f"Unexpected error pulling image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'repository': repository,
            'tag': tag
        }

@Tool(
    name="build_image",
    description="Build a Docker image from a Dockerfile",
    parameters={
        'type': 'object',
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Path to the directory containing the Dockerfile'
            },
            'dockerfile': {
                'type': 'string',
                'default': 'Dockerfile',
                'description': 'Name of the Dockerfile (default: Dockerfile)'
            },
            'tag': {
                'type': 'string',
                'default': None,
                'description': 'Name and optionally a tag in the \'name:tag\' format'
            },
            'buildargs': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Build-time variables'
            },
            'labels': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Set metadata for the image'
            },
            'nocache': {
                'type': 'boolean',
                'default': False,
                'description': 'Do not use cache when building the image'
            },
            'rm': {
                'type': 'boolean',
                'default': True,
                'description': 'Remove intermediate containers after a successful build'
            },
            'forcerm': {
                'type': 'boolean',
                'default': False,
                'description': 'Always remove intermediate containers'
            },
            'pull': {
                'type': 'boolean',
                'default': False,
                'description': 'Attempt to pull a newer version of the image'
            },
            'platform': {
                'type': 'string',
                'default': None,
                'description': 'Platform in the format os[/arch[/variant]]'
            },
            'target': {
                'type': 'string',
                'default': None,
                'description': 'Set the target build stage to build'
            },
            'network_mode': {
                'type': 'string',
                'default': None,
                'description': 'Set the networking mode for the RUN instructions during build'
            },
            'squash': {
                'type': 'boolean',
                'default': False,
                'description': 'Squash newly built layers into a single new layer'
            },
            'extra_hosts': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
                'default': {},
                'description': 'Extra hosts to add to /etc/hosts in building containers'
            },
            'shmsize': {
                'type': 'string',
                'default': None,
                'description': 'Size of /dev/shm in bytes. The size must be greater than 0.'
            },
            'quiet': {
                'type': 'boolean',
                'default': False,
                'description': 'Suppress verbose build output'
            },
            'timeout': {
                'type': 'integer',
                'minimum': 0,
                'default': 0,
                'description': 'HTTP timeout in seconds (0 means no timeout)'
            }
        },
        'required': ['path']
    }
)
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
    target: Optional[str] = None,
    network_mode: Optional[str] = None,
    squash: bool = False,
    extra_hosts: Dict[str, str] = {},
    shmsize: Optional[str] = None,
    quiet: bool = False,
    timeout: int = 0
) -> Dict[str, Any]:
    """
    Build a Docker image from a Dockerfile.
    
    This function builds a Docker image from a Dockerfile with support for various
    build options and configurations.
    
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
        network_mode: Set the networking mode for the RUN instructions during build
        squash: Squash newly built layers into a single new layer
        extra_hosts: Extra hosts to add to /etc/hosts in building containers
        shmsize: Size of /dev/shm in bytes
        quiet: Suppress verbose build output
        timeout: HTTP timeout in seconds (0 means no timeout)
        
    Returns:
        Dictionary with the build results
        
    Example:
        >>> await build_image(
        ...     path="/path/to/build/context",
        ...     dockerfile="Dockerfile.alpine",
        ...     tag="myapp:1.0.0",
        ...     buildargs={"VERSION": "1.0.0"},
        ...     labels={"maintainer": "dev@example.com"},
        ...     platform="linux/amd64"
        ... )
        {
            "status": "success",
            "image_id": "sha256:...",
            "tag": "myapp:1.0.0",
            "logs": [
                {"stream": "Step 1/10 : FROM alpine:3.14\n"},
                {"stream": " ---> 14119a10abf4\n"},
                {"stream": "Step 2/10 : WORKDIR /app\n"},
                {"stream": " ---> Running in 8c4d8a4f8a4f\n"},
                {"stream": " ---> 5f70bf18a086\n"},
                {"stream": "Successfully built 5f70bf18a086\n"},
                {"stream": "Successfully tagged myapp:1.0.0\n"}
            ]
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Prepare build arguments
        build_kwargs = {
            'path': path,
            'dockerfile': dockerfile,
            'tag': tag,
            'buildargs': buildargs,
            'labels': labels,
            'nocache': nocache,
            'rm': rm,
            'forcerm': forcerm,
            'pull': pull,
            'platform': platform,
            'target': target,
            'network_mode': network_mode,
            'squash': squash,
            'extra_hosts': extra_hosts,
            'shmsize': shmsize,
            'quiet': quiet,
            'timeout': timeout,
            'decode': True
        }
        
        # Remove None values
        build_kwargs = {k: v for k, v in build_kwargs.items() if v is not None}
        
        # Build the image
        build_logs = []
        try:
            # Low-level API for better build log handling
            api_client = docker.APIClient()
            
            # Create a build context tar file
            def create_tar(path):
                f = BytesIO()
                with tarfile.open(fileobj=f, mode='w') as tar:
                    for root, _, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, path)
                            tar.add(file_path, arcname=arcname)
                f.seek(0)
                return f
            
            # Create the build context
            build_context = create_tar(path)
            
            # Execute the build
            for line in api_client.build(
                fileobj=build_context,
                custom_context=True,
                **{k: v for k, v in build_kwargs.items() if k != 'path'}
            ):
                if 'stream' in line:
                    line_text = line['stream'].strip()
                    if line_text:
                        build_logs.append({'stream': line_text})
                        logger.info(f"Build: {line_text}")
                elif 'error' in line:
                    error_msg = line['error'].strip()
                    build_logs.append({'error': error_msg})
                    logger.error(f"Build error: {error_msg}")
                    return {
                        'status': 'error',
                        'error': error_msg,
                        'logs': build_logs
                    }
                elif 'status' in line:
                    status = line['status'].strip()
                    if status:
                        build_logs.append({'status': status})
                        logger.info(f"Build status: {status}")
                elif 'aux' in line and 'ID' in line['aux']:
                    image_id = line['aux']['ID']
                
                # Check for build success/failure
                if 'stream' in line and 'Successfully built' in line['stream']:
                    image_id = line['stream'].strip().split(' ')[-1]
                elif 'error' in line:
                    return {
                        'status': 'error',
                        'error': line['error'].strip(),
                        'logs': build_logs
                    }
            
            # If we got here, the build was successful
            return {
                'status': 'success',
                'image_id': image_id,
                'tag': tag,
                'logs': build_logs
            }
            
        except Exception as e:
            error_msg = f"Error during image build: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'status': 'error',
                'error': error_msg,
                'logs': build_logs
            }
        finally:
            try:
                api_client.close()
            except:
                pass
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg,
            'path': path,
            'dockerfile': dockerfile,
            'tag': tag
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'path': path,
            'dockerfile': dockerfile,
            'tag': tag
        }
        
    except Exception as e:
        error_msg = f"Unexpected error building image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'path': path,
            'dockerfile': dockerfile,
            'tag': tag
        }

@Tool(
    name="remove_image",
    description="Remove a Docker image",
    parameters={
        'type': 'object',
        'properties': {
            'image': {
                'type': 'string',
                'description': 'Image ID or name (optionally with tag)'
            },
            'force': {
                'type': 'boolean',
                'default': False,
                'description': 'Force removal of the image even if it is being used'
            },
            'noprune': {
                'type': 'boolean',
                'default': False,
                'description': 'Do not delete untagged parent images'
            }
        },
        'required': ['image']
    }
)
async def remove_image(
    image: str,
    force: bool = False,
    noprune: bool = False
) -> Dict[str, Any]:
    """
    Remove a Docker image.
    
    This function removes a Docker image by ID or name, with options to force
    removal and control pruning of untagged parent images.
    
    Args:
        image: Image ID or name (optionally with tag)
        force: Force removal of the image even if it is being used
        noprune: Do not delete untagged parent images
        
    Returns:
        Dictionary with the removal results
        
    Example:
        >>> await remove_image("nginx:alpine", force=True)
        {
            "status": "success",
            "image": "nginx:alpine",
            "untagged": ["nginx:alpine"],
            "deleted": ["sha256:..."]
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the image
        try:
            img = client.images.get(image)
        except ImageNotFound:
            return {
                'status': 'error',
                'error': f'Image not found: {image}'
            }
        
        # Remove the image
        result = client.images.remove(
            image=image,
            force=force,
            noprune=noprune
        )
        
        # Process the result
        if isinstance(result, list):
            # For newer Docker versions, result is a list of strings
            untagged = [line for line in result if 'Untagged' in line]
            deleted = [line for line in result if 'Deleted' in line]
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
        return {
            'status': 'error',
            'error': error_msg,
            'image': image
        }
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': "Docker daemon not available",
            'image': image
        }
        
    except Exception as e:
        error_msg = f"Unexpected error removing image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'image': image
        }
