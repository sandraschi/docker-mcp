"""
Container image management for Docker MCP.

This module provides tools for managing Docker images including listing, pulling,
building, and removing images. It follows FastMCP 2.12+ standards for tool registration
and error handling with Pydantic v2 models.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

import docker
from docker.errors import (
    APIError,
    BuildError,
    DockerException,
    ImageNotFound,
)
from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from dockermcp.logging_config import logger

from .models import ContainerImageResponse, ContainerOperationResponse

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

class ImagePullPolicy(StrEnum):
    """Policy for pulling container images."""
    ALWAYS = "always"
    IF_NOT_PRESENT = "if-not-present"
    NEVER = "never"

class ImageBuildStatus(StrEnum):
    """Status of an image build operation."""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ImagePullProgress(BaseModel):
    """Progress information for an image pull operation."""
    model_config = ConfigDict(extra='allow')

    id: str | None = Field(None, description="Image or layer ID")
    status: str | None = Field(None, description="Status message")
    progress: str | None = Field(None, description="Progress bar")
    progress_detail: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed progress information"
    )
    error: str | None = Field(None, description="Error message if any")

class ImageBuildResult(BaseModel):
    """Result of an image build operation."""
    image_id: str | None = Field(None, description="ID of the built image")
    logs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Build output logs"
    )
    status: ImageBuildStatus = Field(
        default=ImageBuildStatus.SUCCESS,
        description="Build status"
    )
    error: str | None = Field(None, description="Error message if build failed")

class ImageListRequest(BaseModel):
    """Request model for listing Docker images."""
    name: str | None = Field(None, description="Filter by image name or name:tag")
    all_images: bool = Field(False, description="Show all images (default hides intermediate images)")
    filters: dict[str, str] = Field(default_factory=dict, description="Filter output based on conditions provided")
    digests: bool = Field(False, description="Show image digests")

class ImagePullRequest(BaseModel):
    """Request model for pulling Docker images."""
    repository: str = Field(..., description="Repository name (and optionally a tag or digest)")
    tag: str = Field('latest', description="Tag to pull (default: latest)")
    auth: dict[str, str] | None = Field(None, description="Authentication credentials")
    platform: str | None = Field(None, description="Platform in the format os[/arch[/variant]]")
    all_tags: bool = Field(False, description="Download all tagged images in the repository")
    policy: ImagePullPolicy = Field(
        ImagePullPolicy.IF_NOT_PRESENT,
        description="When to pull the image (always, if-not-present, never)"
    )

class ImageBuildRequest(BaseModel):
    """Request model for building Docker images."""
    path: str = Field(..., description="Path to the directory containing the Dockerfile")
    dockerfile: str = Field('Dockerfile', description="Name of the Dockerfile")
    tag: str | None = Field(None, description="Name and optionally a tag in the 'name:tag' format")
    buildargs: dict[str, str] = Field(default_factory=dict, description="Build-time variables")
    labels: dict[str, str] = Field(default_factory=dict, description="Set metadata for the image")
    nocache: bool = Field(False, description="Do not use cache when building the image")
    rm: bool = Field(True, description="Remove intermediate containers after a successful build")
    forcerm: bool = Field(False, description="Always remove intermediate containers")
    pull: bool = Field(False, description="Attempt to pull a newer version of the image")
    platform: str | None = Field(None, description="Platform in the format os[/arch[/variant]]")
    target: str | None = Field(None, description="Set the target build stage to build")

class ImageRemoveRequest(BaseModel):
    """Request model for removing Docker images."""
    image: str = Field(..., description="Image ID or name (optionally with tag)")
    force: bool = Field(False, description="Force removal of the image even if it is being used")
    noprune: bool = Field(False, description="Do not delete untagged parent images")

@mcp.tool
async def list_images(params: ImageListRequest) -> ContainerImageResponse:
    """
    List Docker images with filtering options.

    This function lists all Docker images available on the host, with various
    filtering options to narrow down the results.

    Args:
        params: ImageListRequest containing filtering options

    Returns:
        ContainerImageResponse with list of images and metadata
    """
    try:
        # Initialize Docker client
        client = docker.from_env()

        # Apply name filter if provided
        filters = dict(params.filters)
        if params.name:
            filters['reference'] = [params.name]

        # Get images
        images = client.images.list(all=params.all_images, filters=filters)

        # Prepare response data
        image_list = []

        for image in images:
            try:
                image_info = {
                    'id': image.id,
                    'repo_tags': image.tags if hasattr(image, 'tags') else [],
                    'repo_digests': image.attrs.get('RepoDigests', []) if params.digests else [],
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

                image_list.append(image_info)

            except Exception as e:
                logger.warning(f"Error processing image {getattr(image, 'id', 'unknown')}: {str(e)}")
                continue

        return ContainerImageResponse.success(
            images=image_list,
            count=len(image_list),
            message=f"Found {len(image_list)} images"
        )

    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerImageResponse.error(
            error=error_msg,
            message="Failed to list images"
        )

    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerImageResponse.error(
            error=error_msg,
            message="Docker daemon not available"
        )

    except Exception as e:
        error_msg = f"Unexpected error listing images: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerImageResponse.error(
            error=error_msg,
            message="An unexpected error occurred"
        )

@mcp.tool
async def pull_image(params: ImagePullRequest) -> ContainerImageResponse:
    """
    Pull a Docker image from a registry.

    Args:
        params: ImagePullRequest containing pull parameters

    Returns:
        ContainerImageResponse with the pull results
    """
    try:
        # Initialize Docker client
        client = docker.from_env()

        # Check if image already exists
        image_tag = f"{params.repository}:{params.tag}" if params.tag and ':' not in params.repository else params.repository

        if params.policy == ImagePullPolicy.IF_NOT_PRESENT:
            try:
                existing_image = client.images.get(image_tag)
                return ContainerImageResponse.success(
                    image_id=existing_image.id,
                    repository=params.repository,
                    tag=params.tag,
                    message=f"Image already exists: {image_tag}",
                    cached=True,
                    digest=existing_image.attrs.get('RepoDigests', [None])[0]
                )
            except (ImageNotFound, APIError):
                pass  # Image doesn't exist, proceed with pull
        elif params.policy == ImagePullPolicy.NEVER:
            return ContainerImageResponse.error(
                error="Pull policy is set to 'never'",
                message="Image pull skipped due to pull policy"
            )

        # Pull the image
        pull_kwargs = {
            'repository': params.repository,
            'tag': params.tag,
            'all_tags': params.all_tags,
            'platform': params.platform
        }

        if params.auth:
            pull_kwargs['auth_config'] = params.auth

        # Execute the pull
        image = client.images.pull(**{k: v for k, v in pull_kwargs.items() if v is not None})

        return ContainerImageResponse.success(
            image_id=image.id,
            repository=params.repository,
            tag=params.tag,
            message=f"Successfully pulled {image_tag}",
            digest=image.attrs.get('RepoDigests', [None])[0]
        )

    except APIError as e:
        error_msg = f"Failed to pull image {params.repository}:{params.tag}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerImageResponse.error(
            error=error_msg,
            message="Failed to pull image"
        )

    except Exception as e:
        error_msg = f"Unexpected error pulling image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerImageResponse.error(
            error=error_msg,
            message="An unexpected error occurred"
        )

@mcp.tool
async def build_image(params: ImageBuildRequest) -> ContainerImageResponse:
    """
    Build a Docker image from a Dockerfile.

    Args:
        params: ImageBuildRequest containing build parameters

    Returns:
        ContainerImageResponse with the build results
    """
    try:
        # Initialize Docker client
        client = docker.from_env()

        # Prepare build arguments
        build_kwargs = {
            'path': params.path,
            'dockerfile': params.dockerfile,
            'tag': params.tag,
            'buildargs': params.buildargs,
            'labels': params.labels,
            'nocache': params.nocache,
            'rm': params.rm,
            'forcerm': params.forcerm,
            'pull': params.pull,
            'platform': params.platform,
            'target': params.target
        }

        # Clean up None values
        build_kwargs = {k: v for k, v in build_kwargs.items() if v is not None}

        # Build the image
        build_logs = []
        try:
            # Use a list to collect logs
            logs = client.api.build(**build_kwargs, decode=True)

            # Process the build logs
            for chunk in logs:
                if 'stream' in chunk:
                    build_logs.append({'stream': chunk['stream'].strip()})
                elif 'status' in chunk:
                    build_logs.append({'status': chunk['status']})
                elif 'error' in chunk:
                    error_msg = chunk['error']
                    logger.error(f"Build error: {error_msg}")
                    return ContainerImageResponse.error(
                        error=error_msg,
                        message="Build failed",
                        logs=build_logs
                    )

            # Get the image ID from the last line of the build output
            if build_logs and 'Successfully built' in build_logs[-1].get('stream', ''):
                image_id = build_logs[-1]['stream'].split(' ')[-1].strip()
                return ContainerImageResponse.success(
                    image_id=image_id,
                    message=f"Successfully built {params.tag or 'image'}",
                    logs=build_logs
                )
            else:
                return ContainerImageResponse.error(
                    error="Build did not complete successfully",
                    message="Build failed",
                    logs=build_logs
                )

        except BuildError as e:
            error_msg = f"Build error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ContainerImageResponse.error(
                error=error_msg,
                message="Build failed",
                logs=build_logs
            )

    except Exception as e:
        error_msg = f"Unexpected error during build: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerImageResponse.error(
            error=error_msg,
            message="An unexpected error occurred during build"
        )

@mcp.tool
async def remove_image(params: ImageRemoveRequest) -> ContainerOperationResponse:
    """
    Remove a Docker image.

    Args:
        params: ImageRemoveRequest containing removal parameters

    Returns:
        ContainerOperationResponse with the removal results
    """
    try:
        # Initialize Docker client
        client = docker.from_env()

        # Remove the image
        client.images.remove(
            image=params.image,
            force=params.force,
            noprune=params.noprune
        )

        return ContainerOperationResponse.success(
            message=f"Successfully removed image {params.image}"
        )

    except ImageNotFound:
        error_msg = f"Image not found: {params.image}"
        logger.warning(error_msg)
        return ContainerOperationResponse.error(
            error=error_msg,
            message=f"Image {params.image} not found"
        )

    except APIError as e:
        error_msg = f"Failed to remove image {params.image}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerOperationResponse.error(
            error=error_msg,
            message="Failed to remove image"
        )

    except Exception as e:
        error_msg = f"Unexpected error removing image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ContainerOperationResponse.error(
            error=error_msg,
            message="An unexpected error occurred"
        )

# Register the tools with MCP
__all__ = [
    'list_images',
    'pull_image',
    'build_image',
    'remove_image',
    'ImageListRequest',
    'ImagePullRequest',
    'ImageBuildRequest',
    'ImageRemoveRequest',
    'ImagePullPolicy',
    'ImageBuildStatus'
]
