"""
GPU-accelerated Container Management for DockerMCP

This module provides tools for managing GPU-accelerated Docker containers.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Any, Union, Literal, Annotated, ClassVar

import docker
from pydantic import BaseModel, Field, ConfigDict, field_validator

from dockermcp.mcp_instance import mcp
from dockermcp.logging_config import logger
from .gpu_management import GPUManager, GPUDevice

class GPUContainerConfig(BaseModel):
    """Configuration for GPU-accelerated containers."""
    device_requests: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of device requests for the container"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the container"
    )
    runtime: str = Field(
        "nvidia",
        description="Container runtime to use (e.g., 'nvidia' or 'nvidia-container-runtime')"
    )
    gpu_ids: Optional[List[Union[int, str]]] = Field(
        None,
        description="List of GPU IDs to use (e.g., [0, 1] or ['all'])"
    )
    count: Optional[Union[int, str]] = Field(
        None,
        description="Number of GPUs to use (integer) or 'all'"
    )
    capabilities: List[List[str]] = Field(
        [['gpu']],
        description="List of GPU capabilities to enable"
    )
    driver: str = Field(
        "",
        description="Driver capabilities to use (e.g., 'nvidia')"
    )
    
    model_config = ConfigDict(
        json_encoders={
            'set': list
        }
    )
    
    @field_validator('gpu_ids', mode='before')
    @classmethod
    def validate_gpu_ids(cls, v):
        if v == 'all':
            return ['all']
        if isinstance(v, str):
            return [gpu_id.strip() for gpu_id in v.split(',')]
        return v
    
    @field_validator('count', mode='before')
    @classmethod
    def validate_count(cls, v):
        if isinstance(v, str) and v.lower() == 'all':
            return 'all'
        if v is not None and v != 'all':
            try:
                return int(v)
            except (ValueError, TypeError):
                pass
        return v

class GPUContainerManager:
    """Manages GPU-accelerated Docker containers."""
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        """Initialize the GPU container manager."""
        self.docker_client = docker_client or docker.from_env()
        self.gpu_manager = GPUManager()
    
    def _create_device_request(
        self,
        gpu_ids: Optional[List[Union[int, str]]] = None,
        count: Optional[Union[int, str]] = None,
        capabilities: Optional[List[List[str]]] = None,
        driver: str = ""
    ) -> Dict[str, Any]:
        """Create a device request for GPU access."""
        device_request = {
            'Driver': driver or '',
            'Count': -1,  # All available GPUs
            'Capabilities': capabilities or [['gpu']],
            'Options': {}
        }
        
        if gpu_ids == ['all'] or count == 'all':
            # Use all available GPUs
            device_request['Count'] = -1
        elif count is not None and isinstance(count, int) and count > 0:
            # Use specific number of GPUs
            device_request['Count'] = count
        elif gpu_ids and gpu_ids != ['all']:
            # Use specific GPU devices
            device_request['DeviceIDs'] = [str(gpu_id) for gpu_id in gpu_ids]
        
        return device_request
    
    def create_gpu_container_config(
        self,
        gpu_ids: Optional[List[Union[int, str]]] = None,
        count: Optional[Union[int, str]] = None,
        capabilities: Optional[List[List[str]]] = None,
        driver: str = "",
        runtime: str = "nvidia",
        environment: Optional[Dict[str, str]] = None
    ) -> GPUContainerConfig:
        """Create a configuration for a GPU-accelerated container."""
        device_request = self._create_device_request(
            gpu_ids=gpu_ids,
            count=count,
            capabilities=capabilities,
            driver=driver
        )
        
        # Set NVIDIA-specific environment variables
        env = environment or {}
        if gpu_ids and gpu_ids != ['all']:
            env['NVIDIA_VISIBLE_DEVICES'] = ','.join(str(gpu_id) for gpu_id in gpu_ids)
        
        return GPUContainerConfig(
            device_requests=[device_request],
            environment=env,
            runtime=runtime,
            gpu_ids=gpu_ids,
            count=count,
            capabilities=capabilities or [['gpu']],
            driver=driver
        )
    
    def get_container_gpu_info(self, container_id: str) -> Dict[str, Any]:
        """Get GPU information for a running container."""
        try:
            container = self.docker_client.containers.get(container_id)
            container.reload()  # Refresh container data
            
            # Get GPU device information
            gpu_info = {}
            
            # Check if container has GPU access
            if container.attrs.get('HostConfig', {}).get('Runtime') == 'nvidia':
                # Get GPU IDs from environment
                env_vars = {}
                if 'Config' in container.attrs and 'Env' in container.attrs['Config']:
                    env_vars = {
                        k: v for k, v in 
                        (var.split('=', 1) for var in container.attrs['Config']['Env'] 
                         if '=' in var)
                    }
                
                gpu_ids = env_vars.get('NVIDIA_VISIBLE_DEVICES', 'all')
                if gpu_ids.lower() == 'all':
                    gpu_ids = [gpu.id for gpu in self.gpu_manager.get_gpu_devices()]
                else:
                    gpu_ids = [gpu_id.strip() for gpu_id in gpu_ids.split(',')]
                
                gpu_info['gpu_ids'] = gpu_ids
                gpu_info['gpus'] = []
                
                for gpu_id in gpu_ids:
                    gpu = self.gpu_manager.get_gpu_by_id(gpu_id)
                    if gpu:
                        gpu_info['gpus'].append(gpu.dict())
            
            return {
                'status': 'success',
                'container_id': container_id,
                'has_gpu_access': bool(gpu_info.get('gpus')),
                **gpu_info
            }
            
        except docker.errors.NotFound:
            return {
                'status': 'error',
                'error': f'Container {container_id} not found'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Failed to get container GPU info: {str(e)}'
            }

# Global GPU container manager instance
gpu_container_manager = GPUContainerManager()


@mcp.tool
async def create_gpu_container(
    image: str,
    command: Optional[str] = None,
    gpu_ids: Union[List[Union[int, str]], str] = 'all',
    count: Optional[Union[int, str]] = None,
    runtime: str = 'nvidia',
    environment: Optional[Dict[str, str]] = None,
    name: Optional[str] = None,
    detach: bool = True,
    auto_remove: bool = False,
    shm_size: str = '2g',
    volumes: Optional[Dict[str, str]] = None,
    ports: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create and start a GPU-accelerated Docker container.
    
    Args:
        image: Docker image to use
        command: Command to run in the container
        gpu_ids: List of GPU IDs to use or 'all' for all GPUs
        count: Number of GPUs to use or 'all' for all GPUs
        runtime: Container runtime to use (e.g., 'nvidia')
        environment: Environment variables to set in the container
        name: Name for the container
        detach: Run container in detached mode
        auto_remove: Automatically remove the container when it exits
        shm_size: Size of /dev/shm (e.g., '2g')
        volumes: Volume mappings (host_path:container_path)
        ports: Port mappings (host_port:container_port)
        
    Returns:
        Dictionary with container information
        
    Example:
        >>> await create_gpu_container(
        ...     image="nvidia/cuda:11.0-base",
        ...     command="nvidia-smi",
        ...     gpu_ids=[0],
        ...     name="gpu-test"
        ... )
        {
            'status': 'success',
            'container_id': 'abc123...',
            'container_name': 'gpu-test',
            'gpu_ids': [0],
            'warnings': []
        }
    """
    try:
        docker_client = docker.from_env()
        gpu_manager = GPUContainerManager(docker_client)
        
        # Handle default values
        environment = environment or {}
        volumes = volumes or {}
        ports = ports or {}
        
        # Create GPU container configuration
        gpu_ids_list = gpu_ids if isinstance(gpu_ids, list) else [gpu_ids]
        config = gpu_manager.create_gpu_container_config(
            gpu_ids=gpu_ids_list,
            count=count,
            runtime=runtime,
            environment=environment
        )
        
        # Prepare container configuration
        container_config = {
            'image': image,
            'command': command,
            'detach': detach,
            'auto_remove': auto_remove,
            'runtime': config.runtime,
            'environment': config.environment,
            'shm_size': shm_size,
            'device_requests': config.device_requests
        }
        
        if name:
            container_config['name'] = name
        
        if volumes:
            container_config['volumes'] = {
                host_path: {'bind': container_path, 'mode': 'rw'}
                for host_path, container_path in volumes.items()
            }
        
        if ports:
            container_config['ports'] = {
                container_port: host_port
                for host_port, container_port in ports.items()
            }
        
        # Create and start the container
        container = docker_client.containers.run(**container_config)
        
        if detach:
            # Get container info
            container.reload()
            
            return {
                'status': 'success',
                'container_id': container.id,
                'container_name': container.name,
                'gpu_ids': gpu_ids if isinstance(gpu_ids, list) else [gpu_ids],
                'warnings': []
            }
        else:
            # For non-detached mode, return the container output
            return {
                'status': 'success',
                'output': container,
                'gpu_ids': gpu_ids if isinstance(gpu_ids, list) else [gpu_ids]
            }
    
    except docker.errors.ImageNotFound as e:
        error_msg = f'Docker image not found: {image}'
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'image': image
        }
    except docker.errors.APIError as e:
        error_msg = f'Docker API error: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }
    except Exception as e:
        error_msg = f'Failed to create GPU container: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }


@mcp.tool
async def get_container_gpu_info(container_id: str) -> Dict[str, Any]:
    """
    Get GPU information for a running container.
    
    Args:
        container_id: Container ID or name
        
    Returns:
        Dictionary with GPU information for the container
        
    Example:
        >>> await get_container_gpu_info("my-gpu-container")
        {
            'status': 'success',
            'container_id': 'abc123...',
            'has_gpu_access': True,
            'gpu_ids': [0],
            'gpus': [
                {
                    'id': '0',
                    'name': 'NVIDIA GeForce RTX 3090',
                    'memory_total': 25769803776,
                    'memory_used': 1073741824,
                    'utilization_gpu': 5,
                    'temperature': 45,
                    'power_draw': 65
                }
            ]
        }
    """
    try:
        gpu_container_manager = GPUContainerManager(docker.from_env())
        result = gpu_container_manager.get_container_gpu_info(container_id)
        if result.get('status') == 'error':
            logger.error(result.get('error', 'Unknown error getting container GPU info'))
        return result
    except Exception as e:
        error_msg = f'Failed to get container GPU info: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }
