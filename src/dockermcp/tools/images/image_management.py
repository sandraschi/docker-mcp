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

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from docker.errors import (
    APIError,
    DockerException,
    ImageNotFound,
)
from pydantic import BaseModel, ConfigDict, Field

from dockermcp.docker_context import check_docker_available, docker_client
from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"id": "sha256:...", "status": "Downloading", "progress": "[=====>              ] 45%"}
        }
    )

    id: str | None = Field(default=None, description="Image or layer ID")
    status: str | None = Field(default=None, description="Status message")
    progress: str | None = Field(default=None, description="Progress bar")
    progress_detail: dict[str, Any] = Field(default_factory=dict, description="Detailed progress information")
    error: str | None = Field(default=None, description="Error message if any")


class ImageBuildResult(BaseModel):
    """Result of an image build operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "image_id": "sha256:...",
                "status": "success",
                "logs": [{"stream": "Successfully built abc123"}],
            }
        }
    )

    image_id: str | None = Field(default=None, description="ID of the built image")
    logs: list[dict[str, Any]] = Field(default_factory=list, description="Build output logs")
    status: ImageBuildStatus = Field(default=ImageBuildStatus.SUCCESS, description="Build status")
    error: str | None = Field(default=None, description="Error message if build failed")


class ImageLayer(BaseModel):
    """Represents a layer in a Docker image."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"id": "sha256:...", "size": 12345678, "empty_layer": False}}
    )

    id: str = Field(..., description="Layer ID")
    created: datetime | None = Field(default=None, description="Creation timestamp")
    created_by: str | None = Field(default=None, description="Command that created the layer")
    size: int = Field(default=0, description="Size of the layer in bytes")
    comment: str | None = Field(default=None, description="Optional comment")
    empty_layer: bool = Field(default=False, description="Whether this is an empty layer")


class ImageHistoryItem(BaseModel):
    """Represents an entry in the image history."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sha256:...",
                "created": "2023-01-01T12:00:00Z",
                "created_by": "/bin/sh -c #(nop) ADD file:...",
                "size": 12345678,
            }
        }
    )

    id: str = Field(..., description="Layer ID")
    created: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="Command that created this layer")
    size: int = Field(default=0, description="Size of this layer in bytes")
    comment: str = Field(default="", description="Comment for this layer")
    tags: list[str] = Field(default_factory=list, description="Tags for this layer")


class ImageSearchResult(BaseModel):
    """Result of an image search operation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "nginx",
                "description": "Official build of Nginx.",
                "is_official": True,
                "star_count": 15000,
            }
        }
    )

    name: str = Field(..., description="Image name")
    description: str = Field(default="", description="Image description")
    is_official: bool = Field(default=False, description="Whether this is an official image")
    is_automated: bool = Field(default=False, description="Whether this is an automated build")
    star_count: int = Field(default=0, description="Number of stars")
    pull_count: int = Field(default=0, description="Number of pulls")


class ImageCompareResult(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"image_a": {...}, "image_b": {...}, "differences": {...}}})

    image_a: dict[str, Any]
    image_b: dict[str, Any]
    differences: dict[str, Any]


