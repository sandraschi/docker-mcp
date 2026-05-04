"""
Docker MCP Tools - FastMCP 2.12.0+ compatible tools

This package contains all the FastMCP 2.12.0+ compatible tools for Docker operations.
"""
import importlib
import logging
import pkgutil
import sys
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

# Add the src directory to the Python path
src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure logging first to ensure all modules use the same config
from dockermcp.logging_config import configure_logging, logger  # noqa: E402

configure_logging(level="INFO")

# Silence noisy loggers
for logger_name in ['fastmcp', 'mcp', 'uvicorn', 'httpx', 'httpcore', 'h11', 'asyncio']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Type variable for tool response models
T = TypeVar('T')

class ToolResponse[T](BaseModel):
    """Standard response model for all tools."""
    success: bool
    message: str
    data: T | None = None
    error: str | None = None

    @classmethod
    def from_success(cls, message: str, data: T | None = None) -> 'ToolResponse[T]':
        """Create a success response."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def from_error(cls, message: str, error: Exception | None = None) -> 'ToolResponse[Any]':
        """Create an error response."""
        error_msg = str(error) if error else message
        return cls(success=False, message=message, error=error_msg)

def discover_tools() -> set[str]:
    """
    Automatically discover all tools from submodules.

    Returns:
        Set of tool names that were discovered and registered
    """
    tools_dir = Path(__file__).parent
    discovered_tools = set()

    # Skip __pycache__, __init__.py, and files starting with _
    modules = [
        name for _, name, is_pkg in pkgutil.iter_modules([str(tools_dir)])
        if not name.startswith('_') and name != 'models' and not name.startswith('test_')
    ]

    for name in modules:
        try:
            # Import the module to register the tools
            module = importlib.import_module(f'.{name}', package=__name__)
            logger.debug(f'Imported tools module: {name}')

            # Get all tools from the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                # Check if it's a FastMCP tool (decorated functions have __wrapped__ or are registered)
                if hasattr(attr, '__wrapped__') or (callable(attr) and hasattr(attr, '_mcp_tool')):
                    discovered_tools.add(attr_name)
                    logger.info(f'Discovered tool: {attr_name} from {name}')
        except ImportError as e:
            logger.warning(f'Failed to import module {name}: {e!s}')
            continue

    return discovered_tools

def get_tools() -> list[dict[str, Any]]:
    """Get metadata for all registered tools."""
    # In FastMCP 2.12+, tools are automatically registered via the @tool decorator
    # This function is kept for backward compatibility
    return []

# Discover and register tools when the package is imported
discovered_tools = discover_tools()

# Re-export common types and functions for tool development
from .containers.container_exec import execute_in_container as exec_command  # noqa: E402
from .containers.container_lifecycle import ContainerAction, manage_container_lifecycle  # noqa: E402
from .containers.container_logs import get_container_logs as container_logs  # noqa: E402
from .containers.container_stats import get_container_stats as container_stats  # noqa: E402
from .containers.list_containers import list_containers  # noqa: E402


# Create convenience functions for common container operations
async def start_container(container_id: str, **kwargs):
    """Start a container."""
    return await manage_container_lifecycle(container_id, ContainerAction.START, **kwargs)

async def stop_container(container_id: str, force: bool = False, timeout: int = 10, **kwargs):
    """Stop a container."""
    return await manage_container_lifecycle(container_id, ContainerAction.STOP, force=force, timeout=timeout, **kwargs)

async def restart_container(container_id: str, timeout: int = 10, **kwargs):
    """Restart a container."""
    return await manage_container_lifecycle(container_id, ContainerAction.RESTART, timeout=timeout, **kwargs)

async def remove_container(container_id: str, force: bool = False, remove_volumes: bool = False, **kwargs):
    """Remove a container."""
    return await manage_container_lifecycle(
        container_id, ContainerAction.REMOVE,
        force=force, remove_volumes=remove_volumes, **kwargs
    )

# Import available image management functions
from .images.image_management import list_images, search_images, tag_image  # noqa: E402


# Define stubs for missing functions to avoid import errors
def pull_image(*args, **kwargs):
    raise NotImplementedError("pull_image has not been implemented yet")

def remove_image(*args, **kwargs):
    raise NotImplementedError("remove_image has not been implemented yet")

def build_image(*args, **kwargs):
    raise NotImplementedError("build_image has not been implemented yet")

def push_image(*args, **kwargs):
    raise NotImplementedError("push_image has not been implemented yet")

# Import network management functions
from .networks.network_management import connect_container_to_network as connect_container  # noqa: E402
from .networks.network_management import (  # noqa: E402
    create_network,
    inspect_network,
    list_networks,
    remove_network,
)
from .networks.network_management import disconnect_container_from_network as disconnect_container  # noqa: E402

# Alias for backward compatibility
get_network = inspect_network

# Import volume management functions
from .system.system_management import get_disk_usage as disk_usage  # noqa: E402

# Import system management functions
from .system.system_management import get_system_info as system_info  # noqa: E402
from .system.system_management import prune_system  # noqa: E402
from .volumes.volume_management import create_volume, list_volumes, prune_volumes, remove_volume  # noqa: E402

# Import workflow management functions
from .workflows.workflow_management import (  # noqa: E402
    create_workflow,
    get_workflow_status,
    start_workflow,
    stop_workflow,
)

# Import desktop management functions (Docker Desktop daemon, updates, recovery)
try:
    from .desktop import (
        docker_daemon_recover,
        docker_daemon_restart,
        docker_desktop_status,
        docker_desktop_update,
    )
    desktop_tools = [
        docker_desktop_status,
        docker_daemon_recover,
        docker_daemon_restart,
        docker_desktop_update
    ]
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(
        f"Desktop tools not available: {e!s}. "
        "Desktop tools require Windows with Docker Desktop."
    )
    desktop_tools = []

# GPU tools are conditionally imported to avoid import errors on systems without NVIDIA GPUs
gpu_tools = []
try:
    from .gpu import (
        create_gpu_container,
        get_container_gpu_info,
        get_gpu_info,
        list_gpus,
        monitor_gpu_usage,
    )
    gpu_tools = [
        list_gpus,
        get_gpu_info,
        monitor_gpu_usage,
        create_gpu_container,
        get_container_gpu_info
    ]
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(
        f"GPU tools not available: {e!s}. "
        "Install GPU dependencies with: pip install -r requirements-gpu.txt"
    )
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(
        f"Failed to initialize GPU tools: {e!s}"
    )

__all__ = [
    'build_image',
    'connect_container',
    'container_logs',
    'container_stats',
    'create_container',
    'create_gpu_container',
    'create_network',
    'create_volume',
    # Workflow tools
    'create_workflow',
    'disconnect_container',
    'discovered_tools',
    'disk_usage',
    'docker_daemon_recover',
    'docker_daemon_restart',
    # Desktop management tools
    'docker_desktop_status',
    'docker_desktop_update',
    'exec_command',
    'get_container',
    'get_container_gpu_info',
    'get_gpu_info',
    'get_network',
    'get_workflow_status',
    # Container tools
    'list_containers',
    # GPU tools
    'list_gpus',
    # Image tools
    'list_images',
    # Network tools
    'list_networks',
    # Volume tools
    'list_volumes',
    'monitor_gpu_usage',
    'prune_system',
    'prune_volumes',
    'pull_image',
    'push_image',
    'remove_container',
    'remove_image',
    'remove_network',
    'remove_volume',
    'restart_container',
    'search_images',
    'start_container',
    'start_workflow',
    'stop_container',
    'stop_workflow',
    # System tools
    'system_info',
    'tag_image'
]
