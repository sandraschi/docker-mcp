"""Docker daemon connection state (import-safe; no FastMCP)."""

from __future__ import annotations

import asyncio
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


def _sync_dependent_modules() -> None:
    """Propagate the active docker_client to all dockermcp modules."""
    global container_mgr, image_mgr, network_mgr, volume_mgr, system_mgr
    if docker_available and docker_client:
        container_mgr = ContainerManager(docker_client)
        image_mgr = ImageManager(docker_client)
        network_mgr = NetworkManager(docker_client)
        volume_mgr = VolumeManager(docker_client)
        system_mgr = SystemManager(docker_client)
    else:
        container_mgr = None
        image_mgr = None
        network_mgr = None
        volume_mgr = None
        system_mgr = None

    # Sync imported attributes in sys.modules so consumers get the live client
    for mod_name, mod in list(sys.modules.items()):
        if mod and (mod_name.startswith("dockermcp") or mod_name.startswith("docker_mcp")):
            if hasattr(mod, "docker_client"):
                mod.docker_client = docker_client
            if hasattr(mod, "docker_available"):
                mod.docker_available = docker_available
            if hasattr(mod, "docker_error"):
                mod.docker_error = docker_error
            if hasattr(mod, "container_mgr"):
                mod.container_mgr = container_mgr
            if hasattr(mod, "image_mgr"):
                mod.image_mgr = image_mgr
            if hasattr(mod, "network_mgr"):
                mod.network_mgr = network_mgr
            if hasattr(mod, "volume_mgr"):
                mod.volume_mgr = volume_mgr
            if hasattr(mod, "system_mgr"):
                mod.system_mgr = system_mgr


def check_docker_available[F: Callable[..., Any]](func: F) -> F:
    """Decorator to check Docker availability before tool execution, attempting reconnect if needed."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        global docker_available, docker_error
        if not docker_available:
            # Attempt on-the-fly reconnection in case daemon started after backend
            if not initialize_docker_connection():
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
    """Initialize Docker connection with graceful error handling and module state sync."""
    global docker_client, docker_available, docker_error

    try:
        logger.info("Attempting to connect to Docker daemon...")
        client = None
        # On Windows, try standard from_env first, then explicitly try desktop-linux pipe if needed
        candidate_urls = [None]
        if sys.platform == "win32":
            candidate_urls.extend(["npipe:////./pipe/dockerDesktopLinuxEngine", "npipe:////./pipe/docker_engine"])

        last_exc = None
        for base_url in candidate_urls:
            try:
                c = docker.DockerClient(base_url=base_url) if base_url else docker.from_env()
                c.ping()
                client = c
                break
            except Exception as exc:
                last_exc = exc
        if not client:
            raise last_exc or docker.errors.DockerException("Unable to connect to any Docker pipe")

        docker_client = client
        docker_available = True
        docker_error = None
        _sync_dependent_modules()
        logger.info("Successfully connected to Docker daemon")
        return True
    except docker.errors.DockerException as e:
        docker_client = None
        docker_available = False
        docker_error = str(e)
        _sync_dependent_modules()
        logger.warning(f"Docker not available: {docker_error}")
        return False
    except Exception as e:
        docker_client = None
        docker_available = False
        docker_error = f"Unexpected error: {e!s}"
        _sync_dependent_modules()
        logger.error(f"Docker connection error: {docker_error}")
        return False


def triple_kill_docker() -> dict:
    """Triple Kill: kill hung Docker processes, restart daemon.

    See DOCKER_WINDOWS_RESILIENCE.md Level 3 for the standard.
    First checks if the daemon is already responsive.
    """
    global docker_client, docker_available, docker_error

    # Quick pre-check: if daemon is already reachable, don't kill anything
    if initialize_docker_connection():
        return {"success": True, "message": "Docker daemon is already reachable and healthy", "killed": []}

    targets = ["Docker Desktop", "com.docker.backend", "com.docker.build", "vpnkit"]
    killed = []
    for name in targets:
        try:
            r = subprocess.run(
                ["taskkill", "/F", "/IM", f"{name}.exe", "/T"],
                capture_output=True,
                timeout=10,
            )
            if r.returncode == 0:
                killed.append(name)
        except Exception:
            pass
    import time

    time.sleep(5)
    # Restart Docker Desktop
    dd = os.path.expandvars(r"%ProgramFiles%\Docker\Docker\Docker Desktop.exe")
    alt = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
    path = dd if os.path.exists(dd) else alt if os.path.exists(alt) else None
    if path:
        subprocess.Popen([path], cwd=os.path.dirname(path))
        # Wait for daemon to become available
        for _i in range(45):
            time.sleep(2)
            if initialize_docker_connection():
                logger.info("Docker recovered after triple kill")
                return {"success": True, "message": "Docker recovered", "killed": killed}
        docker_error = "Docker did not recover after triple kill"
    else:
        docker_error = "Docker Desktop not found at expected path"
    docker_available = False
    _sync_dependent_modules()
    return {"success": False, "message": docker_error, "killed": killed}


def check_docker_service_windows() -> str:
    """Check Docker service status on Windows."""
    try:
        result = subprocess.run(
            ["sc", "query", "Docker Desktop Service"],
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
    global docker_available, docker_client, docker_error
    if not docker_available:
        initialize_docker_connection()

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
