"""
Container tools package for Docker MCP.

This package provides comprehensive container management tools following
FastMCP 2.12+ standards.
"""

# Import container tools to register them with FastMCP
from .container_exec import *
from .container_files import *
from .container_images import *
from .container_inspect import *
from .container_lifecycle import *
from .container_logs import *
from .container_management import *
from .container_network import *
from .container_resources import *
from .container_stats import *
from .container_volumes import *
from .list_containers import *
from .models import (
    ContainerCreateRequest,
    ContainerExecResponse,
    ContainerInspectResponse,
    ContainerListResponse,
    ContainerLogsResponse,
    ContainerOperationResponse,
    ContainerStatsResponse,
    ContainerSummary,
)

__all__ = [
    # Container lifecycle operations
    "create_container",
    "start_container",
    "stop_container",
    "restart_container",
    "remove_container",
    "pause_container",
    "unpause_container",

    # Container management
    "rename_container",
    "update_container",

    # Container inspection
    "inspect_container",
    "get_container_config",

    # Container logs and monitoring
    "get_container_logs",
    "follow_container_logs",
    "get_container_stats",
    "monitor_container_performance",

    # Container execution
    "exec_in_container",
    "exec_command",

    # File operations
    "copy_to_container",
    "copy_from_container",
    "create_archive_in_container",
    "extract_archive_from_container",

    # Network operations
    "connect_container_to_network",
    "disconnect_container_from_network",

    # Volume operations
    "mount_volume_to_container",
    "unmount_volume_from_container",

    # Resource management
    "set_container_resources",
    "get_container_resource_usage",

    # Image operations
    "commit_container_to_image",
    "export_container",
    "import_container",

    # Container listing
    "list_containers",
    "list_running_containers",
    "list_stopped_containers"
]
