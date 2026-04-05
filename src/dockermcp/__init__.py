"""
DockerMCP - FastMCP 3.2+ Server for Docker Operations

This package implements a FastMCP 3.2+ compatible server with STDIO connection
for managing Docker containers, images, networks, and volumes.
"""

__version__ = "3.2.0"

import asyncio
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, cast

# Add the src directory to the Python path
src_dir = str(Path(__file__).parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure logging before importing other modules
from .logging_config import configure_logging, logger

# Set up logging with minimal output by default
configure_logging(level=os.getenv("LOG_LEVEL", "WARNING"))

# Silence noisy loggers
for logger_name in ['fastmcp', 'mcp', 'uvicorn', 'httpx', 'httpcore', 'h11', 'asyncio']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Import core components after logging is configured
import docker

from .core.containers import ContainerManager
from .core.images import ImageManager
from .core.networks import NetworkManager
from .core.system import SystemManager
from .core.volumes import VolumeManager
from .mcp_instance import get_mcp

# Get the shared FastMCP instance
mcp = get_mcp()

# GRACEFUL DOCKER CONNECTION HANDLING
docker_client: docker.DockerClient | None = None
docker_available: bool = False
docker_error: str | None = None

# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])

# Decorator for Docker availability check
def check_docker_available[F: Callable[..., Any]](func: F) -> F:
    """Decorator to check Docker availability before tool execution."""
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not docker_available:
            return {
                "status": "error",
                "message": f"❌ Docker daemon not available: {docker_error}",
                "troubleshooting": [
                    "Start Docker Desktop",
                    "Run 'docker version' to test",
                    "Use docker_status tool for diagnostics"
                ]
            }
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except docker.errors.DockerException as e:
            return {
                "status": "error",
                "message": f"❌ Docker operation failed: {str(e)}",
                "error_type": type(e).__name__
            }
    return cast(F, wrapper)

def initialize_docker_connection() -> bool:
    """Initialize Docker connection with graceful error handling."""
    global docker_client, docker_available, docker_error

    try:
        logger.info("Attempting to connect to Docker daemon...")
        docker_client = docker.from_env()
        docker_client.ping()

        docker_available = True
        docker_error = None
        logger.info("Successfully connected to Docker daemon")
        return True

    except docker.errors.DockerException as e:
        docker_client = None
        docker_available = False
        docker_error = str(e)
        logger.warning(f"Docker not available: {docker_error}")
        return False

    except Exception as e:
        docker_client = None
        docker_available = False
        docker_error = f"Unexpected error: {str(e)}"
        logger.error(f"Docker connection error: {docker_error}")
        return False

def check_docker_service_windows() -> str:
    """Check Docker service status on Windows."""
    try:
        result = subprocess.run(
            ['sc', 'query', 'Docker Desktop Service'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if "RUNNING" in result.stdout:
            return "running"
        elif "STOPPED" in result.stdout:
            return "stopped"
        return "unknown"
    except Exception as e:
        logger.warning(f"Failed to check Docker service status: {e}")
        return "check_failed"

def get_docker_status() -> dict[str, Any]:
    """Get comprehensive Docker connection status."""
    status = {
        "docker_available": docker_available,
        "error": docker_error if not docker_available else None,
        "version": None,
        "api_version": None,
        "connection_type": "named_pipes" if sys.platform == "win32" else "socket",
        "platform": sys.platform,
        "service_status": None
    }

    if docker_available and docker_client:
        try:
            info = docker_client.info()
            version_info = docker_client.version()

            status.update({
                "version": version_info.get("Version"),
                "api_version": version_info.get("ApiVersion"),
                "platform": info.get("OperatingSystem"),
                "connection_type": "named_pipes" if os.name == 'nt' else "unix_socket",
                "server_version": info.get("ServerVersion"),
                "containers_running": info.get("ContainersRunning", 0),
                "containers_total": info.get("Containers", 0),
                "images_count": info.get("Images", 0)
            })
        except Exception as e:
            status["error"] = f"Error getting Docker info: {str(e)}"

    return status

def retry_docker_connection() -> bool:
    """Attempt to reconnect to Docker daemon."""
    logger.info("Attempting to reconnect to Docker daemon...")
    return initialize_docker_connection()

# Initialize Docker connection on import (gracefully)
initialize_docker_connection()

# Initialize managers with Docker client (or None if unavailable)
container_mgr = ContainerManager(docker_client) if docker_available else None
image_mgr = ImageManager(docker_client) if docker_available else None
network_mgr = NetworkManager(docker_client) if docker_available else None
volume_mgr = VolumeManager(docker_client) if docker_available else None
system_mgr = SystemManager(docker_client) if docker_available else None

def register_tools():
    """Import all tool modules to register them with the FastMCP instance."""
    # Import tools here to ensure they're registered via @mcp.tool decorators
    from .tools import containers, images, networks, system, volumes
    from .tools.desktop import desktop_recovery, desktop_status, desktop_update
    from .tools.docker_reconnect import register_tool as register_reconnect_tool
    from .tools.docker_status import register_tool as register_status_tool
    from .tools.gpu import gpu_management

    # These imports register tools via decorators; we assign to _ to satisfy linters
    _ = [
        containers, images, networks, volumes, system,
        desktop_status, desktop_recovery, desktop_update,
        gpu_management,
        register_status_tool(), register_reconnect_tool()
    ]

# Initialize tools on import
register_tools()

# Export public API
__all__ = [
    'mcp',
    'container_mgr',
    'image_mgr',
    'network_mgr',
    'volume_mgr',
    'system_mgr',
    'ContainerManager',
    'ImageManager',
    'NetworkManager',
    'VolumeManager',
    'SystemManager',
    'docker_client',
    'docker_available',
    'initialize_docker_connection',
    'retry_docker_connection',
    'get_docker_status',
    '__version__',
    'register_tools'
]
