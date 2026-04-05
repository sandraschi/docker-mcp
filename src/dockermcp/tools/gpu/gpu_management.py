"""
GPU Management Tools for DockerMCP

This module provides tools for managing NVIDIA GPU resources in Docker containers.
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import docker
from pydantic import BaseModel, Field

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# Initialize FastMCP instance
mcp = FastMCP("GPU Management Tools")

from ...logging_config import logger

# Pydantic models for request/response
class ListGPUsRequest(BaseModel):
    """Request model for listing GPUs."""
    refresh: bool = Field(
        default=False,
        description="Whether to refresh the GPU information cache"
    )
    detailed: bool = Field(
        default=False,
        description="Whether to include detailed GPU information"
    )

class GPUInfoResponse(BaseModel):
    """Response model for GPU information."""
    id: str = Field(..., description="GPU device ID")
    name: str = Field(..., description="GPU model name")
    memory_total: int = Field(..., description="Total GPU memory in bytes")
    memory_used: int = Field(..., description="Used GPU memory in bytes")
    memory_free: int = Field(..., description="Free GPU memory in bytes")
    utilization_gpu: int = Field(..., description="GPU utilization percentage")
    utilization_memory: int = Field(..., description="Memory utilization percentage")
    temperature: int = Field(..., description="GPU temperature in Celsius")
    power_draw: int = Field(..., description="Power draw in watts")
    power_limit: int = Field(..., description="Power limit in watts")
    architecture: str = Field(..., description="GPU architecture")
    driver_version: str = Field(..., description="NVIDIA driver version")
    cuda_version: str = Field(..., description="CUDA version")
    pci_bus_id: str = Field(..., description="PCI bus ID")
    uuid: str = Field(..., description="GPU UUID")

class ListGPUsResponse(BaseModel):
    """Response model for list_gpus tool."""
    gpus: List[GPUInfoResponse] = Field(..., description="List of GPU devices")
    timestamp: str = Field(..., description="Timestamp of the response")
    total_gpus: int = Field(..., description="Total number of GPUs")

class GetGPUInfoRequest(BaseModel):
    """Request model for getting GPU info."""
    gpu_id: str = Field(..., description="ID of the GPU to get information about")
    refresh: bool = Field(
        default=False,
        description="Whether to refresh the GPU information cache"
    )

class MonitorGPUUsageRequest(BaseModel):
    """Request model for monitoring GPU usage."""
    interval: float = Field(
        default=5.0,
        ge=0.1,
        le=300,
        description="Polling interval in seconds"
    )
    duration: float = Field(
        default=60.0,
        ge=1.0,
        le=3600,
        description="Total duration to monitor in seconds"
    )

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
        try:
            if docker_client:
                self.docker_client = docker_client
            else:
                from ....dockermcp import docker_client as global_client, docker_available
                if docker_available:
                    self.docker_client = global_client
                else:
                    self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = None
            
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

@mcp.tool
async def list_gpus(request: ListGPUsRequest) -> ListGPUsResponse:
    """
    List all available NVIDIA GPUs and their current status.
    
    This function retrieves information about all NVIDIA GPUs in the system,
    including their memory usage, utilization, temperature, and other metrics.
    
    Args:
        request: ListGPUsRequest containing:
            - refresh: Whether to refresh the GPU information cache
            - detailed: Whether to include detailed GPU information
        
    Returns:
        ListGPUsResponse with list of GPUs and their status
        
    Raises:
        ToolError: If there's an error retrieving GPU information
        
    Example:
        >>> await list_gpus(ListGPUsRequest(refresh=True, detailed=True))
        ListGPUsResponse(
            gpus=[
                GPUInfoResponse(
                    id='0',
                    name='NVIDIA GeForce RTX 3090',
                    memory_total=25769803776,
                    memory_used=1073741824,
                    memory_free=24696061952,
                    utilization_gpu=5,
                    utilization_memory=10,
                    temperature=45,
                    power_draw=65,
                    power_limit=350,
                    architecture='Ampere',
                    driver_version='470.57.02',
                    cuda_version='11.4',
                    pci_bus_id='0000:4B:00.0',
                    uuid='GPU-12345678-1234-1234-1234-1234567890ab'
                )
            ],
            timestamp='2023-01-01T12:00:00.000000',
            total_gpus=1
        )
    """
    try:
        # Get GPU devices
        gpu_devices = gpu_manager.get_gpu_devices(refresh=request.refresh)
        
        # Convert GPU devices to response models
        gpu_responses = []
        for device in gpu_devices:
            gpu_response = GPUInfoResponse(
                id=device.id,
                name=device.name,
                memory_total=device.memory_total,
                memory_used=device.memory_used,
                memory_free=device.memory_free,
                utilization_gpu=device.utilization_gpu,
                utilization_memory=device.utilization_memory,
                temperature=device.temperature,
                power_draw=device.power_draw,
                power_limit=device.power_limit,
                architecture=device.architecture.value,
                driver_version=device.driver_version,
                cuda_version=device.cuda_version,
                pci_bus_id=device.pci_bus_id,
                uuid=device.uuid
            )
            gpu_responses.append(gpu_response)
        
        # Create and return the response
        return ListGPUsResponse(
            gpus=gpu_responses,
            timestamp=datetime.utcnow().isoformat(),
            total_gpus=len(gpu_responses)
        )
        
    except Exception as e:
        error_msg = f"Failed to list GPUs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

@mcp.tool
async def get_gpu_info(request: GetGPUInfoRequest) -> GPUInfoResponse:
    """
    Get detailed information about a specific GPU.
    
    Args:
        request: GetGPUInfoRequest containing GPU ID and refresh flag
        
    Returns:
        GPUInfoResponse with detailed GPU information
        
    Example:
        >>> await get_gpu_info(GetGPUInfoRequest(gpu_id="0", refresh=True))
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
            'cuda_version': '11.4',
            'pci_bus_id': '0000:4B:00.0',
            'uuid': 'GPU-12345678-1234-1234-1234-1234567890ab'
        }
    """
    try:
        # Refresh GPU info if requested
        gpu = gpu_manager.get_gpu_by_id(request.gpu_id)
        if not gpu:
            error_msg = f'GPU with ID {request.gpu_id} not found'
            logger.error(error_msg)
            raise ToolError(error_msg)
            
        return GPUInfoResponse(
            id=gpu.id,
            name=gpu.name,
            memory_total=gpu.memory_total,
            memory_used=gpu.memory_used,
            memory_free=gpu.memory_free,
            utilization_gpu=gpu.utilization_gpu,
            utilization_memory=gpu.utilization_memory,
            temperature=gpu.temperature,
            power_draw=gpu.power_draw,
            power_limit=gpu.power_limit,
            architecture=gpu.architecture.value,
            driver_version=gpu.driver_version,
            cuda_version=gpu.cuda_version,
            pci_bus_id=gpu.pci_bus_id,
            uuid=gpu.uuid
        )
        
    except Exception as e:
        error_msg = f'Failed to get GPU info: {str(e)}'
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

class GPUSample(BaseModel):
    """A single sample of GPU usage data."""
    id: str = Field(..., description="GPU device ID")
    utilization_gpu: int = Field(..., description="GPU utilization percentage")
    memory_used: int = Field(..., description="Used GPU memory in bytes")
    memory_percent_used: float = Field(..., description="Percentage of GPU memory used")
    temperature: int = Field(..., description="GPU temperature in Celsius")

class MonitoringSample(BaseModel):
    """A single sample of GPU monitoring data."""
    timestamp: str = Field(..., description="ISO timestamp of the sample")
    gpus: List[GPUSample] = Field(..., description="List of GPU samples")
    avg_utilization: float = Field(..., description="Average GPU utilization across all GPUs")
    total_memory_used: int = Field(..., description="Total memory used across all GPUs in bytes")

class MonitorGPUUsageResponse(BaseModel):
    """Response model for monitor_gpu_usage tool."""
    samples: List[MonitoringSample] = Field(..., description="List of monitoring samples")
    sample_count: int = Field(..., description="Total number of samples collected")

@mcp.tool
async def monitor_gpu_usage(request: MonitorGPUUsageRequest) -> MonitorGPUUsageResponse:
    """
    Monitor GPU usage in real-time for a specified duration.
    
    This function collects GPU utilization, memory usage, and temperature metrics
    at regular intervals for the specified duration.
    
    Args:
        request: MonitorGPUUsageRequest containing:
            - interval: Polling interval in seconds (0.1-300)
            - duration: Total monitoring duration in seconds (1-3600)
            
    Returns:
        MonitorGPUUsageResponse containing:
            - samples: List of monitoring samples with GPU metrics
            - sample_count: Total number of samples collected
            
    Raises:
        ToolError: If monitoring fails or invalid parameters are provided
        
    Example:
        >>> await monitor_gpu_usage(MonitorGPUUsageRequest(interval=2, duration=10))
        {
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
                }
            ],
            'sample_count': 1
        }
    """
    try:
        # Validate input parameters
        if request.interval <= 0 or request.interval > 300:
            raise ValueError("Interval must be between 0.1 and 300 seconds")
            
        if request.duration < 1 or request.duration > 3600:
            raise ValueError("Duration must be between 1 and 3600 seconds")
            
        samples = []
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=request.duration)
        
        logger.info(f"Starting GPU monitoring for {request.duration} seconds with {request.interval}s interval")
        
        # Initial sample
        gpu_stats = gpu_manager.get_gpu_stats()
        sample = MonitoringSample(
            timestamp=start_time.isoformat(),
            gpus=[
                GPUSample(
                    id=gpu.id,
                    utilization_gpu=gpu.utilization_gpu,
                    memory_used=gpu.memory_used,
                    memory_percent_used=round(gpu.memory_percent_used, 2),
                    temperature=gpu.temperature
                )
                for gpu in gpu_stats.devices
            ],
            avg_utilization=round(gpu_stats.avg_utilization, 2),
            total_memory_used=gpu_stats.used_memory
        )
        samples.append(sample)
        
        # Continue monitoring until duration elapses
        while (datetime.utcnow() + timedelta(seconds=request.interval)) < end_time:
            try:
                await asyncio.sleep(request.interval)
                
                # Get fresh GPU stats
                gpu_stats = gpu_manager.get_gpu_stats()
                
                sample = MonitoringSample(
                    timestamp=datetime.utcnow().isoformat(),
                    gpus=[
                        GPUSample(
                            id=gpu.id,
                            utilization_gpu=gpu.utilization_gpu,
                            memory_used=gpu.memory_used,
                            memory_percent_used=round(gpu.memory_percent_used, 2),
                            temperature=gpu.temperature
                        )
                        for gpu in gpu_stats.devices
                    ],
                    avg_utilization=round(gpu_stats.avg_utilization, 2),
                    total_memory_used=gpu_stats.used_memory
                )
                
                samples.append(sample)
                
            except Exception as e:
                logger.error(f"Error during GPU monitoring: {str(e)}", exc_info=True)
                # Continue monitoring even if one sample fails
                continue
        
        logger.info(f"Completed GPU monitoring. Collected {len(samples)} samples")
        
        return MonitorGPUUsageResponse(
            samples=samples,
            sample_count=len(samples)
        )
    
    except Exception as e:
        error_msg = f"Failed to monitor GPU usage: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
