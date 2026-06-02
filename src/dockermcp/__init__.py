"""
DockerMCP - FastMCP 3.3 server for Docker operations.
"""

__version__ = "3.3.0"

from .docker_context import (
    ContainerManager,
    ImageManager,
    NetworkManager,
    SystemManager,
    VolumeManager,
    check_docker_available,
    container_mgr,
    docker_available,
    docker_client,
    docker_error,
    get_docker_status,
    image_mgr,
    initialize_docker_connection,
    network_mgr,
    retry_docker_connection,
    system_mgr,
    volume_mgr,
)


def __getattr__(name: str):
    if name == "mcp":
        from .mcp_instance import get_mcp

        return get_mcp()
    if name == "get_mcp":
        from .mcp_instance import get_mcp

        return get_mcp
    if name == "register_tools":
        from .tool_registration import register_all_tools

        return register_all_tools
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ContainerManager",
    "ImageManager",
    "NetworkManager",
    "SystemManager",
    "VolumeManager",
    "__version__",
    "check_docker_available",
    "container_mgr",
    "docker_available",
    "docker_client",
    "get_docker_status",
    "image_mgr",
    "initialize_docker_connection",
    "mcp",
    "network_mgr",
    "register_tools",
    "retry_docker_connection",
    "system_mgr",
    "volume_mgr",
]
