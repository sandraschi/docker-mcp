"""
Container statistics for Docker MCP.

This module provides tools for monitoring container resource usage metrics
like CPU, memory, network I/O, and block I/O. It follows FastMCP 2.12+ standards
for tool registration and error handling.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

import docker
from docker.errors import DockerException, APIError, NotFound
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, ConfigDict

from dockermcp.logging_config import logger

class CPUStats(BaseModel):
    """CPU usage statistics."""
    total_usage: float = Field(..., description="Total CPU usage")
    system_cpu_usage: float = Field(..., description="System CPU usage")
    online_cpus: int = Field(..., description="Number of online CPUs")
    usage_in_kernelmode: float = Field(..., description="Time spent in kernel mode (nanoseconds)")
    usage_in_usermode: float = Field(..., description="Time spent in user mode (nanoseconds)")
    throttling_periods: int = Field(..., description="Number of throttling periods")
    throttled_time: float = Field(..., description="Total throttled time (nanoseconds)")
    percent_usage: float = Field(..., description="CPU usage as a percentage")

class MemoryStats(BaseModel):
    """Memory usage statistics."""
    usage: int = Field(..., description="Current memory usage in bytes")
    max_usage: int = Field(..., description="Maximum memory usage in bytes")
    limit: int = Field(..., description="Memory limit in bytes")
    percent_usage: float = Field(..., description="Memory usage as a percentage of limit")
    cache: int = Field(..., description="Page cache memory usage in bytes")
    rss: int = Field(..., description="Resident Set Size in bytes")
    swap: int = Field(..., description="Swap usage in bytes")

class NetworkStats(BaseModel):
    """Network I/O statistics."""
    rx_bytes: int = Field(..., description="Bytes received")
    rx_packets: int = Field(..., description="Packets received")
    rx_errors: int = Field(..., description="Receive errors")
    rx_dropped: int = Field(..., description="Receive packets dropped")
    tx_bytes: int = Field(..., description="Bytes transmitted")
    tx_packets: int = Field(..., description="Packets transmitted")
    tx_errors: int = Field(..., description="Transmit errors")
    tx_dropped: int = Field(..., description="Transmit packets dropped")

class BlockIOStats(BaseModel):
    """Block I/O statistics."""
    read_bytes: int = Field(..., description="Bytes read")
    write_bytes: int = Field(..., description="Bytes written")
    read_ops: int = Field(..., description="Read operations")
    write_ops: int = Field(..., description="Write operations")

class ContainerStats(BaseModel):
    """Container statistics snapshot."""
    container_id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the stats snapshot")
    cpu: CPUStats = Field(..., description="CPU usage statistics")
    memory: MemoryStats = Field(..., description="Memory usage statistics")
    network: Dict[str, NetworkStats] = Field(..., description="Network statistics by interface")
    block_io: BlockIOStats = Field(..., description="Block I/O statistics")
    pids: int = Field(..., description="Number of processes")

@Tool(
    name="get_container_stats",
    description="Get resource usage statistics for a container",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container'
            },
            'stream': {
                'type': 'boolean',
                'default': False,
                'description': 'Stream stats in real-time (like docker stats)'
            },
            'interval': {
                'type': 'number',
                'minimum': 0.1,
                'maximum': 60,
                'default': 1.0,
                'description': 'Interval in seconds between stats updates (when streaming)'
            },
            'timeout': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 3600,
                'default': 60,
                'description': 'Maximum time in seconds to collect stats (when streaming)'
            },
            'one_shot': {
                'type': 'boolean',
                'default': False,
                'description': 'Get a single stats snapshot (overrides stream=true if both are set)'
            }
        },
        'required': ['container_id']
    }
)
async def get_container_stats(
    container_id: str,
    stream: bool = False,
    interval: float = 1.0,
    timeout: int = 60,
    one_shot: bool = False
) -> Dict[str, Any]:
    """
    Get container statistics including CPU, memory, network, and I/O metrics.
    
    This tool provides detailed resource usage metrics for a container, similar to
    the 'docker stats' command. It can return either a single snapshot of statistics
    or stream them in real-time.
    
    Args:
        container_id: ID or name of the container
        stream: Stream stats in real-time (like docker stats)
        interval: Interval in seconds between stats updates (when streaming)
        timeout: Maximum time in seconds to collect stats (when streaming)
        one_shot: Get a single stats snapshot (overrides stream if both are True)
        
    Returns:
        Dictionary with container statistics or a stream of statistics
        
    Example:
        # Get a single stats snapshot
        >>> await get_container_stats(
        ...     container_id="my-container",
        ...     one_shot=True
        ... )
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "stats": {
                "container_id": "a1b2c3d4e5f6",
                "name": "my-container",
                "timestamp": "2023-01-01T12:00:00Z",
                "cpu": {
                    "total_usage": 1234567890,
                    "system_cpu_usage": 9876543210,
                    "online_cpus": 4,
                    "usage_in_kernelmode": 12345678,
                    "usage_in_usermode": 98765432,
                    "throttling_periods": 0,
                    "throttled_time": 0,
                    "percent_usage": 12.34
                },
                "memory": {
                    "usage": 536870912,
                    "max_usage": 1073741824,
                    "limit": 2147483648,
                    "percent_usage": 50.0,
                    "cache": 134217728,
                    "rss": 402653184,
                    "swap": 0
                },
                "network": {
                    "eth0": {
                        "rx_bytes": 123456,
                        "rx_packets": 123,
                        "rx_errors": 0,
                        "rx_dropped": 0,
                        "tx_bytes": 654321,
                        "tx_packets": 321,
                        "tx_errors": 0,
                        "tx_dropped": 0
                    }
                },
                "block_io": {
                    "read_bytes": 1048576,
                    "write_bytes": 524288,
                    "read_ops": 128,
                    "write_ops": 64
                },
                "pids": 5
            }
        }
        
        # Stream stats in real-time
        >>> await get_container_stats(
        ...     container_id="my-container",
        ...     stream=True,
        ...     interval=2.0,
        ...     timeout=30
        ... )
        {
            "status": "success",
            "container_id": "a1b2c3d4e5f6",
            "stream": <async_generator object _stream_stats>
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
        
        # If one_shot is True, override stream setting
        if one_shot:
            stream = False
        
        if stream:
            # For streaming stats, return a generator
            return {
                "status": "success",
                "container_id": container_id,
                "stream": _stream_stats(container, interval, timeout)
            }
        else:
            # For one-shot stats, get a single stats point
            stats = container.stats(stream=False, decode=True)
            stats_model = _parse_stats(container, stats)
            
            return {
                "status": "success",
                "container_id": container_id,
                "stats": stats_model.model_dump()
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
        error_msg = f"Unexpected error getting container stats: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

async def _stream_stats(
    container: docker.models.containers.Container,
    interval: float,
    timeout: int
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream container statistics in real-time.
    
    Args:
        container: Docker container object
        interval: Time in seconds between stats updates
        timeout: Maximum time in seconds to stream stats
        
    Yields:
        Dictionary with container statistics
    """
    start_time = time.time()
    previous_cpu = None
    previous_system = None
    
    try:
        # Get initial stats to calculate CPU percentages
        stats = container.stats(stream=False, decode=True)
        previous_cpu = stats['cpu_stats']['cpu_usage']['total_usage']
        previous_system = stats['cpu_stats']['system_cpu_usage']
        
        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                logger.info(f"Stats stream timed out after {timeout} seconds")
                break
            
            # Get stats
            stats = container.stats(stream=False, decode=True)
            
            # Parse and yield the stats
            stats_model = _parse_stats(container, stats, previous_cpu, previous_system)
            yield stats_model.model_dump()
            
            # Update previous values for next iteration
            previous_cpu = stats['cpu_stats']['cpu_usage']['total_usage']
            previous_system = stats['cpu_stats']['system_cpu_usage']
            
            # Wait for the next interval
            await asyncio.sleep(interval)
            
    except Exception as e:
        logger.error(f"Error in stats stream: {str(e)}")
        yield {
            "container_id": container.id,
            "name": container.name,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "error": f"Error in stats stream: {str(e)}"
        }

def _parse_stats(
    container: docker.models.containers.Container,
    stats: Dict[str, Any],
    previous_cpu: Optional[int] = None,
    previous_system: Optional[int] = None
) -> ContainerStats:
    """
    Parse raw Docker stats into a structured model.
    
    Args:
        container: Docker container object
        stats: Raw stats dictionary from Docker API
        previous_cpu: Previous CPU usage for delta calculation
        previous_system: Previous system CPU usage for delta calculation
        
    Returns:
        Structured ContainerStats model
    """
    # Calculate CPU percentage if we have previous values
    cpu_percent = 0.0
    if previous_cpu is not None and previous_system is not None:
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - previous_cpu
        system_delta = stats['cpu_stats']['system_cpu_usage'] - previous_system
        
        if system_delta > 0 and cpu_delta > 0:
            online_cpus = stats['cpu_stats'].get('online_cpus', 1)
            cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
    
    # Parse CPU stats
    cpu_stats = CPUStats(
        total_usage=stats['cpu_stats']['cpu_usage']['total_usage'],
        system_cpu_usage=stats['cpu_stats'].get('system_cpu_usage', 0),
        online_cpus=stats['cpu_stats'].get('online_cpus', 1),
        usage_in_kernelmode=stats['cpu_stats']['cpu_usage'].get('usage_in_kernelmode', 0),
        usage_in_usermode=stats['cpu_stats']['cpu_usage'].get('usage_in_usermode', 0),
        throttling_periods=stats['cpu_stats'].get('throttling_data', {}).get('periods', 0),
        throttled_time=stats['cpu_stats'].get('throttling_data', {}).get('throttled_time', 0),
        percent_usage=round(cpu_percent, 2)
    )
    
    # Parse memory stats
    memory_stats = stats.get('memory_stats', {})
    memory_limit = memory_stats.get('limit', 1)  # Avoid division by zero
    memory_usage = memory_stats.get('usage', 0)
    memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0
    
    memory_stats_model = MemoryStats(
        usage=memory_usage,
        max_usage=memory_stats.get('max_usage', 0),
        limit=memory_limit,
        percent_usage=round(memory_percent, 2),
        cache=memory_stats.get('stats', {}).get('cache', 0),
        rss=memory_stats.get('stats', {}).get('rss', 0),
        swap=memory_stats.get('stats', {}).get('swap', 0)
    )
    
    # Parse network stats
    network_stats = {}
    for iface, net_data in stats.get('networks', {}).items():
        network_stats[iface] = NetworkStats(
            rx_bytes=net_data.get('rx_bytes', 0),
            rx_packets=net_data.get('rx_packets', 0),
            rx_errors=net_data.get('rx_errors', 0),
            rx_dropped=net_data.get('rx_dropped', 0),
            tx_bytes=net_data.get('tx_bytes', 0),
            tx_packets=net_data.get('tx_packets', 0),
            tx_errors=net_data.get('tx_errors', 0),
            tx_dropped=net_data.get('tx_dropped', 0)
        )
    
    # Parse block I/O stats
    io_stats = stats.get('blkio_stats', {})
    read_bytes = 0
    write_bytes = 0
    read_ops = 0
    write_ops = 0
    
    for io_entry in io_stats.get('io_service_bytes_recursive', []):
        if io_entry['op'] == 'Read':
            read_bytes += io_entry['value']
        elif io_entry['op'] == 'Write':
            write_bytes += io_entry['value']
            
    for io_entry in io_stats.get('io_serviced_recursive', []):
        if io_entry['op'] == 'Read':
            read_ops += io_entry['value']
        elif io_entry['op'] == 'Write':
            write_ops += io_entry['value']
    
    block_io_stats = BlockIOStats(
        read_bytes=read_bytes,
        write_bytes=write_bytes,
        read_ops=read_ops,
        write_ops=write_ops
    )
    
    # Create and return the full stats model
    return ContainerStats(
        container_id=container.id,
        name=container.name,
        timestamp=datetime.utcnow().isoformat() + 'Z',
        cpu=cpu_stats,
        memory=memory_stats_model,
        network=network_stats,
        block_io=block_io_stats,
        pids=stats.get('pids_stats', {}).get('current', 0)
    )
