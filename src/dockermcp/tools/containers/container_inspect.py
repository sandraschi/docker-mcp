"""
Container inspection tool for Docker MCP.

This module provides detailed inspection of Docker containers including 
configuration, state, and resource usage statistics with comprehensive
error handling and logging. It is compatible with FastMCP 2.12+ and follows
the project's coding standards.
"""
from __future__ import annotations

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, TypeVar
from datetime import datetime

# Pydantic models
from pydantic import BaseModel, Field, ConfigDict

# Docker SDK
import docker
from docker.errors import APIError, NotFound, DockerException
from docker.models.containers import Container

# FastMCP imports
from fastmcp.tools import tool, tool

# Import custom exceptions
from .container_models import ContainerError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Constants
MAX_LOG_LINES = 1000
DEFAULT_LOG_TAIL = 100

def _calculate_cpu_percent(stats: Dict[str, Any]) -> float:
    """Calculate CPU usage percentage from Docker stats."""
    try:
        cpu_stats = stats.get('cpu_stats', {})
        precpu_stats = stats.get('precpu_stats', {})
        
        cpu_usage = cpu_stats.get('cpu_usage', {})
        precpu_usage = precpu_stats.get('cpu_usage', {})
        
        cpu_delta = cpu_usage.get('total_usage', 0) - precpu_usage.get('total_usage', 0)
        system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu_stats.get('system_cpu_usage', 0)
        
        if system_delta > 0 and cpu_delta > 0:
            cpu_count = cpu_stats.get('online_cpus') or len(cpu_usage.get('percpu_usage') or [1])
            return min(100.0, round((cpu_delta / system_delta) * cpu_count * 100.0, 2))
    except Exception as e:
        logger.warning(f"Failed to calculate CPU percentage: {e}")
    return 0.0

def _calculate_memory_usage(stats: Dict[str, Any]) -> Dict[str, float]:
    """Calculate memory usage from Docker stats."""
    try:
        memory_stats = stats.get('memory_stats', {})
        usage = memory_stats.get('usage', 0)
        limit = memory_stats.get('limit', 0)
        
        return {
            'usage_mb': round(usage / (1024 * 1024), 2),
            'limit_mb': round(limit / (1024 * 1024), 2) if limit > 0 else 0.0,
            'percent': round((usage / limit * 100), 2) if limit > 0 else 0.0
        }
    except Exception as e:
        logger.warning(f"Failed to calculate memory usage: {e}")
        return {'usage_mb': 0.0, 'limit_mb': 0.0, 'percent': 0.0}

def _get_network_io(stats: Dict[str, Any]) -> Dict[str, float]:
    """Extract network I/O statistics from container stats."""
    try:
        networks = stats.get('networks', {})
        rx_bytes = sum(n.get('rx_bytes', 0) for n in networks.values())
        tx_bytes = sum(n.get('tx_bytes', 0) for n in networks.values())
        return {'rx_bytes': rx_bytes, 'tx_bytes': tx_bytes}
    except Exception as e:
        logger.warning(f"Failed to get network stats: {e}")
        return {'rx_bytes': 0, 'tx_bytes': 0}

