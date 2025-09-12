"""
GPU Management Tools for DockerMCP

This module provides tools for managing NVIDIA GPU resources in Docker containers.
"""
from typing import List, Dict, Optional, Any, Union

from .gpu_management import (
    GPUArchitecture,
    GPUDevice,
    GPUStats,
    GPUManager,
    gpu_manager,
    list_gpus,
    get_gpu_info,
    monitor_gpu_usage
)

from .gpu_containers import (
    GPUContainerConfig,
    GPUContainerManager,
    gpu_container_manager,
    create_gpu_container,
    get_container_gpu_info
)

__all__ = [
    # GPU Management
    'GPUArchitecture',
    'GPUDevice',
    'GPUStats',
    'GPUManager',
    'gpu_manager',
    'list_gpus',
    'get_gpu_info',
    'monitor_gpu_usage',
    
    # GPU Containers
    'GPUContainerConfig',
    'GPUContainerManager',
    'gpu_container_manager',
    'create_gpu_container',
    'get_container_gpu_info'
]

# Initialize GPU manager on import
try:
    gpu_manager.get_gpu_devices()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(
        f"Failed to initialize GPU manager: {str(e)}"
    )
