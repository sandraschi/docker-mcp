"""Docker daemon connection state (import-safe; no FastMCP)."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import docker

from .core.containers import ContainerManager
from .core.images import ImageManager
from .core.networks import NetworkManager
from .core.system import SystemManager
from .core.volumes import VolumeManager
from .logging_config import logger

docker_client: docker.DockerClient | None = None
docker_available: bool = False
docker_error: str | None = None

F = TypeVar("F", bound=Callable[..., Any])


def check_docker_available[F: Callable[..., Any]](func: F) -> F:
    """Decorator to check Docker availability before tool execution."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not docker_available:
            return {
                "status": "error",
                "message": f"Docker daemon not available: {docker_error}",
                "troubleshooting": [
                    "Start Docker Desktop",
                    "Run 'docker version' to test",
                    "Use docker_status tool for diagnostics",
                ],
            }
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except docker.errors.DockerException as e:
            return {
                "status": "error",
                "message": f"Docker operation failed: {e!s}",
                "error_type": type(e).__name__,
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
        docker_error = f"Unexpected error: {e!s}"
        logger.error(f"Docker connection error: {docker_error}")
        return False


def check_docker_service_windows() -> str:
    """Check Docker service status on Windows."""
    try:
        result = subprocess.run(
            ["sc", "query", "Docker Desktop Service"],  # noqa: S607
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if "RUNNING" in result.stdout:
            return "running"
        if "STOPPED" in result.stdout:
            return "stopped"
        return "unknown"
    except Exception as e:
        logger.warning(f"Failed to check Docker service status: {e}")
        return "check_failed"


def get_docker_status() -> dict[str, Any]:
    """Get comprehensive Docker connection status."""
    status: dict[str, Any] = {
        "docker_available": docker_available,
        "error": docker_error if not docker_available else None,
        "version": None,
        "api_version": None,
        "connection_type": "named_pipes" if sys.platform == "win32" else "socket",
        "platform": sys.platform,
        "service_status": None,
    }

    if docker_available and docker_client:
        try:
            info = docker_client.info()
            version_info = docker_client.version()
            status.update(
                {
                    "version": version_info.get("Version"),
                    "api_version": version_info.get("ApiVersion"),
                    "platform": info.get("OperatingSystem"),
                    "connection_type": "named_pipes" if os.name == "nt" else "unix_socket",
                    "server_version": info.get("ServerVersion"),
                    "containers_running": info.get("ContainersRunning", 0),
                    "containers_total": info.get("Containers", 0),
                    "images_count": info.get("Images", 0),
                }
            )
        except Exception as e:
            status["error"] = f"Error getting Docker info: {e!s}"

    return status


def retry_docker_connection() -> bool:
    """Attempt to reconnect to Docker daemon."""
    logger.info("Attempting to reconnect to Docker daemon...")
    return initialize_docker_connection()


initialize_docker_connection()

container_mgr = ContainerManager(docker_client) if docker_available else None
image_mgr = ImageManager(docker_client) if docker_available else None
network_mgr = NetworkManager(docker_client) if docker_available else None
volume_mgr = VolumeManager(docker_client) if docker_available else None
system_mgr = SystemManager(docker_client) if docker_available else None
