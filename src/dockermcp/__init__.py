"""
DockerMCP - FastMCP 2.12 Server for Docker Operations

This package implements a FastMCP 2.12 compatible server with STDIO connection
for managing Docker containers, images, networks, and volumes.

Key Features:
- FastMCP 2.12 protocol implementation
- STDIO-based client communication
- Comprehensive Docker management
- Asynchronous I/O operations

Package Structure:
    - api/       # MCP protocol endpoints
    - core/      # Core Docker operations
    - models/    # Data models and schemas
    - tools/     # MCP tool implementations
    - utils/     # Utility functions
"""

__version__ = "2.12.0"

import os
import logging
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

from typing import Dict, Any, Optional

# Configure package-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)

# Import core components after logging is configured
import docker
from fastmcp import FastMCP
from .core.containers import ContainerManager
from .core.images import ImageManager
from .core.networks import NetworkManager
from .core.volumes import VolumeManager
from .core.system import SystemManager

# Initialize the MCP server with built-in state management
mcp = FastMCP(
    name="docker-mcp",
    version=__version__
)

# Initialize Docker client
docker_client = docker.from_env()

# Initialize managers with Docker client
container_mgr = ContainerManager(docker_client)
image_mgr = ImageManager(docker_client)
network_mgr = NetworkManager(docker_client)
volume_mgr = VolumeManager(docker_client)
system_mgr = SystemManager(docker_client)

# Register core tools
def register_tools():
    """Register all MCP tools with the server."""
    # Import tools here to avoid circular imports
    from .tools import containers, images, networks, volumes, system
    
    # Register tool modules
    mcp.register_tool(containers)
    mcp.register_tool(images)
    mcp.register_tool(networks)
    mcp.register_tool(volumes)
    mcp.register_tool(system)

# Initialize tools on import
register_tools()

# Export public API
__all__ = [
    # Core components
    'mcp',
    'container_mgr',
    'image_mgr',
    'network_mgr',
    'volume_mgr',
    'system_mgr',
    
    # Manager classes
    'ContainerManager',
    'ImageManager',
    'NetworkManager',
    'VolumeManager',
    'SystemManager',
    
    # Version
    '__version__',
    
    # Functions
    'register_tools'
]

logger = logging.getLogger(__name__)
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import server components
from .server import main  # noqa: F401

__all__ = ["__version__", "main"]