@tool(
    name="inspect_container",
    description=(
        "Inspect a Docker container and return detailed information including "
        "configuration, state, resource usage, and logs."
    ),
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container to inspect'
            },
            'include_stats': {
                'type': 'boolean',
                'description': 'Whether to include resource usage statistics',
                'default': False
            },
            'include_logs': {
                'type': 'boolean',
                'description': 'Whether to include container logs',
                'default': False
            },
            'log_tail': {
                'type': 'integer',
                'description': 'Number of log lines to include (1-1000)',
                'minimum': 1,
                'maximum': MAX_LOG_LINES,
                'default': DEFAULT_LOG_TAIL
            }
        },
        'required': ['container_id']
    },
    output_schema={
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'container_id': {'type': 'string'},
            'name': {'type': 'string'},
            'status': {'type': 'string'},
            'image': {'type': 'string'},
            'created': {'type': 'string', 'format': 'date-time'},
            'state': {'type': 'object'},
            'config': {'type': 'object'},
            'network_settings': {'type': 'object'},
            'mounts': {'type': 'array', 'items': {'type': 'object'}},
            'stats': {'$ref': '#/definitions/ContainerStats'},
            'logs': {'type': 'array', 'items': {'type': 'string'}},
            'error': {'type': 'string'}
        },
        'definitions': {
            'ContainerStats': {
                'type': 'object',
                'properties': {
                    'cpu_percent': {'type': 'number'},
                    'memory_usage': {'type': 'number'},
                    'memory_limit': {'type': 'number'},
                    'memory_percent': {'type': 'number'},
                    'network_io': {
                        'type': 'object',
                        'properties': {
                            'rx_bytes': {'type': 'number'},
                            'tx_bytes': {'type': 'number'}
                        }
                    },
                    'block_io': {'type': 'object'}
                }
            }
        },
        'required': ['success', 'container_id', 'name', 'status', 'image', 'created']
    }
)
async def inspect_container(
    container_id: str,
    include_stats: bool = False,
    include_logs: bool = False,
    log_tail: int = DEFAULT_LOG_TAIL
) -> Dict[str, Any]:
    """
    Inspect a Docker container and return detailed information.
    
    This function provides a comprehensive view of a container's configuration,
    state, and resource usage. It includes robust error handling and supports
    both synchronous and asynchronous operations.
    
    Args:
        container_id: ID or name of the container to inspect
        include_stats: Whether to include resource usage statistics
        include_logs: Whether to include container logs
        log_tail: Number of log lines to include (1-1000)
        
    Returns:
        Dictionary with container information including:
            - Basic info (ID, name, status, image, etc.)
            - Detailed state and configuration
            - Resource usage statistics (if requested)
            - Recent logs (if requested)
            - Network settings and port mappings
            - Volume mounts and environment variables
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get container
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                'success': False,
                'error': f'Container {container_id} not found',
                'container_id': container_id
            }
        except APIError as e:
            return {
                'success': False,
                'error': f'Docker API error: {str(e)}',
                'container_id': container_id
            }
        
        # Get basic container info
        container.reload()
        attrs = container.attrs
        
        # Prepare response
        response = {
            'success': True,
            'container_id': container.id,
            'name': container.name.lstrip('/'),
            'status': container.status,
            'image': container.image.tags[0] if container.image.tags else container.image.id,
            'created': attrs.get('Created'),
            'state': attrs.get('State', {}),
            'config': attrs.get('Config', {}),
            'network_settings': attrs.get('NetworkSettings', {}),
            'mounts': attrs.get('Mounts', []),
        }
        
        # Get stats if requested
        if include_stats:
            try:
                stats = container.stats(stream=False)
                memory = _calculate_memory_usage(stats)
                
                response['stats'] = {
                    'cpu_percent': _calculate_cpu_percent(stats),
                    'memory_usage': memory['usage_mb'],
                    'memory_limit': memory['limit_mb'],
                    'memory_percent': memory['percent'],
                    'network_io': _get_network_io(stats.get('networks', {})),
                    'block_io': stats.get('blkio_stats', {})
                }
            except Exception as e:
                logger.warning(f"Failed to get container stats: {e}")
                response['stats'] = None
        
        # Get logs if requested
        if include_logs:
            try:
                log_tail = max(1, min(MAX_LOG_LINES, int(log_tail)))
                logs = container.logs(
                    tail=log_tail,
                    timestamps=True,
                    stdout=True,
                    stderr=True
                )
                response['logs'] = logs.decode('utf-8', errors='replace').split('\n')
            except Exception as e:
                logger.warning(f"Failed to get container logs: {e}")
                response['logs'] = None
        
        return response
        
    except Exception as e:
        logger.error(f"Error inspecting container {container_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'Failed to inspect container: {str(e)}',
            'container_id': container_id
        }

def get_tools():
    """
    Get all tools defined in this module for registration with FastMCP 2.12+.
    
    Returns:
        List of tool functions to register with FastMCP
    """
    return [inspect_container]
