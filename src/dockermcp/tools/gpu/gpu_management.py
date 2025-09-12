"""
GPU Management Tools for DockerMCP

This module provides tools for managing NVIDIA GPU resources in Docker containers.
"""
from __future__ import annotations

import json
import logging
import subprocess
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Literal

import docker
from pydantic import BaseModel, Field, validator

from fastmcp.tools.tool import Tool
from dockermcp.logging_config import logger

class GPUArchitecture(str, Enum):
    """NVIDIA GPU architecture types."""
    TESLA = "Tesla"
    AMPERE = "Ampere"
    TURING = "Turing"
    VOLTA = "Volta"
    PASCAL = "Pascal"
    MAXWELL = "Maxwell"
    KEPLER = "Kepler"
    FERMI = "Fermi"
    UNKNOWN = "Unknown"

class GPUDevice(BaseModel):
    """Represents a GPU device."""
    id: str = Field(..., description="GPU device ID")
    name: str = Field(..., description="GPU model name")
    memory_total: int = Field(..., description="Total GPU memory in bytes")
    memory_used: int = Field(0, description="Used GPU memory in bytes")
    memory_free: int = Field(0, description="Free GPU memory in bytes")
    utilization_gpu: int = Field(0, description="GPU utilization percentage")
    utilization_memory: int = Field(0, description="Memory utilization percentage")
    temperature: int = Field(0, description="GPU temperature in Celsius")
    power_draw: int = Field(0, description="Power draw in watts")
    power_limit: int = Field(0, description="Power limit in watts")
    architecture: GPUArchitecture = Field(GPUArchitecture.UNKNOWN, description="GPU architecture")
    cuda_version: str = Field("", description="CUDA version supported by the GPU")
    driver_version: str = Field("", description="NVIDIA driver version")
    pci_bus_id: str = Field("", description="PCI bus ID")
    uuid: str = Field("", description="GPU UUID")

    @property
    def memory_percent_used(self) -> float:
        """Calculate the percentage of GPU memory used."""
        return (self.memory_used / self.memory_total * 100) if self.memory_total > 0 else 0

