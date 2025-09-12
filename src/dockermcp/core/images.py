"""
Image management operations.

This module provides functions for managing Docker images including
listing, pulling, and removing images.
"""
from typing import Dict, List, Optional, Any
import asyncio
import logging
from ..logging_config import ContextLogger

logger = ContextLogger(logging.getLogger(f"dockermcp.core.{__name__}"), {})

# TODO: Move image operations from docker_ops/images.py to here

class ImageManager:
    """Manager for image operations."""
    
    def __init__(self, docker_client):
        """Initialize with a Docker client."""
        self.client = docker_client
    
    async def list_images(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all images with optional filtering by name."""
        try:
            images = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.images.list(name=name) if name else self.client.images.list()
            )
            return [
                {
                    'id': img.id,
                    'tags': img.tags,
                    'created': img.attrs['Created'],
                    'size': img.attrs['Size'],
                    'virtual_size': img.attrs['VirtualSize']
                }
                for img in images
            ]
        except Exception as e:
            logger.error(f"Error listing images: {str(e)}")
            raise

    # Add other image operations here...
