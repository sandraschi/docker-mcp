"""
Docker Image Management Tools for DockerMCP.

This module provides FastMCP 2.12.0 compatible tools for managing Docker images.
It includes functionality for pulling, building, tagging, and managing Docker images.
"""

import logging
from typing import List, Type

# Import FastMCP components
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolException

# Configure logger
logger = logging.getLogger(__name__)

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

def get_tools() -> List[Tool]:
    """
    Get all image management tools for registration with FastMCP 2.12+.
    
    This function returns Tool instances that have been properly decorated with @Tool
    in the image_tools.py module. Each tool is already an instance of the Tool class.
    
    Returns:
        List[Tool]: List of Tool instances for all image management operations
        
    Raises:
        RuntimeError: If any tool fails to be properly imported or initialized
    """
    try:
        # Import tools from image_tools to ensure they're properly initialized
        from . import image_tools
        
        # Get tools using the get_tools function from image_tools
        tools = image_tools.get_tools()
        
        # Verify all items are Tool instances
        for tool in tools:
            if not isinstance(tool, Tool):
                raise TypeError(
                    f"Expected Tool instance, got {type(tool).__name__} for {getattr(tool, '__name__', 'unnamed')}"
                )
        
        logger.info(f"Successfully loaded {len(tools)} image management tools")
        return tools
        
    except Exception as e:
        error_msg = f"Failed to load image management tools: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

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
