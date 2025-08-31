"""
Container inspection tool for Docker MCP.

Provides detailed inspection of Docker containers including configuration, state, and resources.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import docker
from docker.models.containers import Container

class ContainerInspectRequest(BaseModel):
    """Request model for container inspection."""
    container_id: str = Field(
        ...,
        description="ID or name of the container to inspect"
    )
    show_stats: bool = Field(
        default=False,
        description="Include live resource usage statistics"
    )
    show_logs: bool = Field(
        default=False,
        description="Include recent logs"
    )
    log_tail: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of log lines to include if show_logs is True"
    )

class ContainerInspectResponse(BaseModel):
    """Response model for container inspection."""
    id: str
    name: str
    status: str
    state: Dict[str, Any]
    config: Dict[str, Any]
    network_settings: Dict[str, Any]
    mounts: list[Dict[str, Any]]
    created: datetime
    image: str
    command: str
    labels: Dict[str, str]
    ports: Dict[str, Any]
    environment: Dict[str, str]
    stats: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None
    error: Optional[str] = None

@Tool(
    name="inspect_container",
    description="Inspect a Docker container and return detailed information",
    parameters={
        "type": "object",
        "properties": {
            "container_id": {
                "type": "string",
                "description": "ID or name of the container to inspect"
            },
            "show_stats": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include live resource usage statistics"
            },
            "show_logs": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include recent logs"
            },
            "log_tail": {
                "type": "integer",
                "default": 100,
                "minimum": 1,
                "maximum": 1000,
                "description": "Number of log lines to include if show_logs is True"
            }
        },
        "required": ["container_id"]
    },
    returns={
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "status": {"type": "string"},
            "state": {"type": "object"},
            "config": {"type": "object"},
            "network_settings": {"type": "object"},
            "mounts": {"type": "array", "items": {"type": "object"}},
            "created": {"type": "string", "format": "date-time"},
            "image": {"type": "string"},
            "command": {"type": "string"},
            "labels": {"type": "object"},
            "ports": {"type": "object"},
            "environment": {"type": "object"},
            "stats": {"type": "object"},
            "logs": {"type": "string"},
            "error": {"type": "string"}
        },
        "required": ["id", "name", "status", "state", "config", "network_settings", "mounts", "created", "image", "command", "labels", "ports", "environment"]
    },
    examples=[
        {
            "name": "Basic container inspection",
            "input": {"container_id": "my-container"},
            "output": {
                "id": "a1b2c3d4e5f6",
                "name": "my-container",
                "status": "running",
                "state": {"Status": "running"},
                "config": {"Image": "nginx:latest"},
                "network_settings": {"IPAddress": "172.17.0.2"},
                "mounts": [],
                "created": "2023-01-01T12:00:00Z",
                "image": "sha256:abc123...",
                "command": "nginx -g 'daemon off;'",
                "labels": {"maintainer": "NGINX Docker Maintainers"},
                "ports": {"80/tcp": [{"HostPort": "8080", "HostIp": "0.0.0.0"}]},
                "environment": {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
            }
        }
    ]
)
async def inspect_container(
    container_id: str,
    show_stats: bool = False,
    show_logs: bool = False,
    log_tail: int = 100
) -> Dict[str, Any]:
    client = docker.from_env()
    
    try:
        container = client.containers.get(container_id)
        
        # Get basic container info
        container.reload()  # Ensure we have the latest state
        container_attrs = container.attrs
        
        # Prepare response
        response = {
            'id': container_attrs['Id'],
            'name': container_attrs['Name'].lstrip('/'),
            'status': container_attrs['State']['Status'],
            'state': container_attrs['State'],
            'config': {
                'image': container_attrs['Config']['Image'],
                'cmd': container_attrs['Config']['Cmd'],
                'entrypoint': container_attrs['Config']['Entrypoint'],
                'working_dir': container_attrs['Config']['WorkingDir'],
                'user': container_attrs['Config']['User'],
                'hostname': container_attrs['Config']['Hostname'],
                'domainname': container_attrs['Config'].get('Domainname', ''),
                'env': {
                    env.split('=', 1)[0]: env.split('=', 1)[1] 
                    for env in container_attrs['Config']['Env']
                    if '=' in env
                },
                'labels': container_attrs['Config']['Labels'],
                'healthcheck': container_attrs['Config'].get('Healthcheck'),
                'stop_signal': container_attrs['Config'].get('StopSignal'),
                'stop_timeout': container_attrs['Config'].get('StopTimeout'),
            },
            'network_settings': {
                'networks': container_attrs['NetworkSettings']['Networks'],
                'ip_address': container_attrs['NetworkSettings']['IPAddress'],
                'ports': container_attrs['NetworkSettings']['Ports'],
            },
            'mounts': [{
                'type': mount.get('Type'),
                'source': mount.get('Source'),
                'destination': mount.get('Destination'),
                'mode': mount.get('Mode'),
                'rw': mount.get('RW', False),
                'propagation': mount.get('Propagation'),
            } for mount in container_attrs['Mounts']],
            'created': container_attrs['Created'],
            'image': container_attrs['Image'],
            'command': ' '.join(container_attrs['Args']) if container_attrs['Args'] else '',
            'labels': container_attrs['Config']['Labels'],
            'ports': container_attrs['NetworkSettings']['Ports'],
            'environment': {
                env.split('=', 1)[0]: env.split('=', 1)[1] 
                for env in container_attrs['Config']['Env']
                if '=' in env
            },
        }
        
        # Add stats if requested
        if show_stats:
            try:
                stats = container.stats(stream=False)
                response['stats'] = {
                    'cpu_percent': _calculate_cpu_percent(stats),
                    'memory_usage': stats['memory_stats'].get('usage', 0),
                    'memory_limit': stats['memory_stats'].get('limit', 0),
                    'memory_percent': _calculate_memory_percent(stats),
                    'network_io': stats['networks'],
                    'block_io': stats['blkio_stats'],
                    'pids': stats['pids_stats']['current'] if 'pids_stats' in stats else 0,
                    'read': stats['read'],
                }
            except Exception as e:
                response['error'] = f"Failed to get stats: {str(e)}"
        
        # Add logs if requested
        if show_logs:
            try:
                logs = container.logs(tail=log_tail).decode('utf-8')
                response['logs'] = logs
            except Exception as e:
                response['error'] = f"Failed to get logs: {str(e)}"
        
        return response
        
    except docker.errors.NotFound:
        return {'error': f"Container {container_id} not found"}
    except docker.errors.APIError as e:
        return {'error': f"Docker API error: {str(e)}"}
    except Exception as e:
        return {'error': f"Unexpected error: {str(e)}"}

def _calculate_cpu_percent(stats: Dict[str, Any]) -> float:
    """Calculate CPU usage percentage from Docker stats."""
    cpu_delta = (
        stats['cpu_stats']['cpu_usage']['total_usage'] - 
        stats['precpu_stats']['cpu_usage']['total_usage']
    )
    system_delta = (
        stats['cpu_stats']['system_cpu_usage'] - 
        stats['precpu_stats']['system_cpu_usage']
    )
    
    if system_delta > 0 and cpu_delta > 0:
        cpu_count = stats['cpu_stats']['online_cpus']
        return (cpu_delta / system_delta) * cpu_count * 100.0
    return 0.0

def _calculate_memory_percent(stats: Dict[str, Any]) -> float:
    """Calculate memory usage percentage from Docker stats."""
    memory_stats = stats.get('memory_stats', {})
    if not memory_stats.get('limit'):
        return 0.0
    
    used_memory = memory_stats.get('usage', 0) - memory_stats.get('stats', {}).get('cache', 0)
    return (used_memory / memory_stats['limit']) * 100.0
