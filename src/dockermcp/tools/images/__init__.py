"""
Docker Image Management Tools for DockerMCP.

This module provides FastMCP 2.12+ compatible tools for managing Docker images.
It includes functionality for pulling, building, tagging, and managing Docker images.
"""

from typing import List
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError

from .image_models import (
    ImageStatus,
    ImageInfo,
    ImageResponse,
    ImageListResponse,
    PullImageRequest,
    BuildImageRequest,
    RemoveImageRequest,
    TagImageRequest,
    SearchImageRequest,
    PruneImagesRequest,
    PruneImagesResponse,
    ImageInspectRequest,
    ImageSaveRequest,
    ImageLoadRequest,
    ImageHistoryRequest,
    ImageExportRequest,
    ImageImportRequest
)

# Import the tool functions directly
from .image_tools import (
    list_images,
    pull_image,
    build_image,
    remove_image,
    tag_image,
    search_images,
    prune_images,
    inspect_image,
    save_image,
    load_image,
    image_history,
    export_filesystem,
    import_filesystem
)

def get_tools() -> List[callable]:
    """
    Get all image management tools for registration with FastMCP 2.12+.
    
    Returns:
        List of @tool-decorated functions for all image management operations
    """
    # Return a list of all @tool-decorated functions
    return [
        list_images,
        pull_image,
        build_image,
        remove_image,
        tag_image,
        search_images,
        prune_images,
        inspect_image,
        save_image,
        load_image,
        image_history,
        export_filesystem,
        import_filesystem
    ]

__all__ = [
    # Models
    'ImageStatus',
    'ImageInfo',
    'ImageResponse',
    'ImageListResponse',
    'PullImageRequest',
    'BuildImageRequest',
    'RemoveImageRequest',
    'TagImageRequest',
    'SearchImageRequest',
    'PruneImagesRequest',
    'PruneImagesResponse',
    'ImageInspectRequest',
    'ImageSaveRequest',
    'ImageLoadRequest',
    'ImageHistoryRequest',
    'ImageExportRequest',
    'ImageImportRequest',
    
    # Tools
    'get_tools',
    'list_images',
    'pull_image',
    'build_image',
    'remove_image',
    'tag_image',
    'search_images',
    'prune_images',
    'inspect_image',
    'save_image',
    'load_image',
    'image_history',
    'export_filesystem',
    'import_filesystem'
]