class GPUStats(BaseModel):
    """GPU statistics and metrics."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    devices: List[GPUDevice] = Field(default_factory=list)
    total_memory: int = 0
    used_memory: int = 0
    free_memory: int = 0
    avg_utilization: float = 0.0

class GPUManager:
    """Manages GPU resources and provides GPU-related operations."""
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        """Initialize the GPU manager."""
        self.docker_client = docker_client or docker.from_env()
        self._gpu_info: Optional[Dict[str, Any]] = None
        self._nvidia_smi_available = self._check_nvidia_smi()
    
    def _check_nvidia_smi(self) -> bool:
        """Check if nvidia-smi is available."""
        try:
            subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("nvidia-smi not found. GPU monitoring will be limited.")
            return False
    
    def _get_gpu_info_nvidia_smi(self) -> Dict[str, Any]:
        """Get GPU information using nvidia-smi."""
        if not self._nvidia_smi_available:
            return {}
        
        try:
            # Get basic GPU info
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw,power.limit,driver_version,pci.bus_id,uuid",
                    "--format=json"
                ],
                check=True,
                capture_output=True,
                text=True
            )
            
            gpu_data = json.loads(result.stdout)
            return gpu_data.get("gpu", [])
            
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get GPU info: {str(e)}")
            return {}
    
    def get_gpu_devices(self, refresh: bool = False) -> List[GPUDevice]:
        """Get information about available GPU devices."""
        if not refresh and self._gpu_info is not None:
            return self._gpu_info
        
        gpu_info = []
        
        # Get GPU info from nvidia-smi
        nvidia_info = self._get_gpu_info_nvidia_smi()
        
        for gpu in nvidia_info:
            try:
                # Parse memory values (e.g., "8119 MiB" -> 8119 * 1024 * 1024)
                def parse_memory(mem_str: str) -> int:
                    if not mem_str or mem_str.lower() == "n/a":
                        return 0
                    try:
                        value, unit = mem_str.strip().split()
                        value = float(value)
                        if "MiB" in unit:
                            return int(value * 1024 * 1024)
                        elif "GiB" in unit:
                            return int(value * 1024 * 1024 * 1024)
                        return int(value)
                    except (ValueError, AttributeError):
                        return 0
                
                # Parse numeric values
                def parse_int(value: str) -> int:
                    try:
                        return int(float(value))
                    except (ValueError, TypeError, AttributeError):
                        return 0
                
                # Parse power values (e.g., "149 W" -> 149)
                def parse_power(power_str: str) -> int:
                    if not power_str or power_str.lower() == "n/a":
                        return 0
                    try:
                        return int(float(power_str.split()[0]))
                    except (ValueError, AttributeError, IndexError):
                        return 0
                
                # Determine architecture from GPU name
                def get_architecture(gpu_name: str) -> GPUArchitecture:
                    gpu_name = (gpu_name or "").lower()
                    if any(arch in gpu_name for arch in ["a100", "a30", "a40"]):
                        return GPUArchitecture.AMPERE
                    elif any(arch in gpu_name for arch in ["t4", "rtx 20", "rtx 30"]):
                        return GPUArchitecture.TURING
                    elif any(arch in gpu_name for arch in ["v100"]):
                        return GPUArchitecture.VOLTA
                    elif any(arch in gpu_name for arch in ["p100", "p40", "p4"]):
                        return GPUArchitecture.PASCAL
                    elif any(arch in gpu_name for arch in ["m40", "m60"]):
                        return GPUArchitecture.MAXWELL
                    elif any(arch in gpu_name for arch in ["k80", "k40"]):
                        return GPUArchitecture.KEPLER
                    elif any(arch in gpu_name for arch in ["tesla"]):
                        return GPUArchitecture.TESLA
                    return GPUArchitecture.UNKNOWN
                
                # Create GPU device
                device = GPUDevice(
                    id=str(gpu.get("index", "0")),
                    name=gpu.get("name", "Unknown GPU").strip(),
                    memory_total=parse_memory(gpu.get("memory.total", "0")),
                    memory_used=parse_memory(gpu.get("memory.used", "0")),
                    memory_free=parse_memory(gpu.get("memory.free", "0")),
                    utilization_gpu=parse_int(gpu.get("utilization.gpu", "0")),
                    utilization_memory=parse_int(gpu.get("utilization.memory", "0")),
                    temperature=parse_int(gpu.get("temperature.gpu", "0")),
                    power_draw=parse_power(gpu.get("power.draw", "0")),
                    power_limit=parse_power(gpu.get("power.limit", "0")),
                    architecture=get_architecture(gpu.get("name", "")),
                    driver_version=gpu.get("driver_version", ""),
                    pci_bus_id=gpu.get("pci.bus_id", ""),
                    uuid=gpu.get("uuid", "")
                )
                
                gpu_info.append(device)
                
            except Exception as e:
                logger.error(f"Error parsing GPU info: {str(e)}", exc_info=True)
        
        self._gpu_info = gpu_info
        return gpu_info
    
    def get_gpu_stats(self) -> GPUStats:
        """Get current GPU statistics."""
        devices = self.get_gpu_devices()
        
        total_memory = sum(device.memory_total for device in devices)
        used_memory = sum(device.memory_used for device in devices)
        free_memory = sum(device.memory_free for device in devices)
        
        if devices:
            avg_utilization = sum(device.utilization_gpu for device in devices) / len(devices)
        else:
            avg_utilization = 0.0
        
        return GPUStats(
            devices=devices,
            total_memory=total_memory,
            used_memory=used_memory,
            free_memory=free_memory,
            avg_utilization=avg_utilization
        )
    
    def get_available_gpus(self, min_memory: int = 0) -> List[GPUDevice]:
        """Get a list of available GPUs with at least min_memory bytes free."""
        return [
            gpu for gpu in self.get_gpu_devices()
            if gpu.memory_free >= min_memory
        ]
    
    def get_gpu_by_id(self, gpu_id: str) -> Optional[GPUDevice]:
        """Get a GPU device by its ID."""
        for gpu in self.get_gpu_devices():
            if gpu.id == gpu_id:
                return gpu
        return None

# Global GPU manager instance
gpu_manager = GPUManager()

@Tool(
    name="list_gpus",
    description="List available NVIDIA GPUs and their status",
    parameters={
        'type': 'object',
        'properties': {
            'refresh': {
                'type': 'boolean',
                'default': False,
                'description': 'Whether to refresh the GPU information cache'
            },
            'detailed': {
                'type': 'boolean',
                'default': False,
                'description': 'Whether to include detailed GPU information'
            }
        }
    }
)
async def list_gpus(refresh: bool = False, detailed: bool = False) -> Dict[str, Any]:
    """
    List all available NVIDIA GPUs and their current status.
    
    Args:
        refresh: Whether to refresh the GPU information cache
        detailed: Whether to include detailed GPU information
        
    Returns:
        Dictionary containing GPU information
        
    Example:
        >>> await list_gpus()
        {
            'status': 'success',
            'gpus': [
                {
                    'id': '0',
                    'name': 'NVIDIA GeForce RTX 3090',
                    'memory_total': 25769803776,
                    'memory_used': 1073741824,
                    'memory_free': 24696061952,
                    'utilization_gpu': 5,
                    'utilization_memory': 10,
                    'temperature': 45,
                    'power_draw': 65,
                    'power_limit': 350,
                    'architecture': 'Ampere',
                    'driver_version': '470.57.02',
                    'memory_percent_used': 4.17
                }
            ],
            'total_gpus': 1,
            'total_memory': 25769803776,
            'used_memory': 1073741824,
            'free_memory': 24696061952,
            'avg_utilization': 5.0
        }
    """
    try:
        gpus = gpu_manager.get_gpu_devices(refresh=refresh)
        gpu_stats = gpu_manager.get_gpu_stats()
        
        if not detailed:
            gpu_list = [
                {
                    'id': gpu.id,
                    'name': gpu.name,
                    'memory_total': gpu.memory_total,
                    'memory_used': gpu.memory_used,
                    'memory_free': gpu.memory_free,
                    'memory_percent_used': round(gpu.memory_percent_used, 2),
                    'utilization_gpu': gpu.utilization_gpu,
                    'temperature': gpu.temperature,
                    'power_draw': gpu.power_draw,
                    'power_limit': gpu.power_limit,
                    'architecture': gpu.architecture.value
                }
                for gpu in gpus
            ]
        else:
            gpu_list = [gpu.dict() for gpu in gpus]
        
        return {
            'status': 'success',
            'gpus': gpu_list,
            'total_gpus': len(gpus),
            'total_memory': gpu_stats.total_memory,
            'used_memory': gpu_stats.used_memory,
            'free_memory': gpu_stats.free_memory,
            'avg_utilization': round(gpu_stats.avg_utilization, 2)
        }
    
    except Exception as e:
        error_msg = f"Failed to list GPUs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }

@Tool(
    name="get_gpu_info",
    description="Get detailed information about a specific GPU",
    parameters={
        'type': 'object',
        'properties': {
            'gpu_id': {
                'type': 'string',
                'description': 'ID of the GPU to get information about'
            },
            'refresh': {
                'type': 'boolean',
                'default': False,
                'description': 'Whether to refresh the GPU information cache'
            }
        },
        'required': ['gpu_id']
    }
)
async def get_gpu_info(gpu_id: str, refresh: bool = False) -> Dict[str, Any]:
    """
    Get detailed information about a specific GPU.
    
    Args:
        gpu_id: ID of the GPU to get information about
        refresh: Whether to refresh the GPU information cache
        
    Returns:
        Dictionary containing detailed GPU information
        
    Example:
        >>> await get_gpu_info("0")
        {
            'status': 'success',
            'gpu': {
                'id': '0',
                'name': 'NVIDIA GeForce RTX 3090',
                'memory_total': 25769803776,
                'memory_used': 1073741824,
                'memory_free': 24696061952,
                'utilization_gpu': 5,
                'utilization_memory': 10,
                'temperature': 45,
                'power_draw': 65,
                'power_limit': 350,
                'architecture': 'Ampere',
                'driver_version': '470.57.02',
                'pci_bus_id': '0000:4B:00.0',
                'uuid': 'GPU-12345678-1234-1234-1234-1234567890ab',
                'memory_percent_used': 4.17
            }
        }
    """
    try:
        gpu = gpu_manager.get_gpu_by_id(gpu_id)
        if not gpu:
            return {
                'status': 'error',
                'error': f'GPU with ID {gpu_id} not found'
            }
        
        return {
            'status': 'success',
            'gpu': gpu.dict()
        }
    
    except Exception as e:
        error_msg = f"Failed to get GPU info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }

@Tool(
    name="monitor_gpu_usage",
    description="Monitor GPU usage in real-time",
    parameters={
        'type': 'object',
        'properties': {
            'interval': {
                'type': 'number',
                'default': 5.0,
                'minimum': 1.0,
                'description': 'Polling interval in seconds'
            },
            'duration': {
                'type': 'number',
                'default': 60.0,
                'minimum': 1.0,
                'description': 'Duration to monitor in seconds'
            }
        }
    }
)
async def monitor_gpu_usage(interval: float = 5.0, duration: float = 60.0) -> Dict[str, Any]:
    """
    Monitor GPU usage in real-time for a specified duration.
    
    Args:
        interval: Polling interval in seconds
        duration: Total duration to monitor in seconds
        
    Returns:
        Dictionary containing monitoring results
        
    Example:
        >>> await monitor_gpu_usage(interval=2, duration=10)
        {
            'status': 'success',
            'samples': [
                {
                    'timestamp': '2023-01-01T12:00:00.000000',
                    'gpus': [
                        {
                            'id': '0',
                            'utilization_gpu': 45,
                            'memory_used': 8589934592,
                            'memory_percent_used': 33.33,
                            'temperature': 72
                        }
                    ],
                    'avg_utilization': 45.0,
                    'total_memory_used': 8589934592
                },
                ...
            ]
        }
    """
    try:
        import asyncio
        from datetime import datetime, timedelta
        
        samples = []
        end_time = datetime.utcnow() + timedelta(seconds=duration)
        
        while datetime.utcnow() < end_time:
            gpu_stats = gpu_manager.get_gpu_stats()
            
            sample = {
                'timestamp': datetime.utcnow().isoformat(),
                'gpus': [
                    {
                        'id': gpu.id,
                        'utilization_gpu': gpu.utilization_gpu,
                        'memory_used': gpu.memory_used,
                        'memory_percent_used': round(gpu.memory_percent_used, 2),
                        'temperature': gpu.temperature
                    }
                    for gpu in gpu_stats.devices
                ],
                'avg_utilization': round(gpu_stats.avg_utilization, 2),
                'total_memory_used': gpu_stats.used_memory
            }
            
            samples.append(sample)
            
            # Sleep until next interval or until end time
            sleep_time = min(interval, (end_time - datetime.utcnow()).total_seconds())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                break
        
        return {
            'status': 'success',
            'samples': samples,
            'sample_count': len(samples)
        }
    
    except Exception as e:
        error_msg = f"Failed to monitor GPU usage: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }
