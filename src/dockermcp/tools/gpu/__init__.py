"""
GPU Management Tools for DockerMCP

This module provides tools for managing NVIDIA GPU resources in Docker containers.
"""

from .gpu_containers import (
    GPUContainerConfig,
    GPUContainerManager,
    create_gpu_container,
    get_container_gpu_info,
    gpu_container_manager,
)
from .gpu_management import (
    GPUArchitecture,
    GPUDevice,
    GPUManager,
    GPUStats,
    get_gpu_info,
    gpu_manager,
    list_gpus,
    monitor_gpu_usage,
)

__all__ = [
    # GPU Management
    "GPUArchitecture",
    # GPU Containers
    "GPUContainerConfig",
    "GPUContainerManager",
    "GPUDevice",
    "GPUManager",
    "GPUStats",
    "create_gpu_container",
    "get_container_gpu_info",
    "get_gpu_info",
    "gpu_container_manager",
    "gpu_manager",
    "list_gpus",
    "monitor_gpu_usage",
]

# Initialize GPU manager on import
try:
    gpu_manager.get_gpu_devices()
except Exception as e:
    import logging

    logging.getLogger(__name__).warning(f"Failed to initialize GPU manager: {e!s}")
