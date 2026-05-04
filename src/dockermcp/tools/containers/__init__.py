"""
Container tools package for Docker MCP.

This package provides comprehensive container management tools following
FastMCP 2.12+ standards.
"""

# Import container tools to register them with FastMCP
from . import container_exec as _container_exec  # noqa: F401
from . import container_files as _container_files  # noqa: F401
from . import container_images as _container_images  # noqa: F401
from . import container_inspect as _container_inspect  # noqa: F401
from . import container_lifecycle as _container_lifecycle  # noqa: F401
from . import container_logs as _container_logs  # noqa: F401
from . import container_management as _container_management  # noqa: F401
from . import container_network as _container_network  # noqa: F401
from . import container_resources as _container_resources  # noqa: F401
from . import container_stats as _container_stats  # noqa: F401
from . import container_volumes as _container_volumes  # noqa: F401
from . import list_containers as _list_containers  # noqa: F401
from .container_exec import execute_in_container  # noqa: F401
from .container_files import list_container_directory, read_container_file, write_container_file  # noqa: F401
from .container_images import build_image, list_images, pull_image, remove_image  # noqa: F401
from .container_inspect import (  # noqa: F401
    BaseResponse,
    ContainerInspectRequest,
    ContainerInspectResponse,
    inspect_container,
)
from .container_lifecycle import ContainerAction, manage_container_lifecycle  # noqa: F401
from .container_logs import get_container_logs
from .container_management import ContainerRequest, manage_container  # noqa: F401
from .container_network import list_networks  # noqa: F401
from .container_resources import get_container_resources, reset_container_resources  # noqa: F401
from .container_stats import get_container_stats
from .container_volumes import create_volume, inspect_volume, list_volumes, prune_volumes, remove_volume  # noqa: F401
from .list_containers import ContainerInfo, list_containers  # noqa: F401

__all__ = [
    # Image operations
    "commit_container_to_image",
    # Network operations
    "connect_container_to_network",
    "copy_from_container",
    # File operations
    "copy_to_container",
    "create_archive_in_container",
    # Container lifecycle operations
    "create_container",
    "disconnect_container_from_network",
    "exec_command",
    # Container execution
    "exec_in_container",
    "export_container",
    "extract_archive_from_container",
    "follow_container_logs",
    "get_container_config",
    # Container logs and monitoring
    "get_container_logs",
    "get_container_resource_usage",
    "get_container_stats",
    "import_container",
    # Container inspection
    "inspect_container",
    # Container listing
    "list_containers",
    "list_running_containers",
    "list_stopped_containers",
    "monitor_container_performance",
    # Volume operations
    "mount_volume_to_container",
    "pause_container",
    "remove_container",
    # Container management
    "rename_container",
    "restart_container",
    # Resource management
    "set_container_resources",
    "start_container",
    "stop_container",
    "unmount_volume_from_container",
    "unpause_container",
    "update_container"
]
