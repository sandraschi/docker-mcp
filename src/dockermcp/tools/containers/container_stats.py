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
from typing import Any, Dict, List, Optional, AsyncGenerator, Union, Annotated

import docker
from docker.errors import DockerException, APIError, NotFound
from pydantic import BaseModel, Field, ConfigDict, HttpUrl, AnyUrl, field_validator
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from dockermcp.logging_config import logger

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

class ContainerStatsParams(BaseModel):
    """Parameters for the get_container_stats tool."""
    model_config = ConfigDict(
        title="ContainerStatsParams",
        json_schema_extra={
            "description": "Parameters for retrieving container statistics"
        }
    )
    container_id: Annotated[str, Field(
        ...,
        description="ID or name of the container",
        min_length=1,
        max_length=128,
        example="a1b2c3d4e5f6"
    )]
    stream: Annotated[bool, Field(
        False,
        description="Stream stats in real-time (like docker stats)"
    )] = False
    interval: Annotated[float, Field(
        1.0,
        ge=0.1,
        le=60.0,
        description="Interval in seconds between stats updates (when streaming)"
    )] = 1.0
    timeout: Annotated[int, Field(
        60,
        ge=1,
        le=3600,
        description="Maximum time in seconds to collect stats (when streaming)"
    )] = 60
    one_shot: Annotated[bool, Field(
        False,
        description="Get a single stats snapshot (overrides stream if both are True)"
    )] = False

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
    error: Optional[str] = Field(None, description="Error message if stats collection failed")