class ImagePruneResult(BaseModel):
    """Result of an image prune operation."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"images_deleted": ["sha256:..."], "space_reclaimed": 123456789}}
    )

    images_deleted: list[str] = Field(default_factory=list, description="List of deleted image IDs")
    space_reclaimed: int = Field(default=0, description="Disk space reclaimed in bytes")


@mcp.tool
@check_docker_available
async def list_images(
    name: str | None = Field(default=None, description="Filter by image name or name:tag"),
    all: bool = Field(default=False, description="Show all images (default hides intermediate images)"),
    filters: dict[str, str] = Field(
        default_factory=dict, description="Filter output based on conditions provided (e.g., `{'dangling': ['true']}`)"
    ),
    digests: bool = Field(default=False, description="Show image digests"),
) -> dict[str, Any]:
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
        # If called directly as a Python function (not via FastMCP reflection), Field defaults may be FieldInfo objects
        if hasattr(name, "default"):
            name = None
        if hasattr(all, "default"):
            all = False
        if hasattr(filters, "default"):
            filters = {}
        else:
            filters = dict(filters) if filters else {}
        if hasattr(digests, "default"):
            digests = False

        # Use shared client
        client = docker_client

        # Apply name filter if provided
        if name:
            filters["reference"] = [name]

        # Get images
        images = client.images.list(all=all, filters=filters)

        # Prepare response
        image_list = []

        for image in images:
            # Get detailed information for each image
            try:
                tags = image.tags if hasattr(image, "tags") else []
                attrs = image.attrs or {}
                labels = attrs.get("Labels") or {}
                if not isinstance(labels, dict):
                    labels = {}
                image_info = {
                    "id": image.id,
                    "repo_tags": tags,
                    "repo_digests": attrs.get("RepoDigests", []),
                    "created": (
                        datetime.fromtimestamp(attrs["Created"], tz=UTC).isoformat()
                        if isinstance(attrs.get("Created"), (int, float))
                        else str(attrs.get("Created", ""))
                    ),
                    "size": attrs.get("Size", 0),
                    "shared_size": attrs.get("SharedSize", 0),
                    "virtual_size": attrs.get("VirtualSize", attrs.get("Size", 0)),
                    "labels": labels,
                    "os": attrs.get("Os"),
                    "architecture": attrs.get("Architecture"),
                    "docker_version": attrs.get("DockerVersion"),
                    "dangling": not tags,
                    "containers": attrs.get("Containers", -1),
                }

                # Only include digests if requested
                if not digests:
                    image_info.pop("repo_digests", None)

                image_list.append(image_info)

            except Exception as e:
                logger.warning(f"Error processing image {image.id}: {e!s}")
                continue

        return {"status": "success", "images": image_list, "count": len(image_list)}

    except APIError as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    except DockerException as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}

    except Exception as e:
        error_msg = f"Unexpected error listing images: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}


@mcp.tool()
@check_docker_available
async def get_image_history(image_id: str) -> dict[str, Any]:
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
        # Use shared client
        client = docker_client

        # Get the image
        try:
            image = client.images.get(image_id)
        except ImageNotFound:
            return {"status": "error", "error": f"Image not found: {image_id}"}

        # Get the image history
        history = image.history()

        # Process the history
        history_list = []
        total_size = 0

        for item in history:
            history_item = {
                "id": item["Id"],
                "created": datetime.fromtimestamp(item["Created"]).isoformat(),
                "created_by": item.get("CreatedBy", ""),
                "size": item.get("Size", 0),
                "comment": item.get("Comment", ""),
                "tags": item.get("Tags", []),
            }
            history_list.append(history_item)
            total_size += item.get("Size", 0)

        return {
            "status": "success",
            "image_id": image.id,
            "history": history_list,
            "total_size": total_size,
            "layer_count": len(history_list),
        }

    except APIError as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    except DockerException as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}

    except Exception as e:
        error_msg = f"Unexpected error getting image history: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}


@mcp.tool
@check_docker_available
async def tag_image(
    image_id: str = Field(..., description="Source image ID or name (optionally with tag)"),
    repository: str = Field(..., description="Repository to tag the image with"),
    tag: str = Field(default="latest", description="Tag to apply to the image"),
    force: bool = Field(default=False, description="Force tagging even if the tag already exists"),
) -> dict[str, Any]:
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
        # Use shared client
        client = docker_client

        # Get the source image
        try:
            image = client.images.get(image_id)
        except ImageNotFound:
            return {"status": "error", "error": f"Source image not found: {image_id}"}

        # Construct the target image reference
        target_ref = f"{repository}:{tag}" if tag else repository

        # Check if the target tag already exists
        if not force:
            try:
                existing = client.images.get(target_ref)
                if existing.id != image.id:
                    return {
                        "status": "error",
                        "error": f"Tag {target_ref} already exists and points to a different image",
                        "existing_image_id": existing.id,
                    }
            except ImageNotFound:
                pass  # Target doesn't exist, which is fine

        # Tag the image
        result = image.tag(repository=repository, tag=tag, force=force)

        if not result:
            return {"status": "error", "error": f"Failed to tag image {image_id} as {target_ref}"}

        return {"status": "success", "source_image": image_id, "target_image": target_ref}

    except APIError as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg, "image_id": image_id, "target": f"{repository}:{tag}"}

    except DockerException as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available", "image_id": image_id}

    except Exception as e:
        error_msg = f"Unexpected error tagging image: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}


@mcp.tool
@check_docker_available
async def search_images(
    term: str = Field(..., description="Search term"),
    limit: int = Field(default=25, ge=1, le=100, description="Maximum number of results to return (1-100)"),
    filters: dict[str, str] = Field(
        default_factory=dict, description="Additional filters (e.g., {'is-official': 'true'}"
    ),
) -> dict[str, Any]:
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
        >>> await search_images("nginx", limit=3, filters={"is-official": "true")
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
        # Use shared client
        client = docker_client

        # Validate limit
        limit = max(1, min(100, limit))  # Ensure limit is between 1 and 100

        # Search for images
        results = client.images.search(term=term, limit=limit, filters=filters)

        # Process results
        result_list = []

        for item in results:
            result_list.append(
                {
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "is_official": item.get("is_official", False),
                    "is_automated": item.get("is_automated", False),
                    "star_count": item.get("star_count", 0),
                    "pull_count": item.get("pull_count", 0),
                }
            )

        return {"status": "success", "results": result_list, "count": len(result_list)}

    except APIError as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg, "term": term}

    except DockerException as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}

    except Exception as e:
        error_msg = f"Unexpected error searching images: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg, "term": term}


@mcp.tool()
@check_docker_available
async def image_compare(
    image_a: str = Field(..., description="First image ID or name:tag"),
    image_b: str = Field(..., description="Second image ID or name:tag"),
) -> dict[str, Any]:
    """Compare two Docker images and show their differences.

    Diffs layers, environment variables, entrypoint, default command, exposed ports,
    labels, working directory, and user. Useful before replacing a base image or
    debugging why a newer build behaves differently.

    ## Return Format
    {"success": bool, "image_a": {...}, "image_b": {...}, "differences": {"layers": {...}, "env": {...}, "entrypoint": str|None, "cmd": str|None, "ports": {...}, "labels": {...}, "workdir": str|None, "user": str|None}}

    ## Examples
    image_compare(image_a="nginx:1.25", image_b="nginx:1.26")
    image_compare(image_a="sha256:abc123", image_b="myapp:latest")
    """
    try:
        client = docker_client
        img_a = client.images.get(image_a)
        img_b = client.images.get(image_b)
        a_attrs = img_a.attrs
        b_attrs = img_b.attrs

        def _layers(attrs: dict) -> list[str]:
            return [
                layer.get("createdBy", layer.get("CreatedBy", ""))
                for layer in attrs.get("RootFS", {}).get("Layers", attrs.get("rootfs", {}).get("diff_ids", []))
            ]

        def _env_map(attrs: dict) -> dict[str, str]:
            env = {}
            for e in (attrs.get("Config", {}) if "Config" in attrs else attrs.get("config", {})).get("Env", []):
                if "=" in e:
                    k, v = e.split("=", 1)
                    env[k] = v
            return env

        def _config_get(attrs: dict, key: str):
            return (attrs.get("Config", {}) if "Config" in attrs else attrs.get("config", {})).get(key)

        a_layers = _layers(a_attrs)
        b_layers = _layers(b_attrs)
        a_env = _env_map(a_attrs)
        b_env = _env_map(b_attrs)

        shared_layers = sum(1 for layer in a_layers if layer in b_layers)
        diff = {
            "layers": {
                "image_a_count": len(a_layers),
                "image_b_count": len(b_layers),
                "shared": shared_layers,
                "added": [layer for layer in b_layers if layer not in a_layers][:10],
                "removed": [layer for layer in a_layers if layer not in b_layers][:10],
            },
            "env": {
                "shared": {k: v for k, v in a_env.items() if k in b_env and b_env[k] == v},
                "added": {k: b_env[k] for k in b_env if k not in a_env},
                "removed": {k: a_env[k] for k in a_env if k not in b_env},
                "changed": {
                    k: {"from": a_env[k], "to": b_env[k]} for k in a_env if k in b_env and a_env[k] != b_env[k]
                },
            },
            "entrypoint": {
                "image_a": _config_get(a_attrs, "Entrypoint"),
                "image_b": _config_get(b_attrs, "Entrypoint"),
            },
            "cmd": {"image_a": _config_get(a_attrs, "Cmd"), "image_b": _config_get(b_attrs, "Cmd")},
            "ports": {
                "image_a": list((_config_get(a_attrs, "ExposedPorts") or {}).keys()),
                "image_b": list((_config_get(b_attrs, "ExposedPorts") or {}).keys()),
            },
            "labels": {"image_a": _config_get(a_attrs, "Labels"), "image_b": _config_get(b_attrs, "Labels")},
            "workdir": {"image_a": _config_get(a_attrs, "WorkingDir"), "image_b": _config_get(b_attrs, "WorkingDir")},
            "user": {"image_a": _config_get(a_attrs, "User"), "image_b": _config_get(b_attrs, "User")},
        }

        return {
            "success": True,
            "image_a": {"id": img_a.id, "tags": img_a.tags, "size": a_attrs.get("Size", 0)},
            "image_b": {"id": img_b.id, "tags": img_b.tags, "size": b_attrs.get("Size", 0)},
            "differences": diff,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool
@check_docker_available
async def prune_images(
    filters: dict[str, str] = Field(
        default_factory=dict, description="Filters to process on the prune (e.g., {'dangling': ['true']}"
    ),
    dry_run: bool = Field(default=False, description="If true, only show what would be deleted"),
) -> dict[str, Any]:
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
            client = docker_client
            dangling_images = client.images.list(filters={"dangling": True})

            # Calculate total size
            total_size = sum(img.attrs["Size"] for img in dangling_images)

            return {
                "status": "success",
                "dry_run": True,
                "images_that_would_be_deleted": [img.id for img in dangling_images],
                "space_that_would_be_reclaimed": total_size,
                "count": len(dangling_images),
                "message": f"Would remove {len(dangling_images)} images ({total_size / 1024 / 1024:.1f} MB)",
            }

        # Use shared client
        client = docker_client

        # Prune images
        result = client.images.prune(filters=filters)

        # Process the result
        images_deleted = result.get("ImagesDeleted", [])
        space_reclaimed = result.get("SpaceReclaimed", 0)

        return {
            "status": "success",
            "images_deleted": images_deleted,
            "space_reclaimed": space_reclaimed,
            "count": len(images_deleted),
            "message": f"Pruned {len(images_deleted)} images ({space_reclaimed / 1024 / 1024:.1f} MB)",
        }

    except APIError as e:
        error_msg = f"Docker API error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    except DockerException as e:
        error_msg = f"Docker error: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}

    except Exception as e:
        error_msg = f"Unexpected error pruning images: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}
