"""
Container resource management for Docker MCP.

This module provides tools for managing container resource constraints including
CPU, memory, I/O, and other resource limits. It follows FastMCP 2.12+ standards
for tool registration and error handling.
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import docker
from docker.errors import DockerException, APIError, NotFound, ContainerError
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, validator, confloat, conint

from dockermcp.logging_config import logger

class CpuPriority(str, Enum):
    """CPU priority levels for container CPU shares."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class MemoryUnit(str, Enum):
    """Memory unit options for resource limits."""
    BYTES = "b"
    KILOBYTES = "k"
    MEGABYTES = "m"
    GIGABYTES = "g"

class IoDeviceWeight(BaseModel):
    """I/O weight configuration for a device."""
    path: str = Field(..., description="Path to the device")
    weight: conint(ge=10, le=1000) = Field(
        default=100,
        description="I/O weight (10-1000, default: 100)"
    )

class UpdateResourceResult(BaseModel):
    """Result of a resource update operation."""
    container_id: str = Field(..., description="ID of the container")
    resource_type: str = Field(..., description="Type of resource that was updated")
    previous_value: Any = Field(None, description="Previous resource value")
    new_value: Any = Field(..., description="New resource value")
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings that occurred during the update"
    )

@Tool(
    name="get_container_resources",
    description="Get resource limits and usage for a container",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'include_usage': {
                'type': 'boolean',
                'default': True,
                'description': 'Include current resource usage statistics'
            }
        },
        'required': ['container_id']
    }
)
async def get_container_resources(
    container_id: str,
    include_usage: bool = True
) -> Dict[str, Any]:
    """
    Get resource limits and usage for a container.
    
    This function retrieves the current resource limits and, optionally,
    the current resource usage statistics for a container.
    
    Args:
        container_id: ID or name of the container
        include_usage: Include current resource usage statistics
        
    Returns:
        Dictionary with resource limits and usage information
        
    Example:
        >>> await get_container_resources("my-container")
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "resources": {
                "cpu": {
                    "shares": 1024,
                    "quota": 100000,
                    "period": 100000,
                    "cpus": "0-3",
                    "mems": "0-1",
                    "realtime_period": 1000000,
                    "realtime_runtime": 950000
                },
                "memory": {
                    "limit": 1073741824,
                    "reservation": 536870912,
                    "swappiness": 60,
                    "oom_kill_disable": False,
                    "kernel": 0,
                    "kernel_tcp": 0,
                    "swappiness": 60,
                    "use_hierarchy": True
                },
                "blkio": {
                    "weight": 300,
                    "weight_device": [
                        {"path": "/dev/sda", "weight": 200}
                    ],
                    "read_bps": 10485760,
                    "write_bps": 10485760,
                    "read_iops": 1000,
                    "write_iops": 1000
                },
                "pids_limit": 1024,
                "ulimits": [
                    {"name": "nofile", "soft": 1024, "hard": 2048}
                ]
            },
            "usage": {
                "cpu_usage": {
                    "total_usage": 1000000000,
                    "percpu_usage": [500000000, 500000000],
                    "usage_in_kernelmode": 100000000,
                    "usage_in_usermode": 900000000,
                    "system_cpu_usage": 5000000000,
                    "online_cpus": 2,
                    "throttling_data": {
                        "periods": 100,
                        "throttled_periods": 0,
                        "throttled_time": 0
                    }
                },
                "memory_usage": {
                    "usage": 536870912,
                    "max_usage": 805306368,
                    "stats": {
                        "cache": 100000000,
                        "rss": 400000000,
                        "rss_huge": 0,
                        "mapped_file": 0,
                        "pgpgin": 1000,
                        "pgpgout": 900,
                        "pgfault": 100,
                        "pgmajfault": 1,
                        "inactive_anon": 0,
                        "active_anon": 400000000,
                        "inactive_file": 100000000,
                        "active_file": 0,
                        "unevictable": 0,
                        "hierarchical_memory_limit": 1073741824,
                        "hierarchical_memsw_limit": 2147483648,
                        "total_cache": 100000000,
                        "total_rss": 400000000,
                        "total_rss_huge": 0,
                        "total_mapped_file": 0,
                        "total_pgpgin": 1000,
                        "total_pgpgout": 900,
                        "total_pgfault": 100,
                        "total_pgmajfault": 1,
                        "total_inactive_anon": 0,
                        "total_active_anon": 400000000,
                        "total_inactive_file": 100000000,
                        "total_active_file": 0,
                        "total_unevictable": 0
                    },
                    "limit": 1073741824,
                    "failcnt": 0
                },
                "blkio_usage": {
                    "io_service_bytes_recursive": [
                        {"major": 8, "minor": 0, "op": "read", "value": 1000000},
                        {"major": 8, "minor": 0, "op": "write", "value": 500000}
                    ],
                    "io_serviced_recursive": [
                        {"major": 8, "minor": 0, "op": "read", "value": 100},
                        {"major": 8, "minor": 0, "op": "write", "value": 50}
                    ],
                    "io_queue_recursive": [],
                    "io_service_time_recursive": [],
                    "io_wait_time_recursive": [],
                    "io_merged_recursive": [],
                    "io_time_recursive": [],
                    "sectors_recursive": []
                },
                "pids_stats": {
                    "current": 5,
                    "limit": 1024
                }
            }
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "status": "error",
                "container_id": container_id,
                "error": f"Container not found: {container_id}"
            }
        
        # Get container info
        container.reload()
        host_config = container.attrs['HostConfig']
        
        # Prepare response
        result = {
            "status": "success",
            "container_id": container.id,
            "resources": {}
        }
        
        # CPU resources
        result["resources"]["cpu"] = {
            "shares": host_config.get('CpuShares'),
            "quota": host_config.get('CpuQuota'),
            "period": host_config.get('CpuPeriod'),
            "cpus": host_config.get('CpusetCpus'),
            "mems": host_config.get('CpusetMems'),
            "realtime_period": host_config.get('CpuRealtimePeriod'),
            "realtime_runtime": host_config.get('CpuRealtimeRuntime')
        }
        
        # Memory resources
        result["resources"]["memory"] = {
            "limit": host_config.get('Memory'),
            "reservation": host_config.get('MemoryReservation'),
            "swappiness": host_config.get('MemorySwappiness'),
            "oom_kill_disable": host_config.get('OomKillDisable', False),
            "kernel": host_config.get('KernelMemory'),
            "kernel_tcp": host_config.get('KernelMemoryTCP'),
            "use_hierarchy": host_config.get('MemoryUseHierarchy')
        }
        
        # Block I/O resources
        result["resources"]["blkio"] = {
            "weight": host_config.get('BlkioWeight'),
            "weight_device": host_config.get('BlkioWeightDevice'),
            "device_read_bps": host_config.get('BlkioDeviceReadBps'),
            "device_write_bps": host_config.get('BlkioDeviceWriteBps'),
            "device_read_iops": host_config.get('BlkioDeviceReadIOps'),
            "device_write_iops": host_config.get('BlkioDeviceWriteIOps'),
        }
        
        # PID limit
        result["resources"]["pids_limit"] = host_config.get('PidsLimit')
        
        # Ulimits
        result["resources"]["ulimits"] = [
            {"name": ulimit["Name"], "soft": ulimit["Soft"], "hard": ulimit["Hard"]}
            for ulimit in (host_config.get('Ulimits') or [])
        ]
        
        # Get current resource usage if requested
        if include_usage:
            try:
                stats = container.stats(stream=False)
                result["usage"] = {
                    "cpu_usage": stats.get('cpu_stats', {}),
                    "memory_usage": stats.get('memory_stats', {}),
                    "blkio_usage": stats.get('blkio_stats', {}),
                    "pids_stats": stats.get('pids_stats', {})
                }
            except Exception as e:
                logger.warning(f"Failed to get container stats: {str(e)}")
                result["usage"] = {"error": f"Failed to get usage stats: {str(e)}"}
        
        return result
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error getting container resources: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@Tool(
    name="update_container_resources",
    description="Update resource limits for a container",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'cpu_shares': {
                'type': 'integer',
                'minimum': 2,
                'maximum': 262144,
                'default': None,
                'description': 'CPU shares (relative weight)'
            },
            'cpu_priority': {
                'type': 'string',
                'enum': [e.value for e in CpuPriority],
                'default': None,
                'description': 'CPU priority (overrides cpu_shares)'
            },
            'cpu_quota': {
                'type': 'integer',
                'minimum': 1000,
                'default': None,
                'description': 'Microseconds of CPU time the container gets per cpu_period'
            },
            'cpu_period': {
                'type': 'integer',
                'minimum': 1000,
                'default': 100000,
                'description': 'The length of a CPU period in microseconds'
            },
            'cpus': {
                'type': 'string',
                'default': None,
                'description': 'CPUs in which to allow execution (0-3, 0,1)'
            },
            'memory': {
                'type': 'string',
                'default': None,
                'description': 'Memory limit (e.g., 512m, 2g)'
            },
            'memory_reservation': {
                'type': 'string',
                'default': None,
                'description': 'Memory soft limit (e.g., 512m, 2g)'
            },
            'memory_swappiness': {
                'type': 'integer',
                'minimum': 0,
                'maximum': 100,
                'default': None,
                'description': 'Tune container memory swappiness (0-100)'
            },
            'blkio_weight': {
                'type': 'integer',
                'minimum': 10,
                'maximum': 1000,
                'default': None,
                'description': 'Block IO weight (relative weight), between 10 and 1000'
            },
            'device_weights': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string'},
                        'weight': {'type': 'integer', 'minimum': 10, 'maximum': 1000}
                    },
                    'required': ['path', 'weight']
                },
                'default': [],
                'description': 'Per-device block IO weight'
            },
            'device_read_bps': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string'},
                        'rate': {'type': 'string'}
                    },
                    'required': ['path', 'rate']
                },
                'default': [],
                'description': 'Limit read rate (bytes per second) from a device (e.g., [{"path": "/dev/sda", "rate": "1mb"}])'
            },
            'device_write_bps': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string'},
                        'rate': {'type': 'string'}
                    },
                    'required': ['path', 'rate']
                },
                'default': [],
                'description': 'Limit write rate (bytes per second) to a device'
            },
            'device_read_iops': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string'},
                        'rate': {'type': 'integer', 'minimum': 1}
                    },
                    'required': ['path', 'rate']
                },
                'default': [],
                'description': 'Limit read rate (IO per second) from a device'
            },
            'device_write_iops': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string'},
                        'rate': {'type': 'integer', 'minimum': 1}
                    },
                    'required': ['path', 'rate']
                },
                'default': [],
                'description': 'Limit write rate (IO per second) to a device'
            },
            'pids_limit': {
                'type': 'integer',
                'minimum': -1,
                'default': None,
                'description': 'Limit the number of processes (set -1 for unlimited)'
            },
            'restart_policy': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'enum': ['no', 'on-failure', 'always', 'unless-stopped'],
                        'default': 'no'
                    },
                    'maximum_retry_count': {
                        'type': 'integer',
                        'minimum': 0,
                        'default': 0
                    }
                },
                'default': None,
                'description': 'Restart policy to apply when a container exits'
            }
        },
        'required': ['container_id']
    }
)
async def update_container_resources(
    container_id: str,
    cpu_shares: Optional[int] = None,
    cpu_priority: Optional[str] = None,
    cpu_quota: Optional[int] = None,
    cpu_period: int = 100000,
    cpus: Optional[str] = None,
    memory: Optional[str] = None,
    memory_reservation: Optional[str] = None,
    memory_swappiness: Optional[int] = None,
    blkio_weight: Optional[int] = None,
    device_weights: List[Dict[str, Union[str, int]]] = [],
    device_read_bps: List[Dict[str, str]] = [],
    device_write_bps: List[Dict[str, str]] = [],
    device_read_iops: List[Dict[str, Union[str, int]]] = [],
    device_write_iops: List[Dict[str, Union[str, int]]] = [],
    pids_limit: Optional[int] = None,
    restart_policy: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update resource limits for a container.
    
    This function updates the resource limits for a running container. It can be used
    to adjust CPU, memory, I/O, and other resource constraints.
    
    Args:
        container_id: ID or name of the container
        cpu_shares: CPU shares (relative weight)
        cpu_priority: CPU priority (overrides cpu_shares if set)
        cpu_quota: Microseconds of CPU time the container gets per cpu_period
        cpu_period: The length of a CPU period in microseconds
        cpus: CPUs in which to allow execution (0-3, 0,1)
        memory: Memory limit (e.g., 512m, 2g)
        memory_reservation: Memory soft limit (e.g., 512m, 2g)
        memory_swappiness: Tune container memory swappiness (0-100)
        blkio_weight: Block IO weight (relative weight), between 10 and 1000
        device_weights: Per-device block IO weight
        device_read_bps: Limit read rate (bytes per second) from a device
        device_write_bps: Limit write rate (bytes per second) to a device
        device_read_iops: Limit read rate (IO per second) from a device
        device_write_iops: Limit write rate (IO per second) to a device
        pids_limit: Limit the number of processes (set -1 for unlimited)
        restart_policy: Restart policy to apply when a container exits
        
    Returns:
        Dictionary with the update results
        
    Example:
        >>> await update_container_resources(
        ...     container_id="my-container",
        ...     cpu_priority="high",
        ...     memory="1g",
        ...     memory_reservation="512m",
        ...     blkio_weight=500,
        ...     device_weights=[{"path": "/dev/sda", "weight": 200}],
        ...     pids_limit=1024
        ... )
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "updates": [
                {
                    "resource_type": "cpu_shares",
                    "previous_value": 1024,
                    "new_value": 768,
                    "container_id": "a1b2c3d4e5f6"
                },
                {
                    "resource_type": "memory",
                    "previous_value": 536870912,
                    "new_value": 1073741824,
                    "container_id": "a1b2c3d4e5f6"
                }
            ]
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "status": "error",
                "container_id": container_id,
                "error": f"Container not found: {container_id}"
            }
        
        # Get current container info
        container.reload()
        host_config = container.attrs['HostConfig']
        
        # Prepare update parameters
        update_kwargs = {}
        results = []
        
        # Handle CPU shares based on priority if specified
        if cpu_priority is not None:
            priority_map = {
                CpuPriority.LOW: 256,
                CpuPriority.NORMAL: 512,
                CpuPriority.HIGH: 768,
                CpuPriority.CRITICAL: 1024
            }
            new_cpu_shares = priority_map.get(CpuPriority(cpu_priority))
            if new_cpu_shares != host_config.get('CpuShares'):
                update_kwargs['cpu_shares'] = new_cpu_shares
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="cpu_shares",
                    previous_value=host_config.get('CpuShares'),
                    new_value=new_cpu_shares
                ).dict())
        elif cpu_shares is not None and cpu_shares != host_config.get('CpuShares'):
            update_kwargs['cpu_shares'] = cpu_shares
            results.append(UpdateResourceResult(
                container_id=container.id,
                resource_type="cpu_shares",
                previous_value=host_config.get('CpuShares'),
                new_value=cpu_shares
            ).dict())
        
        # Handle CPU quota/period
        if cpu_quota is not None and cpu_quota != host_config.get('CpuQuota'):
            update_kwargs['cpu_quota'] = cpu_quota
            results.append(UpdateResourceResult(
                container_id=container.id,
                resource_type="cpu_quota",
                previous_value=host_config.get('CpuQuota'),
                new_value=cpu_quota
            ).dict())
        
        if cpu_period is not None and cpu_period != host_config.get('CpuPeriod'):
            update_kwargs['cpu_period'] = cpu_period
            results.append(UpdateResourceResult(
                container_id=container.id,
                resource_type="cpu_period",
                previous_value=host_config.get('CpuPeriod'),
                new_value=cpu_period
            ).dict())
        
        # Handle CPU set
        if cpus is not None and cpus != host_config.get('CpusetCpus'):
            update_kwargs['cpuset_cpus'] = cpus
            results.append(UpdateResourceResult(
                container_id=container.id,
                resource_type="cpuset_cpus",
                previous_value=host_config.get('CpusetCpus'),
                new_value=cpus
            ).dict())
        
        # Handle memory limits
        if memory is not None:
            # Convert memory string to bytes
            memory_bytes = _parse_memory_string(memory)
            if memory_bytes != host_config.get('Memory'):
                update_kwargs['mem_limit'] = memory_bytes
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="memory_limit",
                    previous_value=host_config.get('Memory'),
                    new_value=memory_bytes
                ).dict())
        
        if memory_reservation is not None:
            memory_reservation_bytes = _parse_memory_string(memory_reservation)
            if memory_reservation_bytes != host_config.get('MemoryReservation'):
                update_kwargs['mem_reservation'] = memory_reservation_bytes
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="memory_reservation",
                    previous_value=host_config.get('MemoryReservation'),
                    new_value=memory_reservation_bytes
                ).dict())
        
        if memory_swappiness is not None and memory_swappiness != host_config.get('MemorySwappiness'):
            update_kwargs['mem_swappiness'] = memory_swappiness
            results.append(UpdateResourceResult(
                container_id=container.id,
                resource_type="memory_swappiness",
                previous_value=host_config.get('MemorySwappiness'),
                new_value=memory_swappiness
            ).dict())
        
        # Handle Block I/O
        if blkio_weight is not None and blkio_weight != host_config.get('BlkioWeight'):
            update_kwargs['blkio_weight'] = blkio_weight
            results.append(UpdateResourceResult(
                container_id=container.id,
                resource_type="blkio_weight",
                previous_value=host_config.get('BlkioWeight'),
                new_value=blkio_weight
            ).dict())
        
        # Handle device weights
        if device_weights:
            weight_devices = [
                {"Path": str(w['path']), "Weight": int(w['weight'])}
                for w in device_weights
            ]
            if weight_devices != host_config.get('BlkioWeightDevice'):
                update_kwargs['blkio_weight_device'] = weight_devices
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="blkio_weight_device",
                    previous_value=host_config.get('BlkioWeightDevice'),
                    new_value=weight_devices
                ).dict())
        
        # Handle device read/write bps/iops
        def _parse_device_rates(rate_str: str) -> int:
            """Convert rate string (e.g., '1mb') to bytes per second."""
            rate_str = rate_str.lower().strip()
            if rate_str.endswith('k'):
                return int(rate_str[:-1]) * 1024
            elif rate_str.endswith('m'):
                return int(rate_str[:-1]) * 1024 * 1024
            elif rate_str.endswith('g'):
                return int(rate_str[:-1]) * 1024 * 1024 * 1024
            elif rate_str.endswith('kb'):
                return int(rate_str[:-2]) * 1000
            elif rate_str.endswith('mb'):
                return int(rate_str[:-2]) * 1000 * 1000
            elif rate_str.endswith('gb'):
                return int(rate_str[:-2]) * 1000 * 1000 * 1000
            elif rate_str.endswith('kib'):
                return int(rate_str[:-3]) * 1024
            elif rate_str.endswith('mib'):
                return int(rate_str[:-3]) * 1024 * 1024
            elif rate_str.endswith('gib'):
                return int(rate_str[:-3]) * 1024 * 1024 * 1024
            else:
                return int(rate_str)
        
        if device_read_bps:
            read_bps = [
                {"Path": str(d['path']), "Rate": _parse_device_rates(str(d['rate']))}
                for d in device_read_bps
            ]
            if read_bps != host_config.get('BlkioDeviceReadBps'):
                update_kwargs['device_read_bps'] = read_bps
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="device_read_bps",
                    previous_value=host_config.get('BlkioDeviceReadBps'),
                    new_value=read_bps
                ).dict())
        
        if device_write_bps:
            write_bps = [
                {"Path": str(d['path']), "Rate": _parse_device_rates(str(d['rate']))}
                for d in device_write_bps
            ]
            if write_bps != host_config.get('BlkioDeviceWriteBps'):
                update_kwargs['device_write_bps'] = write_bps
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="device_write_bps",
                    previous_value=host_config.get('BlkioDeviceWriteBps'),
                    new_value=write_bps
                ).dict())
        
        if device_read_iops:
            read_iops = [
                {"Path": str(d['path']), "Rate": int(d['rate'])}
                for d in device_read_iops
            ]
            if read_iops != host_config.get('BlkioDeviceReadIOps'):
                update_kwargs['device_read_iops'] = read_iops
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="device_read_iops",
                    previous_value=host_config.get('BlkioDeviceReadIOps'),
                    new_value=read_iops
                ).dict())
        
        if device_write_iops:
            write_iops = [
                {"Path": str(d['path']), "Rate": int(d['rate'])}
                for d in device_write_iops
            ]
            if write_iops != host_config.get('BlkioDeviceWriteIOps'):
                update_kwargs['device_write_iops'] = write_iops
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="device_write_iops",
                    previous_value=host_config.get('BlkioDeviceWriteIOps'),
                    new_value=write_iops
                ).dict())
        
        # Handle PIDs limit
        if pids_limit is not None and pids_limit != host_config.get('PidsLimit'):
            update_kwargs['pids_limit'] = pids_limit
            results.append(UpdateResourceResult(
                container_id=container.id,
                resource_type="pids_limit",
                previous_value=host_config.get('PidsLimit'),
                new_value=pids_limit
            ).dict())
        
        # Handle restart policy
        if restart_policy is not None:
            policy = {
                'Name': restart_policy.get('name', 'no'),
                'MaximumRetryCount': restart_policy.get('maximum_retry_count', 0)
            }
            if policy != host_config.get('RestartPolicy'):
                update_kwargs['restart_policy'] = policy
                results.append(UpdateResourceResult(
                    container_id=container.id,
                    resource_type="restart_policy",
                    previous_value=host_config.get('RestartPolicy'),
                    new_value=policy
                ).dict())
        
        # Apply updates if there are any
        if update_kwargs:
            container.update(**update_kwargs)
            
            # Verify the updates were applied
            container.reload()
            updated_config = container.attrs['HostConfig']
            
            # Verify each update was applied correctly
            for result in results:
                resource_type = result['resource_type']
                expected_value = result['new_value']
                
                # Map our parameter names to the actual Docker API field names
                field_map = {
                    'cpu_shares': 'CpuShares',
                    'cpu_quota': 'CpuQuota',
                    'cpu_period': 'CpuPeriod',
                    'cpuset_cpus': 'CpusetCpus',
                    'memory_limit': 'Memory',
                    'memory_reservation': 'MemoryReservation',
                    'memory_swappiness': 'MemorySwappiness',
                    'blkio_weight': 'BlkioWeight',
                    'blkio_weight_device': 'BlkioWeightDevice',
                    'device_read_bps': 'BlkioDeviceReadBps',
                    'device_write_bps': 'BlkioDeviceWriteBps',
                    'device_read_iops': 'BlkioDeviceReadIOps',
                    'device_write_iops': 'BlkioDeviceWriteIOps',
                    'pids_limit': 'PidsLimit',
                    'restart_policy': 'RestartPolicy'
                }
                
                field_name = field_map.get(resource_type, resource_type)
                actual_value = updated_config.get(field_name)
                
                # For lists/dicts, we need to do a deep comparison
                if isinstance(expected_value, (list, dict)) and isinstance(actual_value, (list, dict)):
                    if expected_value != actual_value:
                        result['warnings'].append(
                            f"Update may not have been applied correctly. "
                            f"Expected {expected_value}, got {actual_value}"
                        )
                elif expected_value != actual_value:
                    result['warnings'].append(
                        f"Update may not have been applied correctly. "
                        f"Expected {expected_value}, got {actual_value}"
                    )
            
            return {
                "status": "success",
                "container_id": container.id,
                "updates": results,
                "message": f"Updated {len(results)} resource(s)"
            }
        else:
            return {
                "status": "success",
                "container_id": container.id,
                "message": "No changes were needed",
                "updates": []
            }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error updating container resources: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

def _parse_memory_string(memory_str: str) -> int:
    """
    Parse a memory string with unit suffix to bytes.
    
    Args:
        memory_str: Memory string with optional unit (e.g., '512m', '2g')
        
    Returns:
        Memory value in bytes
        
    Raises:
        ValueError: If the string format is invalid
    """
    memory_str = memory_str.strip().lower()
    
    if not memory_str:
        raise ValueError("Empty memory string")
    
    # Handle numeric values without units (assume bytes)
    if memory_str.isdigit():
        return int(memory_str)
    
    # Handle values with units
    units = {
        'b': 1,
        'k': 1024,
        'm': 1024 * 1024,
        'g': 1024 * 1024 * 1024,
        't': 1024 * 1024 * 1024 * 1024,
        'kb': 1000,
        'mb': 1000 * 1000,
        'gb': 1000 * 1000 * 1000,
        'tb': 1000 * 1000 * 1000 * 1000,
        'kib': 1024,
        'mib': 1024 * 1024,
        'gib': 1024 * 1024 * 1024,
        'tib': 1024 * 1024 * 1024 * 1024
    }
    
    # Find the unit at the end of the string
    unit = ''
    for u in sorted(units.keys(), key=len, reverse=True):
        if memory_str.endswith(u):
            unit = u
            break
    
    if not unit:
        # No valid unit found, assume bytes
        try:
            return int(memory_str)
        except ValueError:
            raise ValueError(f"Invalid memory format: {memory_str}")
    
    # Extract the numeric part
    num_str = memory_str[:-len(unit)]
    try:
        num = float(num_str)
    except ValueError:
        raise ValueError(f"Invalid numeric value in memory string: {num_str}")
    
    # Calculate bytes
    return int(num * units[unit])

@Tool(
    name="reset_container_resources",
    description="Reset all resource limits for a container to their default values",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            }
        },
        'required': ['container_id']
    }
)
async def reset_container_resources(container_id: str) -> Dict[str, Any]:
    """
    Reset all resource limits for a container to their default values.
    
    This function resets all resource limits (CPU, memory, I/O, etc.) for a container
    to their default values, effectively removing any custom resource constraints.
    
    Args:
        container_id: ID or name of the container
        
    Returns:
        Dictionary with the reset results
        
    Example:
        >>> await reset_container_resources("my-container")
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "message": "All resource limits reset to defaults"
        }
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "status": "error",
                "container_id": container_id,
                "error": f"Container not found: {container_id}"
            }
        
        # Get current container info
        container.reload()
        
        # Prepare reset parameters - setting to None/empty will reset to defaults
        reset_params = {
            'cpu_shares': 0,  # 0 means use the default
            'cpu_quota': -1,  # -1 means no quota
            'cpu_period': 100000,  # Default period
            'cpuset_cpus': '',  # Empty means all CPUs
            'mem_limit': 0,  # 0 means no limit
            'mem_reservation': 0,  # 0 means no reservation
            'mem_swappiness': -1,  # -1 means use the default
            'blkio_weight': 0,  # 0 means use the default
            'blkio_weight_device': [],  # Empty means no device-specific weights
            'device_read_bps': [],  # Empty means no read limits
            'device_write_bps': [],  # Empty means no write limits
            'device_read_iops': [],  # Empty means no read IOPS limits
            'device_write_iops': [],  # Empty means no write IOPS limits
            'pids_limit': 0,  # 0 means no limit
            'restart_policy': {'Name': 'no'}  # Default restart policy
        }
        
        # Apply the reset
        container.update(**reset_params)
        
        return {
            "status": "success",
            "container_id": container.id,
            "message": "All resource limits reset to defaults"
        }
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error resetting container resources: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}