class ContainerStatsResponse(BaseModel):
    """Response model for container statistics."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            AsyncGenerator: lambda v: "<async_generator>"
        },
        json_schema_extra={
            "example": {
                "container_id": "a1b2c3d4e5f6",
                "name": "my-container",
                "timestamp": "2023-01-01T12:00:00Z",
                "cpu": {
                    "total_usage": 1000000000,
                    "system_cpu_usage": 5000000000,
                    "online_cpus": 4,
                    "usage_in_kernelmode": 200000000,
                    "usage_in_usermode": 300000000,
                    "throttling_periods": 0,
                    "throttled_time": 0,
                    "percent_usage": 25.5
                },
                "memory": {
                    "usage": 1024000000,
                    "max_usage": 2048000000,
                    "limit": 4294967296,
                    "percent_usage": 50.0,
                    "cache": 512000000,
                    "rss": 512000000,
                    "swap": 0
                },
                "network": {
                    "eth0": {
                        "rx_bytes": 1024,
                        "rx_packets": 10,
                        "rx_errors": 0,
                        "rx_dropped": 0,
                        "tx_bytes": 2048,
                        "tx_packets": 20,
                        "tx_errors": 0,
                        "tx_dropped": 0
                    }
                },
                "block_io": {
                    "read_bytes": 1024000,
                    "write_bytes": 512000,
                    "read_ops": 100,
                    "write_ops": 50
                },
                "pids": 5
            }
        }
    )
    
    container_id: str = Field(..., description="ID of the container")
    name: str = Field(..., description="Name of the container")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the stats snapshot")
    cpu: Dict[str, Any] = Field(..., description="CPU usage statistics")
    memory: Dict[str, Any] = Field(..., description="Memory usage statistics")
    network: Dict[str, Any] = Field(..., description="Network statistics by interface")
    block_io: Dict[str, Any] = Field(..., description="Block I/O statistics")
    pids: int = Field(..., description="Number of processes")
    error: Optional[str] = Field(None, description="Error message if stats collection failed")

@mcp.tool
async def get_container_stats(params: ContainerStatsParams) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """Get container statistics including CPU, memory, network, and I/O metrics.
    
    This tool provides detailed resource usage metrics for a container, similar to
    the 'docker stats' command. It can return either a single snapshot of statistics
    or stream them in real-time.
    
    Example:
        ```python
        # Get a single stats snapshot
        from dockermcp.tools.containers.container_stats import ContainerStatsParams
        
        params = ContainerStatsParams(
            container_id="my-container",
            one_shot=True
        )
        result = await get_container_stats(params)
        
        # Stream stats in real-time
        stream_params = ContainerStatsParams(
            container_id="my-container",
            stream=True,
            interval=1.0,
            timeout=30
        )
        async for stats in await get_container_stats(stream_params):
            print(stats)
        ```
    
    Args:
        params: ContainerStatsParams object containing all parameters for the stats request
            - container_id: ID or name of the container
            - stream: If True, stream stats in real-time (like docker stats)
            - interval: Seconds between stats updates (when streaming)
            - timeout: Maximum seconds to collect stats (when streaming)
            - one_shot: If True, get a single stats snapshot (overrides stream if both are True)
    
    Returns:
        Union[ToolResponse[Dict[str, Any]], AsyncGenerator[ContainerStatsResponse, None]]:
            - If one_shot=True: ToolResponse with stats data
            - If stream=True: AsyncGenerator yielding ContainerStatsResponse objects
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the container
        try:
            container = client.containers.get(params.container_id)
        except NotFound as e:
            error_msg = f"Container not found: {params.container_id}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "error": str(e)
            }
        
        # Handle one-shot request
        if params.one_shot or not params.stream:
            # Get a single stats snapshot
            container = client.containers.get(params.container_id)
            stats = container.stats(stream=False, decode=True)
            parsed_stats = _parse_stats(container, stats)
            return {
                "status": "success",
                "message": "Container stats retrieved successfully",
                "data": parsed_stats.model_dump()
            }
        
        # Handle streaming request
        try:
            return _stream_stats(container, params.interval, params.timeout)
        except Exception as e:
            error_msg = f"Failed to start stats stream: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "message": "Failed to start stats stream",
                "error": error_msg,
                "data": {"container_id": container.id}
            }
            
    except Exception as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": "Failed to get container stats",
            "error": error_msg
        }

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
        ContainerStatsResponse with container statistics
        
    Example:
        >>> container = docker.from_env().containers.get("my-container")
        >>> async for stats in _stream_stats(container, interval=1.0, timeout=30):
        ...     print(stats)
    """
    start_time = time.time()
    previous_cpu = None
    previous_system = None
    
    try:
        # Get initial stats
        stats = container.stats(stream=False, decode=True)
        parsed_stats = _parse_stats(container, stats, previous_cpu, previous_system)
        previous_cpu = stats['cpu_stats']['cpu_usage']['total_usage']
        previous_system = stats['cpu_stats']['system_cpu_usage']
        
        yield ContainerStatsResponse(**parsed_stats.model_dump())
        
        # Continue streaming until timeout
        while (time.time() - start_time) < timeout:
            await asyncio.sleep(interval)
            
            try:
                stats = container.stats(stream=False, decode=True)
                parsed_stats = _parse_stats(container, stats, previous_cpu, previous_system)
                previous_cpu = stats['cpu_stats']['cpu_usage']['total_usage']
                previous_system = stats['cpu_stats']['system_cpu_usage']
                
                yield ContainerStatsResponse(**parsed_stats.model_dump())
                
            except (DockerException, APIError) as e:
                error_msg = f"Failed to get container stats: {str(e)}"
                logger.error(error_msg, exc_info=True)
                yield ContainerStatsResponse(
                    container_id=container.id,
                    name=container.name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    cpu={},
                    memory={},
                    network={},
                    block_io={},
                    pids=0,
                    error=error_msg
                )
                break
                
    except Exception as e:
        error_msg = f"Unexpected error in stats stream: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield ContainerStatsResponse(
            container_id=container.id,
            name=container.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu={},
            memory={},
            network={},
            block_io={},
            pids=0,
            error=error_msg
        )

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
        
    Example:
        >>> container = docker.from_env().containers.get("my-container")
        >>> stats = container.stats(stream=False, decode=True)
        >>> parsed_stats = _parse_stats(container, stats)
    """
    try:
        # Extract CPU stats with safe dictionary access
        cpu_stats = stats.get('cpu_stats', {}) or {}
        precpu_stats = stats.get('precpu_stats', {}) or {}
        cpu_usage = cpu_stats.get('cpu_usage', {}) or {}
        precpu_usage = precpu_stats.get('cpu_usage', {}) or {}
        
        # Calculate CPU usage percentage with safety checks
        cpu_delta = (cpu_usage.get('total_usage') or 0) - (precpu_usage.get('total_usage') or 0)
        system_delta = (cpu_stats.get('system_cpu_usage') or 0) - (precpu_stats.get('system_cpu_usage') or 0)
        
        online_cpus = cpu_stats.get('online_cpus', 0) or 1  # Default to 1 to avoid division by zero
        cpu_percent = 0.0
        
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
        
        # Extract memory stats with safe access
        memory_stats = stats.get('memory_stats', {}) or {}
        memory_stats_stats = memory_stats.get('stats', {}) or {}
        
        memory_usage = memory_stats.get('usage', 0) or 0
        memory_limit = memory_stats.get('limit', 1)  # Avoid division by zero
        memory_percent = (memory_usage / memory_limit * 100.0) if memory_limit > 0 else 0.0
        
        # Extract network stats with safe access
        network_stats = {}
        networks = stats.get('networks', {}) or {}
        
        for if_name, if_stats in networks.items():
            if if_stats:  # Only process non-None interface stats
                network_stats[if_name] = NetworkStats(
                    rx_bytes=if_stats.get('rx_bytes', 0) or 0,
                    rx_packets=if_stats.get('rx_packets', 0) or 0,
                    rx_errors=if_stats.get('rx_errors', 0) or 0,
                    rx_dropped=if_stats.get('rx_dropped', 0) or 0,
                    tx_bytes=if_stats.get('tx_bytes', 0) or 0,
                    tx_packets=if_stats.get('tx_packets', 0) or 0,
                    tx_errors=if_stats.get('tx_errors', 0) or 0,
                    tx_dropped=if_stats.get('tx_dropped', 0) or 0
                )
        
        # Extract block I/O stats with safe access
        blkio_stats = stats.get('blkio_stats', {}) or {}
        io_service_bytes = blkio_stats.get('io_service_bytes_recursive', []) or []
        io_serviced = blkio_stats.get('io_serviced_recursive', []) or []
        
        read_bytes = sum(
            io.get('value', 0) for io in io_service_bytes 
            if isinstance(io, dict) and io.get('op') == 'Read'
        )
        
        write_bytes = sum(
            io.get('value', 0) for io in io_service_bytes 
            if isinstance(io, dict) and io.get('op') == 'Write'
        )
        
        read_ops = sum(
            io.get('value', 0) for io in io_serviced
            if isinstance(io, dict) and io.get('op') == 'Read'
        )
        
        write_ops = sum(
            io.get('value', 0) for io in io_serviced
            if isinstance(io, dict) and io.get('op') == 'Write'
        )
        
        # Get throttling data with safe access
        throttling_data = cpu_stats.get('throttling_data', {}) or {}
        
        # Create and return the structured model
        return ContainerStats(
            container_id=container.id,
            name=container.name,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            cpu=CPUStats(
                total_usage=cpu_usage.get('total_usage', 0) or 0,
                system_cpu_usage=cpu_stats.get('system_cpu_usage', 0) or 0,
                online_cpus=online_cpus,
                usage_in_kernelmode=cpu_usage.get('usage_in_kernelmode', 0) or 0,
                usage_in_usermode=cpu_usage.get('usage_in_usermode', 0) or 0,
                throttling_periods=throttling_data.get('periods', 0) or 0,
                throttled_time=throttling_data.get('throttled_time', 0) or 0,
                percent_usage=round(float(cpu_percent), 2)
            ),
            memory=MemoryStats(
                usage=memory_usage,
                max_usage=memory_stats.get('max_usage', 0) or 0,
                limit=memory_limit,
                percent_usage=round(float(memory_percent), 2),
                cache=memory_stats_stats.get('cache', 0) or 0,
                rss=memory_stats_stats.get('rss', 0) or 0,
                swap=memory_stats_stats.get('swap', 0) or 0
            ),
            network=network_stats,
            block_io=BlockIOStats(
                read_bytes=read_bytes,
                write_bytes=write_bytes,
                read_ops=read_ops,
                write_ops=write_ops
            ),
            pids=stats.get('pids_stats', {}).get('current', 0) or 0
        )
        
    except Exception as e:
        logger.error(f"Error parsing container stats: {str(e)}", exc_info=True)
        # Return a minimal error response that matches the ContainerStats model
        return ContainerStats(
            container_id=container.id,
            name=container.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu=CPUStats(
                total_usage=0,
                system_cpu_usage=0,
                online_cpus=0,
                usage_in_kernelmode=0,
                usage_in_usermode=0,
                throttling_periods=0,
                throttled_time=0,
                percent_usage=0.0
            ),
            memory=MemoryStats(
                usage=0,
                max_usage=0,
                limit=0,
                percent_usage=0.0,
                cache=0,
                rss=0,
                swap=0
            ),
            network={},
            block_io=BlockIOStats(
                read_bytes=0,
                write_bytes=0,
                read_ops=0,
                write_ops=0
            ),
            pids=0,
            error=f"Error parsing stats: {str(e)}"
        )
