"""
Image management tools for Docker MCP.

This module provides FastMCP 2.10.1 compatible tools for managing Docker images.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from fastmcp.tools import Tool

# Configure logger
logger = logging.getLogger(__name__)
from dockermcp.core.images import ImageManager
from dockermcp.tools.images.image_models import (
    ImageInfo, ImageResponse, ImageListResponse,
    PullImageRequest, BuildImageRequest, ImageOperationRequest,
    RemoveImageRequest, TagImageRequest, SearchImageRequest,
    PruneImagesRequest, PruneImagesResponse, ImageInspectRequest,
    ImageSaveRequest, ImageLoadRequest, ImageHistoryRequest,
    ImageExportRequest, ImageImportRequest
)

# Initialize image manager
import docker
image_mgr = ImageManager(docker_client=docker.from_env())

@Tool(
    name="list_images",
    description="List all Docker images on the host system",
    parameters={
        "type": "object",
        "properties": {
            "all": {
                "type": "boolean",
                "default": True,
                "description": "Show all images (default: True)"
            },
            "filters": {
                "type": "object",
                "default": {},
                "description": "Filter images by criteria"
            }
        }
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "images": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "size": {"type": "integer"},
                        "created": {"type": "string", "format": "date-time"},
                        "virtual_size": {"type": "integer"},
                        "used": {"type": "boolean"}
                    }
                }
            },
            "total_size": {"type": "integer"},
            "total": {"type": "integer"}
        },
        "required": ["success", "message", "images", "total_size", "total"]
    },
    examples=[
        {
            "input": {"all": True, "filters": {}},
            "output": {
                "success": True,
                "message": "Images listed successfully",
                "images": [
                    {
                        "id": "sha256:abc123",
                        "tags": ["nginx:latest"],
                        "size": 1337000000,
                        "created": "2023-01-01T00:00:00Z",
                        "virtual_size": 1337000000,
                        "used": True
                    }
                ],
                "total_size": 1337000000,
                "total": 1
            }
        }
    ]
)
async def list_images(
    all: bool = True,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """List all Docker images on the host system with detailed information.
    
    Args:
        all: Show all images (default: True)
        filters: Filter images by criteria (default: None)
        
    Returns:
        Dictionary containing the list of images and metadata
    """
    logger.info(f"Listing images with filters: {filters}")
    try:
        filters = filters or {}
        # Get raw images data
        images_data = await image_mgr.list_images(all=all, filters=filters)
        
        # Convert to ImageInfo objects
        images = []
        for img_data in images_data:
            try:
                # Ensure required fields exist
                if not isinstance(img_data, dict):
                    img_data = vars(img_data) if hasattr(img_data, '__dict__') else dict(img_data)
                
                # Handle potential datetime objects
                if 'Created' in img_data and hasattr(img_data['Created'], 'isoformat'):
                    img_data['Created'] = img_data['Created'].isoformat()
                
                # Convert to ImageInfo and back to dict to ensure proper serialization
                image_info = ImageInfo(**img_data)
                images.append(image_info.model_dump())
                
            except Exception as img_error:
                logger.warning(f"Failed to process image data: {str(img_error)}", exc_info=True)
                # Include problematic image data in the response with error information
                images.append({
                    "error": f"Failed to process image: {str(img_error)}",
                    "raw_data": str(img_data)[:500]  # Include first 500 chars of raw data
                })
        
        # Calculate total size
        total_size = sum(img.get('Size', 0) for img in images if isinstance(img, dict) and 'Size' in img)
        
        # Create response
        response = {
            "success": True,
            "message": f"Successfully listed {len(images)} images",
            "images": images,
            "total_size": total_size
        }
        
        logger.info(f"Successfully listed {len(images)} images")
        return response
        
    except Exception as e:
        error_msg = f"Failed to list images: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "images": [],
            "total_size": 0,
            "error": str(e)
        }

@Tool(
    name="pull_image",
    description="Pull a Docker image from a registry",
    parameters={
        "type": "object",
        "properties": {
            "repository": {"type": "string", "description": "Name of the image to pull"},
            "tag": {"type": "string", "default": "latest", "description": "Tag of the image to pull"},
            "auth_config": {"type": "object", "default": {}, "description": "Authentication credentials"},
            "platform": {"type": "string", "default": None, "description": "Platform in the format 'os/arch'"}
        },
        "required": ["repository"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "image": {"type": "object"}
        },
        "required": ["success", "message"]
    },
    examples=[
        {
            "input": {
                "repository": "nginx",
                "tag": "latest"
            },
            "output": {
                "success": True,
                "message": "Image 'nginx:latest' pulled successfully",
                "image": {
                    "Id": "sha256:...",
                    "RepoTags": ["nginx:latest"],
                    "Size": 1337
                }
            }
        }
    ]
)
async def pull_image(
    request: PullImageRequest
) -> Dict[str, Any]:
    """Pull a Docker image from a registry."""
    logger.info(f"Pulling image: {request.repository}:{request.tag}")
    try:
        logger.debug(f"Pull request details: {request.model_dump()}")
        image = await image_mgr.pull_image(
            repository=request.repository,
            tag=request.tag,
            auth_config=request.auth_config,
            platform=request.platform
        )
        
        response = {
            "success": True,
            "message": f"Image '{request.repository}:{request.tag}' pulled successfully",
            "image": image
        }
        logger.info(f"Successfully pulled image: {request.repository}:{request.tag}")
        return response
        
    except Exception as e:
        error_msg = f"Failed to pull image {request.repository}:{request.tag}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e)
        }

@Tool(
    name="build_image",
    description="Build a Docker image from a Dockerfile",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the directory containing the build context"},
            "tag": {"type": "string", "description": "Name and optionally a tag in 'name:tag' format"},
            "dockerfile": {"type": "string", "default": None, "description": "Path to the Dockerfile within the build context"},
            "buildargs": {"type": "object", "default": {}, "description": "Build-time variables"},
            "labels": {"type": "object", "default": {}, "description": "Set metadata for the image"},
            "nocache": {"type": "boolean", "default": False, "description": "Do not use cache when building the image"},
            "rm": {"type": "boolean", "default": True, "description": "Remove intermediate containers after a successful build"},
            "pull": {"type": "boolean", "default": False, "description": "Attempt to pull a newer version of the image"}
        },
        "required": ["path", "tag"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "image": {"type": "object"}
        },
        "required": ["success", "message"]
    },
    examples=[
        {
            "input": {
                "path": "/path/to/build/context",
                "tag": "myapp:latest"
            },
            "output": {
                "success": True,
                "message": "Image 'myapp:latest' built successfully",
                "image": {
                    "Id": "sha256:...",
                    "RepoTags": ["myapp:latest"],
                    "Size": 123456789
                }
            }
        }
    ]
)
async def build_image(
    request: BuildImageRequest
) -> Dict[str, Any]:
    """Build a Docker image from a Dockerfile."""
    logger.info(f"Building image with tag: {request.tag}")
    logger.debug(f"Build request details: {request.model_dump()}")
    
    try:
        # Validate build context path exists
        if not os.path.exists(request.path):
            error_msg = f"Build context path does not exist: {request.path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Starting build from path: {request.path}")
        if request.dockerfile:
            logger.debug(f"Using Dockerfile: {request.dockerfile}")
        
        # Build the image
        image = await image_mgr.build_image(
            path=request.path,
            tag=request.tag,
            dockerfile=request.dockerfile,
            buildargs=request.buildargs,
            labels=request.labels,
            nocache=request.nocache,
            rm=request.rm,
            pull=request.pull
        )
        
        # Ensure image data is serializable
        if hasattr(image, 'model_dump'):
            image_data = image.model_dump()
        elif hasattr(image, 'attrs'):
            image_data = dict(image.attrs)
        else:
            image_data = dict(image)
        
        response = {
            "success": True,
            "message": f"Image '{request.tag}' built successfully",
            "image": image_data
        }
        
        logger.info(f"Successfully built image: {request.tag}")
        return response
        
    except Exception as e:
        error_msg = f"Failed to build image '{request.tag}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e)
        }

@Tool(
    name="remove_image",
    description="Remove a Docker image from the host system",
    parameters={
        "type": "object",
        "properties": {
            "image": {"type": "string", "description": "Image ID or name to remove"},
            "force": {"type": "boolean", "default": False, "description": "Force removal of the image"},
            "noprune": {"type": "boolean", "default": False, "description": "Do not delete untagged parents"}
        },
        "required": ["image"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "deleted": {"type": "array", "items": {"type": "string"}},
            "untagged": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["success", "message", "deleted", "untagged"]
    },
    examples=[
        {
            "input": {
                "image": "nginx:latest",
                "force": False
            },
            "output": {
                "success": True,
                "message": "Image 'nginx:latest' removed successfully",
                "deleted": ["sha256:abc123..."],
                "untagged": ["nginx:latest"]
            }
        }
    ]
)
async def remove_image(
    request: RemoveImageRequest
) -> Dict[str, Any]:
    """Remove a Docker image from the host system."""
    logger.info(f"Removing image: {request.image}")
    logger.debug(f"Remove request details: force={request.force}, noprune={request.noprune}")
    
    try:
        logger.debug(f"Initiating removal of image: {request.image}")
        result = await image_mgr.remove_image(
            image=request.image,
            force=request.force,
            noprune=request.noprune
        )
        
        # Ensure we have lists for deleted and untagged
        deleted = list(result.get('Deleted', []))
        untagged = list(result.get('Untagged', []))
        
        # Log the operation details
        logger.info(f"Successfully processed removal of image: {request.image}")
        if deleted:
            logger.debug(f"Deleted layers: {deleted}")
        if untagged:
            logger.debug(f"Untagged references: {untagged}")
        
        response = {
            "success": True,
            "message": f"Image '{request.image}' removed successfully",
            "deleted": deleted,
            "untagged": untagged
        }
        
        return response
        
    except docker.errors.ImageNotFound as e:
        error_msg = f"Image not found: {request.image}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e),
            "deleted": [],
            "untagged": []
        }
    except docker.errors.APIError as e:
        error_msg = f"Docker API error while removing image {request.image}"
        logger.error(f"{error_msg}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e),
            "deleted": [],
            "untagged": []
        }
    except Exception as e:
        error_msg = f"Unexpected error removing image {request.image}"
        logger.error(f"{error_msg}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e),
            "deleted": [],
            "untagged": []
        }

@Tool(
    name="tag_image",
    description="Tag a Docker image with a new name and tag",
    parameters={
        "type": "object",
        "properties": {
            "image": {"type": "string", "description": "Source image name or ID"},
            "repository": {"type": "string", "description": "Repository to tag the image with"},
            "tag": {"type": "string", "default": "latest", "description": "Tag name"},
            "force": {"type": "boolean", "default": False, "description": "Force tagging even if tag already exists"}
        },
        "required": ["image", "repository"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "source_image": {"type": "string"},
            "new_tag": {"type": "string"}
        },
        "required": ["success", "message", "source_image", "new_tag"]
    },
    examples=[
        {
            "input": {
                "image": "nginx:latest",
                "repository": "myregistry/nginx",
                "tag": "v1.0"
            },
            "output": {
                "success": True,
                "message": "Image 'nginx:latest' successfully tagged as 'myregistry/nginx:v1.0'",
                "source_image": "nginx:latest",
                "new_tag": "myregistry/nginx:v1.0"
            }
        }
    ]
)
async def tag_image(
    request: TagImageRequest
) -> Dict[str, Any]:
    """Tag a Docker image with a new name and tag."""
    new_tag = f"{request.repository}:{request.tag}"
    logger.info(f"Tagging image: {request.image} as {new_tag}")
    logger.debug(f"Tag request details: force={request.force}")
    
    try:
        # Validate source image exists
        try:
            await image_mgr.inspect_image(request.image)
        except docker.errors.ImageNotFound:
            error_msg = f"Source image not found: {request.image}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "source_image": request.image,
                "new_tag": new_tag
            }
        
        logger.debug(f"Initiating tag operation from {request.image} to {new_tag}")
        result = await image_mgr.tag_image(
            image=request.image,
            repository=request.repository,
            tag=request.tag,
            force=request.force
        )
        
        # Verify the tag was created
        try:
            # Get the image details to verify the new tag exists
            image_info = await image_mgr.inspect_image(new_tag)
            logger.debug(f"Successfully verified new tag: {new_tag}")
        except Exception as verify_error:
            error_msg = f"Failed to verify new tag {new_tag}: {str(verify_error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg,
                "error": str(verify_error),
                "source_image": request.image,
                "new_tag": new_tag
            }
        
        response = {
            "success": True,
            "message": f"Successfully tagged {request.image} as {new_tag}",
            "source_image": request.image,
            "new_tag": new_tag
        }
        
        logger.info(f"Successfully tagged image as {new_tag}")
        return response
        
    except docker.errors.APIError as e:
        error_msg = f"Docker API error while tagging image: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e),
            "source_image": request.image,
            "new_tag": new_tag
        }
    except Exception as e:
        error_msg = f"Failed to tag image {request.image}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e),
            "source_image": request.image,
            "new_tag": new_tag
        }

@Tool(
    name="search_images",
    description="Search for Docker images in a registry",
    parameters={
        "type": "object",
        "properties": {
            "term": {
                "type": "string",
                "description": "Search term to look for in image names"
            },
            "limit": {
                "type": "integer",
                "default": 25,
                "minimum": 1,
                "maximum": 100,
                "description": "Maximum number of results to return"
            },
            "filters": {
                "type": "object",
                "default": {},
                "description": "Additional filters for the search"
            }
        },
        "required": ["term"]
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "is_official": {"type": "boolean"},
                        "is_automated": {"type": "boolean"},
                        "star_count": {"type": "integer"}
                    }
                }
            },
            "count": {"type": "integer"},
            "search_term": {"type": "string"}
        },
        "required": ["success", "results", "count", "search_term"]
    },
    examples=[
        {
            "input": {
                "term": "nginx",
                "limit": 5
            },
            "output": {
                "success": true,
                "message": "Found 5 results for 'nginx'",
                "results": [
                    {
                        "name": "nginx",
                        "description": "Official build of Nginx.",
                        "is_official": true,
                        "is_automated": false,
                        "star_count": 17500
                    }
                ],
                "count": 5,
                "search_term": "nginx"
            }
        }
    ]
)
async def search_images(
    request: SearchImageRequest
) -> Dict[str, Any]:
    """Search for Docker images in a registry."""
    logger.info(f"Searching for images with term: '{request.term}'")
    logger.debug(f"Search parameters: limit={request.limit}, filters={request.filters}")
    
    try:
        # Validate search term
        if not request.term or not isinstance(request.term, str):
            error_msg = "Search term must be a non-empty string"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "results": [],
                "count": 0,
                "search_term": request.term
            }
        
        # Ensure limit is within bounds
        limit = max(1, min(100, int(request.limit) if request.limit else 25))
        
        logger.debug(f"Initiating image search for: '{request.term}' with limit {limit}")
        
        try:
            results = await image_mgr.search_images(
                term=request.term,
                limit=limit,
                filters=request.filters or {}
            )
        except docker.errors.APIError as api_error:
            error_msg = f"Docker API error while searching images: {str(api_error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg,
                "results": [],
                "count": 0,
                "search_term": request.term,
                "error": str(api_error)
            }
        
        # Process and validate results
        valid_results = []
        for result in results:
            try:
                # Ensure required fields exist
                if not isinstance(result, dict):
                    result = dict(result) if hasattr(result, '__dict__') else {}
                
                # Create a standardized result entry
                valid_result = {
                    'name': str(result.get('name', '')),
                    'description': str(result.get('description', '')),
                    'is_official': bool(result.get('is_official', False)),
                    'is_automated': bool(result.get('is_automated', False)),
                    'star_count': int(result.get('star_count', 0))
                }
                
                # Only include results with a name
                if valid_result['name']:
                    valid_results.append(valid_result)
                
            except Exception as result_error:
                logger.warning(f"Error processing search result: {str(result_error)}")
                continue
        
        result_count = len(valid_results)
        message = f"Found {result_count} result{'' if result_count == 1 else 's'} for '{request.term}'"
        
        response = {
            "success": True,
            "message": message,
            "results": valid_results[:limit],  # Ensure we don't exceed the limit
            "count": min(result_count, limit),
            "search_term": request.term
        }
        
        logger.info(message)
        if result_count > 0:
            logger.debug(f"First result: {valid_results[0]}")
        
        return response
        
    except ValueError as ve:
        error_msg = f"Invalid search parameter: {str(ve)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "results": [],
            "count": 0,
            "search_term": request.term,
            "error": str(ve)
        }
    except Exception as e:
        error_msg = f"Unexpected error searching for images: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "results": [],
            "count": 0,
            "search_term": request.term,
            "error": str(e)
        }

@Tool(
    name="prune_images",
    description="Remove unused Docker images to free up disk space",
    parameters={
        "type": "object",
        "properties": {
            "filters": {
                "type": "object",
                "default": {},
                "description": "Filters to process on the prune list"
            },
            "dangling": {
                "type": "boolean",
                "default": True,
                "description": "When true, delete only unused and untagged images"
            }
        }
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "message": {"type": "string"},
            "images_deleted": {"type": "array", "items": {"type": "string"}},
            "space_reclaimed": {"type": "integer"},
            "details": {"type": "object"}
        },
        "required": ["success", "message", "images_deleted", "space_reclaimed"]
    },
    examples=[
        {
            "input": {
                "dangling": true
            },
            "output": {
                "success": true,
                "message": "Successfully pruned 3 unused images, reclaiming 1.2GB",
                "images_deleted": ["sha256:abc123...", "sha256:def456..."],
                "space_reclaimed": 1288490188,
                "details": {
                    "ImagesDeleted": [
                        {"Untagged": "<image_id_1>"},
                        {"Deleted": "<image_id_2>"}
                    ],
                    "SpaceReclaimed": 1288490188
                }
            }
        }
    ]
)
async def prune_images(
    request: PruneImagesRequest
) -> Dict[str, Any]:
    """
    Remove unused Docker images to free up disk space.
    
    Args:
        request: PruneImagesRequest containing filters and options
        
    Returns:
        Dictionary with operation results including deleted images and space reclaimed
    """
    logger.info("Initiating image pruning operation")
    logger.debug(f"Prune parameters: dangling={request.dangling}, filters={request.filters}")
    
    try:
        # Validate filters if provided
        if request.filters and not isinstance(request.filters, dict):
            error_msg = "Filters must be a dictionary"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "images_deleted": [],
                "space_reclaimed": 0,
                "error": error_msg
            }
        
        # Execute the prune operation
        logger.debug("Executing image prune operation")
        result = await image_mgr.prune_images(
            filters=request.filters or {},
            dangling=request.dangling
        )
        
        # Process the results
        images_deleted = []
        space_reclaimed = int(result.get("SpaceReclaimed", 0))
        
        # Extract deleted image IDs
        for item in result.get("ImagesDeleted", []):
            if isinstance(item, dict):
                # Handle both "Deleted" and "Untagged" entries
                for _, img_id in item.items():
                    if img_id and img_id not in images_deleted:
                        images_deleted.append(img_id)
            elif item and item not in images_deleted:
                images_deleted.append(item)
        
        # Format the response
        deleted_count = len(images_deleted)
        space_mb = space_reclaimed / (1024 * 1024)
        
        if deleted_count == 0:
            message = "No unused images to remove"
        else:
            message = (
                f"Successfully pruned {deleted_count} unused image{'s' if deleted_count != 1 else ''}, "
                f"reclaiming {space_mb:.2f}MB"
            )
        
        response = {
            "success": True,
            "message": message,
            "images_deleted": images_deleted,
            "space_reclaimed": space_reclaimed,
            "details": result
        }
        
        logger.info(f"Prune operation completed: {message}")
        logger.debug(f"Prune details: {result}")
        
        return response
        
    except docker.errors.APIError as api_error:
        error_msg = f"Docker API error during image pruning: {str(api_error)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "images_deleted": [],
            "space_reclaimed": 0,
            "error": str(api_error)
        }
    except ValueError as ve:
        error_msg = f"Invalid parameter: {str(ve)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "images_deleted": [],
            "space_reclaimed": 0,
            "error": str(ve)
        }
    except Exception as e:
        error_msg = f"Unexpected error during image pruning: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "message": error_msg,
            "images_deleted": [],
            "space_reclaimed": 0,
            "error": str(e)
        }

@Tool(
    name="inspect_image",
    description="Return low-level information about an image"
)
async def inspect_image(
    request: ImageInspectRequest
) -> Dict[str, Any]:
    """Return low-level information about an image."""
    try:
        details = await image_mgr.inspect_image(
            image=request.image,
            size=request.size
        )
        return {
            "success": True,
            "image": details,
            "message": "Image details retrieved successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to inspect image: {str(e)}"
        }

@Tool(
    name="save_image",
    description="Save an image to a tar archive"
)
async def save_image(
    request: ImageSaveRequest
) -> Dict[str, Any]:
    """Save an image to a tar archive."""
    try:
        result = await image_mgr.save_image(
            image=request.image,
            output_path=request.output_path,
            format=request.format
        )
        return {
            "success": True,
            "output_path": request.output_path,
            "size": result.get("size", 0),
            "message": f"Image saved to {request.output_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save image: {str(e)}",
            "output_path": request.output_path
        }

@Tool(
    name="load_image",
    description="Load an image from a tar archive"
)
async def load_image(
    request: ImageLoadRequest
) -> Dict[str, Any]:
    """Load an image from a tar archive."""
    try:
        result = await image_mgr.load_image(
            input_path=request.input_path,
            quiet=request.quiet
        )
        return {
            "success": True,
            "image": result.get("image_id"),
            "message": "Image loaded successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to load image: {str(e)}",
            "input_path": request.input_path
        }

@Tool(
    name="image_history",
    description="Get the history of an image"
)
async def image_history(
    request: ImageHistoryRequest
) -> Dict[str, Any]:
    """Get the history of an image."""
    try:
        history = await image_mgr.history(
            image=request.image,
            all_layers=request.all
        )
        return {
            "success": True,
            "history": history,
            "layer_count": len(history)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get image history: {str(e)}"
        }

@Tool(
    name="export_filesystem",
    description="Export a container's filesystem as a tar archive"
)
async def export_filesystem(
    request: ImageExportRequest
) -> Dict[str, Any]:
    """Export a container's filesystem as a tar archive."""
    try:
        result = await image_mgr.export_filesystem(
            container=request.image,
            output_path=request.output_path,
            chunk_size=request.chunk_size
        )
        return {
            "success": True,
            "output_path": request.output_path,
            "size": result.get("size", 0),
            "message": f"Filesystem exported to {request.output_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to export filesystem: {str(e)}",
            "output_path": request.output_path
        }

@Tool(
    name="import_filesystem",
    description="Import the contents from a tarball to create a filesystem image"
)
async def import_filesystem(
    request: ImageImportRequest
) -> Dict[str, Any]:
    """Import the contents from a tarball to create a filesystem image."""
    try:
        result = await image_mgr.import_filesystem(
            source=request.source,
            repository=request.repository,
            tag=request.tag,
            message=request.message,
            changes=request.changes
        )
        return {
            "success": True,
            "image_id": result.get("image_id"),
            "message": "Filesystem imported successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to import filesystem: {str(e)}",
            "source": request.source
        }
