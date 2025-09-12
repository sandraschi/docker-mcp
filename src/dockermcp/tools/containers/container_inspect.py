"""
Container inspection tool for Docker MCP.

This module provides detailed inspection of Docker containers including 
configuration, state, and resource usage statistics with comprehensive
error handling and logging. It follows FastMCP 2.12+ standards.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

import docker
from docker.errors import DockerException, APIError, NotFound
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, ConfigDict

from dockermcp.logging_config import logger

# Constants
DEFAULT_LOG_TAIL = 100
MAX_LOG_LINES = 1000

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
            return (cpu_delta / system_delta) * 100.0 * len(cpu_usage.get('percpu_usage', [1]))
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    
    return 0.0

def _calculate_memory_usage(stats: Dict[str, Any]) -> Dict[str, int]:
    """Calculate memory usage from Docker stats."""
    try:
        memory_stats = stats.get('memory_stats', {})
        usage = memory_stats.get('usage', 0)
        limit = memory_stats.get('limit', 1)  # Avoid division by zero
        
        return {
            'usage': usage,
            'limit': limit,
            'percent': (usage / limit) * 100.0 if limit > 0 else 0.0
        }
    except (KeyError, TypeError, ZeroDivisionError):
        return {'usage': 0, 'limit': 0, 'percent': 0.0}

def _get_network_io(stats: Dict[str, Any]) -> Dict[str, int]:
    """Extract network I/O statistics from container stats."""
    try:
        networks = stats.get('networks', {})
        rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
        tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())
        return {'rx_bytes': rx_bytes, 'tx_bytes': tx_bytes}
    except (AttributeError, TypeError):
        return {'rx_bytes': 0, 'tx_bytes': 0}

@Tool(
    name="inspect_container",
    description="Inspect a Docker container and return detailed information",
    parameters={
        'type': 'object',
        'properties': {
            'container_id': {
                'type': 'string',
                'description': 'ID or name of the container to inspect'
            },
            'include_stats': {
                'type': 'boolean',
                'default': False,
                'description': 'Include resource usage statistics'
            },
            'include_logs': {
                'type': 'boolean',
                'default': False,
                'description': 'Include container logs'
            },
            'log_tail': {
                'type': 'integer',
                'minimum': 1,
                'maximum': MAX_LOG_LINES,
                'default': DEFAULT_LOG_TAIL,
                'description': f'Number of log lines to include (1-{MAX_LOG_LINES})'
            }
        },
        'required': ['container_id']
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
            
    Example:
        >>> await inspect_container(
        ...     container_id="my-container",
        ...     include_stats=True,
        ...     include_logs=True,
        ...     log_tail=50
        ... )
        {
            "id": "a1b2c3d4e5f6",
            "name": "my-container",
            "status": "running",
            "image": "nginx:latest",
            "state": {
                "status": "running",
                "running": True,
                "paused": False,
                "restarting": False,
                "started_at": "2023-01-01T12:00:00Z"
            },
            "stats": {
                "cpu_percent": 12.5,
                "memory_usage": 1024,
                "memory_limit": 2048,
                "memory_percent": 50.0,
                "network_io": {
                    "rx_bytes": 1024,
                    "tx_bytes": 2048
                }
            },
            "logs": ["log line 1", "log line 2"],
            "network_settings": {
                "ip_address": "172.17.0.2",
                "ports": {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}
            },
            "mounts": [
                {
                    "source": "/host/path",
                    "destination": "/container/path",
                    "mode": "ro"
                }
            ],
            "environment": {"ENV_VAR": "value"}
        }
    """
    try:
        # Validate log_tail
        log_tail = max(1, min(log_tail, MAX_LOG_LINES))
        
        # Initialize Docker client
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {
                "error": f"Container not found: {container_id}",
                "status": "error"
            }
        
        # Basic container info
        container_attrs = container.attrs
        result = {
            "id": container_attrs["Id"],
            "name": container_attrs["Name"].lstrip("/"),
            "image": container_attrs["Config"]["Image"],
            "status": container_attrs["State"]["Status"],
            "state": {
                "status": container_attrs["State"]["Status"],
                "running": container_attrs["State"].get("Running", False),
                "paused": container_attrs["State"].get("Paused", False),
                "restarting": container_attrs["State"].get("Restarting", False),
                "oom_killed": container_attrs["State"].get("OOMKilled", False),
                "dead": container_attrs["State"].get("Dead", False),
                "pid": container_attrs["State"].get("Pid", 0),
                "exit_code": container_attrs["State"].get("ExitCode", 0),
                "error": container_attrs["State"].get("Error", ""),
                "started_at": container_attrs["State"].get("StartedAt", ""),
                "finished_at": container_attrs["State"].get("FinishedAt", "")
            },
            "created": container_attrs["Created"],
            "path": container_attrs["Path"],
            "args": container_attrs["Args"],
            "config": {
                "hostname": container_attrs["Config"].get("Hostname", ""),
                "domainname": container_attrs["Config"].get("Domainname", ""),
                "user": container_attrs["Config"].get("User", ""),
                "working_dir": container_attrs["Config"].get("WorkingDir", ""),
                "tty": container_attrs["Config"].get("Tty", False),
                "open_stdin": container_attrs["Config"].get("OpenStdin", False),
                "attach_stdin": container_attrs["Config"].get("AttachStdin", False),
                "attach_stdout": container_attrs["Config"].get("AttachStdout", False),
                "attach_stderr": container_attrs["Config"].get("AttachStderr", False)
            },
            "host_config": {
                "network_mode": container_attrs["HostConfig"].get("NetworkMode", "default"),
                "restart_policy": container_attrs["HostConfig"].get("RestartPolicy", {}),
                "auto_remove": container_attrs["HostConfig"].get("AutoRemove", False)
            },
            "network_settings": {
                "ip_address": container_attrs["NetworkSettings"].get("IPAddress", ""),
                "ip_prefix_len": container_attrs["NetworkSettings"].get("IPPrefixLen", 0),
                "gateway": container_attrs["NetworkSettings"].get("Gateway", ""),
                "mac_address": container_attrs["NetworkSettings"].get("MacAddress", ""),
                "networks": container_attrs["NetworkSettings"].get("Networks", {})
            },
            "mounts": [
                {
                    "source": mount["Source"],
                    "destination": mount["Destination"],
                    "mode": mount.get("Mode", ""),
                    "type": mount["Type"],
                    "rw": mount.get("RW", False)
                }
                for mount in container_attrs.get("Mounts", [])
            ],
            "environment": {
                env.split("=", 1)[0]: env.split("=", 1)[1] 
                for env in container_attrs["Config"].get("Env", [])
                if "=" in env
            },
            "labels": container_attrs["Config"].get("Labels", {})
        }
        
        # Add port mappings
        if "Ports" in container_attrs["NetworkSettings"]:
            result["ports"] = container_attrs["NetworkSettings"]["Ports"]
        
        # Include resource usage statistics if requested
        if include_stats:
            try:
                stats = container.stats(stream=False)
                result["stats"] = {
                    "cpu_percent": _calculate_cpu_percent(stats),
                    "memory_usage": _calculate_memory_usage(stats),
                    "network_io": _get_network_io(stats)
                }
            except Exception as e:
                logger.warning(f"Failed to get container stats: {str(e)}")
                result["stats"] = {"error": str(e)}
        
        # Include logs if requested
        if include_logs:
            try:
                logs = container.logs(
                    tail=log_tail,
                    stdout=True,
                    stderr=True,
                    timestamps=False,
                    follow=False
                )
                if logs:
                    result["logs"] = logs.decode("utf-8", errors="replace").splitlines()
            except Exception as e:
                logger.warning(f"Failed to get container logs: {str(e)}")
                result["logs"] = [f"Failed to retrieve logs: {str(e)}"]
        
        return result
        
    except APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"error": "Docker daemon not available", "status": "error"}
        
    except Exception as e:
        error_msg = f"Unexpected error inspecting container: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg, "status": "error"}
