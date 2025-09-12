"""
System management tools for Docker MCP.

This module provides FastMCP 2.11.3 compatible tools for managing Docker system.
"""
from dockermcp.logging_config import logger, configure_logging
configure_logging()

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, AsyncGenerator

# FastMCP 2.12+ import pattern
from fastmcp.tools.tool import Tool, tool
from fastmcp.exceptions import ToolException

# Set tool availability flag
TOOL_AVAILABLE = True
logger.debug("FastMCP Tool imported from fastmcp.tools")

from typing import Optional, Dict, Any
import logging
import docker
from datetime import datetime
from pydantic import ValidationError

from dockermcp.core.system import SystemManager
from dockermcp.utils.helpers import format_size, parse_size, human_readable_to_bytes
from dockermcp.tools.system.system_models import (
    SystemInfo, SystemResponse, SystemPruneResponse, SystemDiskUsageResponse,
    SystemInfoResponse, SystemPingResponse, SystemAuthRequest, SystemAuthResponse,
    SystemPruneRequest, SystemEventsRequest, SystemEventsResponse, SystemDataUsageResponse,
    SystemResourceType, DiskUsage, MemoryUsage, CpuUsage, NetworkUsage, SystemUpdateChannel,
    SystemComponent, SystemHealthStatus, PruneFilter, EventFilter
)

# Configure logging
from dockermcp.logging_config import logger

# Get a child logger for this module
logger = logger.getChild('system_tools')

# Initialize system manager
import docker
system_mgr = SystemManager(docker_client=docker.from_env())

async def _check_daemon_health() -> Dict[str, Any]:
    """Check Docker daemon health and accessibility using graceful connection handling."""
    try:
        # Try to get the Docker client
        try:
            client = docker.from_env()
            # Test basic API connectivity
            client.ping()
            daemon_status = 'healthy'
            
            # Test more intensive operation to verify full functionality
            try:
                client.containers.list(limit=1)
            except Exception as e:
                daemon_status = 'degraded'
                logger.warning(f"Docker daemon is accessible but may be degraded: {str(e)}")
            
            return {
                'status': daemon_status,
                'api_version': client.api.version()['ApiVersion'],
                'docker_version': client.version()['Version']
            }
            
        except Exception as e:
            # If we can't even get a client, return unavailable status
            logger.error(f"Docker client initialization failed: {str(e)}")
            raise
            
    except Exception as e:
        # Handle any unexpected errors
        logger.error(f"Docker daemon check failed: {str(e)}")
        return {
            'status': 'unavailable',
            'error': str(e),
            'recovery_steps': [
                '1. Check if Docker service is running: `systemctl status docker`',
                '2. Try restarting Docker: `sudo systemctl restart docker`',
                '3. Check logs: `journalctl -u docker.service --no-pager -n 50`',
                '4. If Docker is unresponsive, consider: `sudo systemctl stop docker` then `sudo systemctl start docker`'
            ]
        }

@Tool(
    name="help",
    description="List all available commands and their descriptions",
    parameters={
        'type': 'object',
        'properties': {
            'category': {
                'type': 'string',
                'description': 'Filter tools by category (containers, images, networks, volumes, system, monitoring)',
                'enum': ['containers', 'images', 'networks', 'volumes', 'system', 'monitoring', None],
                'default': None
            }
        }
    },
    output_schema={
        'success': True,
        'message': 'Available commands retrieved successfully',
        'commands': {},
        'categories': []
    }
)
@Tool(
    name="status",
    description="Get system status and resource usage information with Docker daemon health check",
    parameters={
        'type': 'object',
        'properties': {
            'detailed': {
                'type': 'boolean',
                'description': 'Include detailed resource usage information',
                'default': False
            },
            'include_containers': {
                'type': 'boolean',
                'description': 'Include container status in the response',
                'default': True
            },
            'include_system': {
                'type': 'boolean',
                'description': 'Include system resource usage information',
                'default': True
            },
            'check_grafana': {
                'type': 'boolean',
                'description': 'Check for running Grafana monitoring',
                'default': True
            },
            'check_daemon': {
                'type': 'boolean',
                'description': 'Perform Docker daemon health check',
                'default': True
            }
        }
    },
    output_schema={
        'success': True,
        'message': 'System status retrieved successfully',
        'timestamp': '',
        'status': {}
    }
)
async def status(
    detailed: bool = False,
    include_containers: bool = True,
    include_system: bool = True,
    check_grafana: bool = True,
    check_daemon: bool = True
) -> Dict[str, Any]:
    """
    Get current status of the Docker system including daemon health, resource usage, and monitoring.
    
    Args:
        detailed: Include detailed resource usage information
        include_containers: Include container status in the response
        include_system: Include system resource usage information
        check_grafana: Check Grafana monitoring status
        check_daemon: Perform Docker daemon health check
        
    Returns:
        Dictionary with system status information including Docker daemon health
    """
    try:
        result = {
            'success': True,
            'message': 'System status retrieved successfully',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'status': {}
        }
        
        if include_system:
            # Get system-wide information
            sys_info = await system_info(detailed=detailed)
            if sys_info.get('success'):
                result['status']['system'] = sys_info
            
            # Get disk usage
            disk_usage = await system_disk_usage(verbose=detailed)
            if disk_usage.get('success'):
                result['status']['disk_usage'] = disk_usage
        
        if include_containers:
            # Get container status
            try:
                from dockermcp.tools.containers.container_tools import list_containers
                containers = await list_containers(all=True, size=detailed)
                if containers.get('success'):
                    result['status']['containers'] = containers
            except Exception as e:
                logger.warning(f"Could not fetch container status: {str(e)}")
        
        # Add Docker daemon health status
        if check_daemon:
            result['status']['daemon'] = await _check_daemon_health()
            
            # If daemon is down, skip other checks that would fail
            if result['status']['daemon'].get('status') != 'healthy':
                result['message'] = 'Docker daemon is not healthy - some checks were skipped'
                result['status']['health'] = 'degraded'
                return result
                
        # Add system health status
        result['status']['health'] = await _check_health()
        
        # Check Grafana status if requested
        if check_grafana:
            try:
                from dockermcp.utils.grafana_utils import GrafanaManager
                grafana_mgr = GrafanaManager(docker_client=docker.from_env())
                grafana_status = await grafana_mgr.is_grafana_running()
                result['status']['grafana'] = grafana_status
                
                if grafana_status.get('status') != 'running' and detailed:
                    result['status']['grafana_setup_guide'] = {
                        'message': 'Grafana is not running. To set up Grafana for Docker monitoring:',
                        'steps': [
                            '1. Run: await setup_grafana() to start a Grafana container',
                            f'2. Access Grafana at http://localhost:13000',
                            '3. Log in with admin/admin (change password on first login)',
                            '4. Set up data sources:',
                            '   - Prometheus: http://prometheus:9090 (if using Docker monitoring stack)',
                            '   - Node Exporter: For host metrics',
                            '   - cAdvisor: For container metrics',
                            '5. Import recommended dashboards:',
                            '   - Docker Host Metrics (ID: 10619)',
                            '   - Docker Container & Host (ID: 10620)',
                            '   - cAdvisor (ID: 193)'
                        ],
                        'note': 'For detailed monitoring setup, run: await help(category="monitoring")'
                    }
                    
            except Exception as e:
                logger.warning(f"Could not check Grafana status: {str(e)}")
                result['status']['grafana'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return result
        
    except Exception as e:
        return handle_error(e, "retrieving system status")


async def _check_health() -> Dict[str, Any]:
    """Check the health of the Docker system."""
    try:
        # Check if Docker daemon is responding
        ping = await system_ping()
        if not ping.get('success'):
            return {
                'status': 'unhealthy',
                'message': 'Docker daemon not responding',
                'details': ping
            }
        
        # Check disk space
        disk = await system_disk_usage()
        if disk.get('success') and 'data' in disk:
            total_space = disk['data'].get('total_space', 0)
            used_space = disk['data'].get('used_space', 0)
            if total_space > 0 and (used_space / total_space) > 0.9:  # 90% full
                return {
                    'status': 'degraded',
                    'message': 'Disk space is critically low',
                    'details': disk
                }
        
        return {
            'status': 'healthy',
            'message': 'All systems operational',
            'details': {
                'docker_version': ping.get('data', {}).get('version'),
                'api_version': ping.get('data', {}).get('api_version')
            }
        }
        
    except Exception as e:
        return {
            'status': 'unknown',
            'message': f'Health check failed: {str(e)}',
            'error': str(e)
        }


@Tool(
    name="help",
    description="List all available commands and their descriptions",
    parameters={
        'type': 'object',
        'properties': {
            'category': {
                'type': 'string',
                'description': 'Filter tools by category (containers, images, networks, volumes, system)',
                'enum': ['containers', 'images', 'networks', 'volumes', 'system', None],
                'default': None
            }
        }
    },
    output_schema={
        'success': True,
        'message': 'Available commands retrieved successfully',
        'commands': {},
        'categories': []
    }
)
async def help(category: Optional[str] = None) -> Dict[str, Any]:
    """
    List all available Docker MCP commands with their descriptions.
    
    Args:
        category: Optional category to filter commands (containers, images, networks, volumes, system)
        
    Returns:
        Dictionary with available commands grouped by category
    """
    try:
        # In FastMCP 2.12+, get_tools_metadata() doesn't exist
        # Provide a manual catalog of available commands instead
        commands = {
            'containers': [
                {'name': 'list_containers', 'description': 'List all containers on the Docker host'},
                {'name': 'create_container', 'description': 'Create a new container'},
                {'name': 'start_container', 'description': 'Start a container'},
                {'name': 'stop_container', 'description': 'Stop a running container'},
                {'name': 'restart_container', 'description': 'Restart a container'},
                {'name': 'remove_container', 'description': 'Remove a container'},
                {'name': 'inspect_container', 'description': 'Get detailed information about a container'},
                {'name': 'container_logs', 'description': 'Get logs from a container'}
            ],
            'images': [
                {'name': 'list_images', 'description': 'List all images on the Docker host'},
                {'name': 'pull_image', 'description': 'Pull an image from a registry'},
                {'name': 'build_image', 'description': 'Build an image from a Dockerfile'},
                {'name': 'remove_image', 'description': 'Remove an image'},
                {'name': 'tag_image', 'description': 'Add a tag to an image'},
                {'name': 'inspect_image', 'description': 'Get detailed information about an image'}
            ],
            'networks': [
                {'name': 'list_networks', 'description': 'List all networks'},
                {'name': 'create_network', 'description': 'Create a new network'},
                {'name': 'remove_network', 'description': 'Remove a network'},
                {'name': 'inspect_network', 'description': 'Get detailed information about a network'}
            ],
            'volumes': [
                {'name': 'list_volumes', 'description': 'List all volumes'},
                {'name': 'create_volume', 'description': 'Create a new volume'},
                {'name': 'remove_volume', 'description': 'Remove a volume'},
                {'name': 'inspect_volume', 'description': 'Get detailed information about a volume'}
            ],
            'system': [
                {'name': 'system_info', 'description': 'Get system-wide information'},
                {'name': 'system_disk_usage', 'description': 'Get disk usage information'},
                {'name': 'system_prune', 'description': 'Remove unused resources'},
                {'name': 'system_ping', 'description': 'Test connectivity to Docker daemon'},
                {'name': 'status', 'description': 'Get overall system status and health'}
            ],
            'compose': [
                {'name': 'compose_up', 'description': 'Create and start containers from Compose file'},
                {'name': 'compose_down', 'description': 'Stop and remove containers from Compose file'},
                {'name': 'compose_build', 'description': 'Build services defined in Compose file'},
                {'name': 'compose_logs', 'description': 'View logs from Compose services'},
                {'name': 'compose_ps', 'description': 'List containers in Compose project'}
            ]
        }
        
        # Filter by category if requested
        if category and category in commands:
            commands = {category: commands[category]}
        
        return {
            'success': True,
            'message': 'Available commands retrieved successfully',
            'commands': commands,
            'categories': list(commands.keys())
        }
        
    except Exception as e:
        return handle_error(e, "retrieving help information")


@Tool(
    name="setup_grafana",
    description="Set up Grafana for home automation monitoring on port 13000",
    parameters={
        'type': 'object',
        'properties': {
            'port': {
                'type': 'integer',
                'description': 'Host port to bind Grafana to (default: 13000)',
                'default': 13000
            },
            'volume': {
                'type': 'string',
                'description': 'Name of the volume for persistent storage',
                'default': 'grafana-storage'
            },
            'network': {
                'type': 'string',
                'description': 'Docker network to connect Grafana to (e.g., host, bridge, or custom network)',
                'default': 'host'
            }
        }
    },
    output_schema={
        'success': True,
        'message': 'Grafana setup completed successfully',
        'next_steps': [],
        'documentation': ''
    }
)
async def setup_grafana(port: int = 13000, volume: str = "grafana-storage", network: str = "host") -> Dict[str, Any]:
    """
    Set up Grafana for home automation and camera monitoring.
    
    This will start a Grafana container with persistent storage and default configuration
    optimized for home automation use cases, including camera monitoring and sensor data.
    
    Default access: http://localhost:13000 (admin/admin)
    """
    try:
        from dockermcp.utils.grafana_utils import GrafanaManager
        grafana_mgr = GrafanaManager(docker_client=docker.from_env())
        result = await grafana_mgr.setup_grafana(port=port, volume=volume)
        
        if result.get('success'):
            result['next_steps'] = [
                f"1. Open Grafana in your browser: http://localhost:{port}",
                "2. Log in with admin/admin (change password when prompted)",
                "3. Add your data sources:",
                "   - InfluxDB/Telegraf for sensor data",
                "   - MQTT for IoT device communication",
                "   - Prometheus for metrics collection",
                "4. Import home automation dashboards:",
                "   - Home Automation Dashboard (ID: 13639)",
                "   - Smart Home Dashboard (ID: 10820)",
                "5. Set up alerts for motion detection or sensor thresholds"
            ]
            result['documentation'] = (
                "For home automation setup, run: await help(category='grafana')\n"
                "Recommended plugins: 'grafana-image-renderer' for camera snapshots"
            )
            
        return result
        
    except Exception as e:
        return handle_error(e, "setting up Grafana")


def handle_error(
    error: Exception,
    context: str = "system operation",
    include_details: bool = True
) -> Dict[str, Any]:
    """Handle errors and return a standardized error response.
    
    Args:
        error: The exception that was raised
        context: Description of the operation that failed
        include_details: Whether to include detailed error information
        
    Returns:
        Dict containing error information
    """
    error_type = error.__class__.__name__
    error_msg = str(error)
    
    logger.error(f"Error during {context}: {error_type}: {error_msg}", exc_info=True)
    
    error_details = {
        'type': error_type,
        'message': error_msg,
    }
    
    if include_details and hasattr(error, 'details'):
        error_details['details'] = getattr(error, 'details')
    
    return {
        'success': False,
        'error': f"Failed to {context}: {error_msg}",
        'error_type': error_type,
        'error_details': error_details,
        'timestamp': datetime.utcnow().isoformat()
    }

@Tool(
    name="system_info",
    description="Get comprehensive system-wide information about the Docker host",
    parameters={
        "type": "object",
        "properties": {
            "detailed": {"type": "boolean", "description": "Whether to include detailed resource usage information", "default": True}
        },
        "required": []
    }
)
async def system_info(detailed: bool = True) -> Dict[str, Any]:
    """Get detailed system-wide information about the Docker host.
    
    Args:
        detailed: Whether to include detailed resource usage information
        
    Returns:
        Dict containing system information
    """
    try:
        # Get basic system info
        info = await system_mgr.info()
        
        # Get container statistics
        containers = await system_mgr.containers(all=True)
        container_stats = {
            'total': len(containers),
            'running': sum(1 for c in containers if c.get('State') == 'running'),
            'paused': sum(1 for c in containers if c.get('State') == 'paused'),
            'stopped': sum(1 for c in containers if c.get('State') == 'exited'),
            'restarting': sum(1 for c in containers if c.get('State') == 'restarting'),
            'dead': sum(1 for c in containers if c.get('State') == 'dead')
        }
        
        # Get resource usage if detailed info is requested
        memory = MemoryUsage()
        cpu = CpuUsage()
        disk = DiskUsage()
        network = {}
        
        if detailed:
            try:
                # Get memory usage
                mem_stats = await system_mgr.memory_stats()
                memory = MemoryUsage(
                    used=mem_stats.get('usage', 0) - mem_stats.get('stats', {}).get('cache', 0),
                    available=mem_stats.get('limit', 0) - (mem_stats.get('usage', 0) - mem_stats.get('stats', {}).get('cache', 0)),
                    total=mem_stats.get('limit', 0),
                    buffer=mem_stats.get('stats', {}).get('buffers', 0),
                    cache=mem_stats.get('stats', {}).get('cache', 0),
                    shared=mem_stats.get('stats', {}).get('shared', 0),
                    swap_total=mem_stats.get('stats', {}).get('swap', 0),
                    swap_used=mem_stats.get('stats', {}).get('swap_usage', 0)
                )
                
                # Get CPU usage
                cpu_stats = await system_mgr.cpu_stats()
                cpu = CpuUsage(
                    cores=info.get('NCPU', 1),
                    cores_usage=[0.0] * info.get('NCPU', 1),  # Will be updated by system metrics
                    system_usage=cpu_stats.get('system_cpu_usage', 0),
                    user_usage=cpu_stats.get('cpu_usage', {}).get('usage_in_usermode', 0),
                    iowait=cpu_stats.get('cpu_usage', {}).get('usage_in_kernelmode', 0),
                    load_average={
                        '1min': 0.0,  # Will be updated by system metrics
                        '5min': 0.0,  # Will be updated by system metrics
                        '15min': 0.0  # Will be updated by system metrics
                    }
                )
                
                # Get disk usage
                disk_stats = await system_mgr.disk_usage()
                disk = DiskUsage(
                    used=disk_stats.get('LayersSize', 0),
                    available=disk_stats.get('LayersSize', 0) * 0.2,  # 20% buffer
                    total=disk_stats.get('LayersSize', 0) * 1.2,  # Total with buffer
                    mount_point=info.get('DockerRootDir', '/var/lib/docker'),
                    filesystem='overlay2',  # Default, will be updated by system metrics
                    inodes_used=0,  # Will be updated by system metrics
                    inodes_total=0,  # Will be updated by system metrics
                    read_only=False  # Will be updated by system metrics
                )
                
                # Get network interfaces
                net_stats = await system_mgr.network_stats()
                for iface, stats in net_stats.items():
                    network[iface] = NetworkUsage(
                        interface=iface,
                        bytes_sent=stats.get('tx_bytes', 0),
                        bytes_recv=stats.get('rx_bytes', 0),
                        packets_sent=stats.get('tx_packets', 0),
                        packets_recv=stats.get('rx_packets', 0),
                        errors_in=stats.get('rx_errors', 0),
                        errors_out=stats.get('tx_errors', 0),
                        speed=stats.get('speed', 0),
                        mtu=stats.get('mtu', 1500),
                        mac_address=stats.get('mac_address', ''),
                        ip_addresses=stats.get('ip_addresses', []),
                        is_up=stats.get('operstate', 'down') == 'up'
                    )
                    
            except Exception as e:
                logger.warning(f"Could not collect detailed system metrics: {str(e)}")
        
        # Build the response
        response = SystemInfoResponse(
            success=True,
            message="System information retrieved successfully",
            system_status=info,
            containers=container_stats,
            images=info.get('Images', 0),
            volumes=info.get('NVolumes', 0),
            networks=info.get('NNetworks', 0),
            server_version=info.get('ServerVersion', ''),
            api_version=info.get('ApiVersion', ''),
            min_api_version=info.get('MinAPIVersion', ''),
            kernel_version=info.get('KernelVersion', ''),
            operating_system=info.get('OperatingSystem', ''),
            os_type=info.get('OSType', ''),
            architecture=info.get('Architecture', ''),
            cpus=info.get('NCPU', 0),
            memory=memory,
            cpu=cpu,
            disk=disk,
            network=network,
            storage_driver=info.get('Driver', ''),
            logging_driver=info.get('LoggingDriver', ''),
            cgroup_driver=info.get('CgroupDriver', ''),
            cgroup_version=info.get('CgroupVersion', ''),
            security_options=info.get('SecurityOptions', []),
            experimental_build=info.get('ExperimentalBuild', False),
            debug=info.get('Debug', False),
            registry_mirrors=info.get('RegistryConfig', {}).get('Mirrors', []),
            live_restore_enabled=info.get('LiveRestoreEnabled', False),
            default_runtime=info.get('DefaultRuntime', 'runc'),
            runtimes=info.get('Runtimes', {}),
            swarm=info.get('Swarm', {}),
            warnings=info.get('Warnings', []),
            uptime=timedelta(seconds=info.get('SystemTime', 0) - info.get('SystemTime', 0) % 3600)  # Approximate
        )
        
        return response.dict()
        
    except Exception as e:
        return SystemResponse.error_response(
            message="Failed to retrieve system information",
            error_type="SystemInfoError",
            error_details={"error": str(e)},
            status_code=500
        ).dict()

@Tool(
    name="system_disk_usage",
    description="Get detailed disk usage information for Docker resources",
    parameters={
        "type": "object",
        "properties": {
            "verbose": {"type": "boolean", "description": "Whether to include detailed information about each resource", "default": False}
        },
        "required": []
    }
)
async def system_disk_usage(verbose: bool = False) -> Dict[str, Any]:
    """Get detailed disk usage information for Docker resources.
    
    Args:
        verbose: Whether to include detailed information about each resource
        
    Returns:
        Dict containing disk usage information
    """
    try:
        # Get disk usage from Docker
        usage = await system_mgr.disk_usage()
        
        # Calculate total usage
        layers_size = usage.get('LayersSize', 0)
        build_cache_size = sum(
            cache.get('Size', 0) 
            for cache in usage.get('BuildCache', [])
        )
        
        # Get detailed information if verbose is True
        detailed_usage = {}
        if verbose:
            # Get disk usage by image
            images = {}
            for img in usage.get('Images', []):
                images[img['Id']] = {
                    'size': img.get('Size', 0),
                    'shared_size': img.get('SharedSize', 0),
                    'virtual_size': img.get('VirtualSize', 0),
                    'containers': img.get('Containers', 0),
                    'tags': img.get('RepoTags', [])
                }
            
            # Get disk usage by container
            containers = {}
            for container in usage.get('Containers', []):
                containers[container['Id']] = {
                    'size_rw': container.get('SizeRw', 0),
                    'size_root_fs': container.get('SizeRootFs', 0),
                    'image': container.get('Image', ''),
                    'name': container.get('Names', [''])[0].lstrip('/'),
                    'state': container.get('State', '')
                }
            
            # Get disk usage by volume
            volumes = {}
            for vol in usage.get('Volumes', []):
                volumes[vol['Name']] = {
                    'usage_data': vol.get('UsageData', {}).get('Size', 0),
                    'driver': vol.get('Driver', ''),
                    'mountpoint': vol.get('Mountpoint', '')
                }
            
            detailed_usage = {
                'images': images,
                'containers': containers,
                'volumes': volumes,
                'build_cache': [
                    {
                        'id': cache.get('ID', ''),
                        'size': cache.get('Size', 0),
                        'created': cache.get('CreatedAt', ''),
                        'last_used': cache.get('LastUsedAt', ''),
                        'in_use': cache.get('InUse', False),
                        'shared': cache.get('Shared', False)
                    }
                    for cache in usage.get('BuildCache', [])
                ]
            }
        
        # Build the response
        response = SystemDiskUsageResponse(
            success=True,
            message="Disk usage retrieved successfully",
            layers_size=layers_size,
            images=len(usage.get('Images', [])),
            containers=len(usage.get('Containers', [])),
            volumes=len(usage.get('Volumes', [])),
            build_cache=build_cache_size,
            builder_size=0,  # Will be updated by system metrics
            total_usage=layers_size + build_cache_size,
            details=detailed_usage if verbose else None
        )
        
        return response.dict()
        
    except Exception as e:
        return SystemResponse.error_response(
            message="Failed to retrieve disk usage information",
            error_type="DiskUsageError",
            error_details={"error": str(e)},
            status_code=500
        ).dict()

@Tool(
    name="system_ping",
    description="Ping the Docker server to check connectivity and get version information",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def system_ping() -> Dict[str, Any]:
    """Ping the Docker server to check connectivity and get version information.
    
    This is a lightweight operation that can be used to verify that the Docker
    daemon is accessible and to get basic version information.
    
    Returns:
        Dict containing ping response and version information
    """
    try:
        start_time = datetime.utcnow()
        ping = await system_mgr.ping()
        end_time = datetime.utcnow()
        
        # Calculate latency in milliseconds
        latency_ms = round((end_time - start_time).total_seconds() * 1000, 2)
        
        # Get additional version information
        version = await system_mgr.version()
        
        # Build the response
        response = SystemPingResponse(
            success=True,
            message="Docker daemon is accessible",
            api_version=ping.get('ApiVersion', ''),
            os=ping.get('OSType', ''),
            arch=ping.get('Architecture', ''),
            kernel_version=ping.get('KernelVersion', ''),
            components=[
                {
                    'name': 'docker',
                    'version': version.get('Version', ''),
                    'api_version': version.get('ApiVersion', ''),
                    'min_api_version': version.get('MinAPIVersion', ''),
                    'git_commit': version.get('GitCommit', ''),
                    'go_version': version.get('GoVersion', ''),
                    'os': version.get('Os', ''),
                    'arch': version.get('Arch', '')
                },
                {
                    'name': 'containerd',
                    'version': version.get('Components', [{}])[0].get('Version', ''),
                    'details': version.get('Components', [{}])[0].get('Details', {})
                },
                {
                    'name': 'runc',
                    'version': version.get('RuncCommit', {}).get('ID', ''),
                    'commit': version.get('RuncCommit', {}).get('ID', '')
                },
                {
                    'name': 'docker-init',
                    'version': version.get('InitCommit', {}).get('ID', ''),
                    'commit': version.get('InitCommit', {}).get('ID', '')
                }
            ],
            platform={
                'name': version.get('Platform', {}).get('Name', ''),
                'os': version.get('Os', ''),
                'architecture': version.get('Arch', ''),
                'kernel_version': version.get('KernelVersion', '')
            },
            security_options=version.get('SecurityOptions', []),
            build_time=version.get('BuildTime', ''),
            experimental=version.get('Experimental', False),
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return response.dict()
        
    except Exception as e:
        return SystemResponse.error_response(
            message="Failed to ping Docker server",
            error_type="PingError",
            error_details={"error": str(e)},
            status_code=503  # Service Unavailable
        ).dict()

@Tool(
    name="system_auth",
    description="Authenticate with a Docker registry",
    parameters={
        "type": "object",
        "properties": {
            "request": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Registry username"},
                    "password": {"type": "string", "description": "Registry password or token"},
                    "email": {"type": "string", "format": "email", "description": "Email address for the registry account"},
                    "serveraddress": {"type": "string", "description": "Address of the registry server"},
                    "reauth": {"type": "boolean", "description": "Whether to force re-authentication", "default": False}
                },
                "required": ["username", "password", "serveraddress"]
            }
        },
        "required": ["request"]
    }
)
async def system_auth(
    request: SystemAuthRequest
) -> Dict[str, Any]:
    """Authenticate with a Docker registry with enhanced security and token management.
    
    This function handles authentication with Docker registries, including support for:
    - Basic authentication (username/password)
    - Token-based authentication
    - Refresh tokens
    - Credential helpers
    
    Args:
        request: Authentication request containing credentials and registry information
        
    Returns:
        Dict containing authentication response with token and status
    """
    try:
        # Build auth configuration
        auth_config = {
            'username': request.username,
            'password': request.password,
            'email': request.email,
            'serveraddress': request.serveraddress,
            'auth': request.auth,
            'registrytoken': request.registry_token,
            'identitytoken': request.identity_token
        }
        
        # Add credential helper configuration if provided
        if request.creds_store:
            auth_config['credsStore'] = request.creds_store
        if request.creds_store_opt:
            auth_config['credHelpers'] = request.creds_store_opt
        
        # Perform authentication
        start_time = datetime.utcnow()
        response = await system_mgr.auth(auth_config)
        end_time = datetime.utcnow()
        
        # Parse response
        status = response.get('Status', '').lower()
        is_success = 'succeeded' in status or 'login' in status
        
        # Build response
        auth_response = SystemAuthResponse(
            success=is_success,
            message=response.get('Status', 'Authentication completed'),
            status=response.get('Status', 'Login Succeeded'),
            identity_token=response.get('IdentityToken'),
            expires_in=response.get('ExpiresIn'),
            refresh_token=response.get('RefreshToken'),
            registry_url=request.serveraddress,
            username=request.username,
            email=request.email,
            server_info={
                'server_version': response.get('ServerVersion'),
                'api_version': response.get('ApiVersion'),
                'min_api_version': response.get('MinAPIVersion')
            },
            latency_ms=round((end_time - start_time).total_seconds() * 1000, 2),
            timestamp=datetime.utcnow().isoformat()
        )
        
        return auth_response.dict()
        
    except Exception as e:
        return SystemResponse.error_response(
            message="Authentication failed",
            error_type="AuthenticationError",
            error_details={
                "error": str(e),
                "server": getattr(request, 'serveraddress', 'unknown'),
                "username": getattr(request, 'username', 'not provided')
            },
            status_code=401  # Unauthorized
        ).dict()

@Tool(
    name="system_prune",
    description="Delete unused Docker resources to free up disk space",
    parameters={
        "type": "object",
        "properties": {
            "request": {
                "type": "object",
                "properties": {
                    "containers": {"type": "boolean", "description": "Remove all stopped containers", "default": True},
                    "images": {"type": "boolean", "description": "Remove unused images", "default": True},
                    "volumes": {"type": "boolean", "description": "Remove unused volumes", "default": False},
                    "networks": {"type": "boolean", "description": "Remove unused networks", "default": True},
                    "build_cache": {"type": "boolean", "description": "Remove build cache", "default": True},
                    "all": {"type": "boolean", "description": "Remove all unused resources (overrides other options)", "default": False},
                    "filters": {
                        "type": "object",
                        "description": "Filter what to prune",
                        "properties": {
                            "until": {"type": "string", "description": "Prune resources created before this timestamp"},
                            "label": {"type": "array", "items": {"type": "string"}, "description": "Prune resources with matching labels"}
                        }
                    }
                },
                "required": []
            }
        },
        "required": ["request"]
    }
)
async def system_prune(
    request: SystemPruneRequest
) -> Dict[str, Any]:
    """Delete unused Docker resources to free up disk space.
    
    This function can remove:
    - Stopped containers
    - Dangling images
    - Unused networks
    - Build cache
    - Unused volumes (if requested)
    
    Args:
        request: Prune configuration specifying what to remove
        
    Returns:
        Dict containing information about the pruned resources and reclaimed space
    """
    try:
        # Validate request
        if not any([
            request.prune_containers,
            request.prune_volumes,
            request.prune_images,
            request.prune_networks,
            request.prune_build_cache
        ]):
            return SystemResponse.error_response(
                message="No resources selected for pruning",
                error_type="ValidationError",
                status_code=400
            ).dict()
        
        # Convert filters to Docker API format
        prune_filters = request.get_filters() if hasattr(request, 'get_filters') else {}
        
        # Initialize response
        response = SystemPruneResponse(
            success=True,
            message="Prune operation completed successfully",
            reclaimed_space=0,
            reclaimed_space_human="0B",
            deleted_objects={},
            deleted_counts={},
            prune_errors={}
        )
        
        # Prune containers if requested
        if request.prune_containers:
            try:
                result = await system_mgr.prune_containers(
                    filters=prune_filters.get('containers', {})
                )
                if result:
                    response.add_deleted_objects('containers', result.get('ContainersDeleted', []))
                    response.reclaimed_space += result.get('SpaceReclaimed', 0)
            except Exception as e:
                response.add_prune_error('containers', str(e))
                logger.error(f"Error pruning containers: {str(e)}")
        
        # Prune images if requested
        if request.prune_images:
            try:
                result = await system_mgr.prune_images(
                    filters=prune_filters.get('images', {})
                )
                if result:
                    response.add_deleted_objects('images', result.get('ImagesDeleted', []))
                    response.reclaimed_space += result.get('SpaceReclaimed', 0)
            except Exception as e:
                response.add_prune_error('images', str(e))
                logger.error(f"Error pruning images: {str(e)}")
        
        # Prune networks if requested
        if request.prune_networks:
            try:
                result = await system_mgr.prune_networks(
                    filters=prune_filters.get('networks', {})
                )
                if result:
                    response.add_deleted_objects('networks', result.get('NetworksDeleted', []))
            except Exception as e:
                response.add_prune_error('networks', str(e))
                logger.error(f"Error pruning networks: {str(e)}")
        
        # Prune volumes if requested
        if request.prune_volumes:
            try:
                result = await system_mgr.prune_volumes(
                    filters=prune_filters.get('volumes', {})
                )
                if result:
                    response.add_deleted_objects('volumes', result.get('VolumesDeleted', []))
                    response.reclaimed_space += result.get('SpaceReclaimed', 0)
            except Exception as e:
                response.add_prune_error('volumes', str(e))
                logger.error(f"Error pruning volumes: {str(e)}")
        
        # Prune build cache if requested
        if request.prune_build_cache:
            try:
                result = await system_mgr.prune_build_cache(
                    filters=prune_filters.get('build-cache', {})
                )
                if result:
                    response.add_deleted_objects('build_cache', result.get('CachesDeleted', []))
                    response.reclaimed_space += result.get('SpaceReclaimed', 0)
            except Exception as e:
                response.add_prune_error('build_cache', str(e))
                logger.error(f"Error pruning build cache: {str(e)}")
        
        # Update human-readable size
        response.reclaimed_space_human = format_size(response.reclaimed_space)
        
        # Check if any operations failed
        if response.prune_errors:
            response.success = False
            response.message = "Prune operation completed with errors"
        
        return response.dict()
        
    except Exception as e:
        return SystemResponse.error_response(
            message="Prune operation failed",
            error_type="PruneError",
            error_details={"error": str(e)},
            status_code=500
        ).dict()

@Tool(
    name="system_events",
    description="Monitor Docker events in real-time",
    parameters={
        "type": "object",
        "properties": {
            "request": {
                "type": "object",
                "properties": {
                    "since": {"type": "string", "format": "date-time", "description": "Show events created since this timestamp"},
                    "until": {"type": "string", "format": "date-time", "description": "Show events created before this timestamp"},
                    "filters": {
                        "type": "object",
                        "description": "Filter events by criteria",
                        "properties": {
                            "type": {"type": "array", "items": {"type": "string"}, "description": "Event types to include (e.g., 'container', 'image', 'network')"},
                            "event": {"type": "array", "items": {"type": "string"}, "description": "Event actions to include (e.g., 'start', 'stop', 'die')"},
                            "container": {"type": "array", "items": {"type": "string"}, "description": "Filter by container ID or name"},
                            "image": {"type": "array", "items": {"type": "string"}, "description": "Filter by image ID or name"},
                            "label": {"type": "array", "items": {"type": "string"}, "description": "Filter by labels"},
                            "event_type": {"type": "array", "items": {"type": "string"}, "description": "Filter by event type (deprecated, use 'type' instead)"}
                        }
                    },
                    "stream": {"type": "boolean", "description": "Stream events in real-time", "default": False}
                },
                "required": []
            }
        },
        "required": ["request"]
    }
)
async def system_events(
    request: SystemEventsRequest
) -> Dict[str, Any]:
    """Monitor Docker events in real-time or query historical events.
    
    This function provides a stream of Docker events that can be filtered by:
    - Event type (container, image, volume, network, etc.)
    - Action (create, start, stop, die, etc.)
    - Time range (since/until)
    - Custom filters
    
    Args:
        request: Event subscription configuration
        
    Returns:
        Dict containing event stream or historical events
    """
    try:
        # Convert filters to Docker API format
        event_filters = {}
        if request.filters:
            event_filters = request.filters.to_dict()
        
        # Handle streaming events
        if request.stream:
            async def event_generator():
                """Generator function that yields events as they occur."""
                event_queue = asyncio.Queue()
                
                async def callback(event):
                    """Callback for processing events."""
                    await event_queue.put(event)
                
                try:
                    # Stream events as they arrive
                    while True:
                        try:
                            event = await asyncio.wait_for(
                                event_queue.get(),
                                timeout=request.timeout if request.timeout else 30
                            )
                            yield {
                                'success': True,
                                'message': 'Event received',
                                'timestamp': datetime.utcnow().isoformat(),
                                'event': event
                            }
                            event_queue.task_done()
                        except asyncio.TimeoutError:
                            # Send a keep-alive message
                            yield {
                                'success': True,
                                'message': 'Event stream active',
                                'timestamp': datetime.utcnow().isoformat(),
                                'event': None
                            }
                except asyncio.CancelledError:
                    logger.info("Event stream cancelled by client")
                    raise
                except Exception as e:
                    logger.error(f"Error in event stream: {str(e)}")
                    yield {
                        'success': False,
                        'message': f'Event stream error: {str(e)}',
                        'timestamp': datetime.utcnow().isoformat(),
                        'error': str(e)
                    }
                finally:
                    # Cleanup
                    if listener and hasattr(listener, 'close'):
                        await listener.close()
            
            # Return the async generator for streaming
            return event_generator()
        
        # Handle one-time event query
        else:
            events = await system_mgr.events(
                since=request.since,
                until=request.until,
                filters=event_filters,
                decode=True
            )
            
            # Apply limit if specified
            if request.limit and len(events) > request.limit:
                events = events[-request.limit:]
            
            return SystemEventsResponse(
                success=True,
                message=f"Retrieved {len(events)} events",
                events=events,
                count=len(events),
                start_time=request.since,
                end_time=request.until or datetime.utcnow().isoformat(),
                filters=event_filters
            ).dict()
            
    except Exception as e:
        return SystemResponse.error_response(
            message="Failed to retrieve events",
            error_type="EventError",
            error_details={"error": str(e)},
            status_code=500
        ).dict()

@Tool(
    name="system_data_usage",
    description="Get detailed data usage information about the Docker installation",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def system_data_usage() -> Dict[str, Any]:
    """Get comprehensive data usage information about the Docker installation.
    
    This function provides detailed information about disk usage by Docker, including:
    - Images and their sizes
    - Containers and their disk usage
    - Volumes and their sizes
    - Build cache usage
    - Builder disk usage
    
    Returns:
        Dict containing detailed data usage information
    """
    try:
        # Get disk usage data
        usage = await system_mgr.df()
        
        # Calculate total usage
        layers_size = usage.get('LayersSize', 0)
        builder_size = usage.get('BuilderSize', 0)
        
        # Process images
        images = []
        image_total_size = 0
        for img in usage.get('Images', []):
            img_size = img.get('Size', 0)
            images.append({
                'id': img.get('Id', ''),
                'tags': img.get('RepoTags', []),
                'size': img_size,
                'shared_size': img.get('SharedSize', 0),
                'virtual_size': img.get('VirtualSize', 0),
                'containers': img.get('Containers', 0),
                'created': img.get('Created', 0),
                'created_human': str(datetime.fromtimestamp(img.get('Created', 0))) if img.get('Created') else None
            })
            image_total_size += img_size
        
        # Process containers
        containers = []
        container_total_size = 0
        for container in usage.get('Containers', []):
            container_size = container.get('SizeRw', 0) + container.get('SizeRootFs', 0)
            containers.append({
                'id': container.get('Id', ''),
                'name': container.get('Names', [''])[0].lstrip('/'),
                'image': container.get('Image', ''),
                'command': container.get('Command', ''),
                'state': container.get('State', ''),
                'status': container.get('Status', ''),
                'size_rw': container.get('SizeRw', 0),
                'size_root_fs': container.get('SizeRootFs', 0),
                'total_size': container_size,
                'created': container.get('Created', 0),
                'created_human': str(datetime.fromtimestamp(container.get('Created', 0))) if container.get('Created') else None
            })
            container_total_size += container_size
        
        # Process volumes
        volumes = []
        volume_total_size = 0
        for vol in usage.get('Volumes', []):
            vol_size = vol.get('UsageData', {}).get('Size', 0)
            volumes.append({
                'name': vol.get('Name', ''),
                'driver': vol.get('Driver', ''),
                'mountpoint': vol.get('Mountpoint', ''),
                'scope': vol.get('Scope', ''),
                'size': vol_size,
                'ref_count': vol.get('UsageData', {}).get('RefCount', 0)
            })
            volume_total_size += vol_size
        
        # Process build cache
        build_cache = []
        build_cache_total_size = 0
        for cache in usage.get('BuildCache', []):
            cache_size = cache.get('Size', 0)
            build_cache.append({
                'id': cache.get('ID', ''),
                'type': cache.get('Type', ''),
                'description': cache.get('Description', ''),
                'size': cache_size,
                'created': cache.get('CreatedAt', ''),
                'last_used': cache.get('LastUsedAt', ''),
                'in_use': cache.get('InUse', False),
                'shared': cache.get('Shared', False)
            })
            build_cache_total_size += cache_size
        
        # Calculate total usage
        total_usage = layers_size + builder_size + container_total_size + volume_total_size + build_cache_total_size
        
        # Build response
        return SystemDataUsageResponse(
            success=True,
            message="Data usage retrieved successfully",
            layers_size=layers_size,
            builder_size=builder_size,
            images={
                'total': len(images),
                'total_size': image_total_size,
                'details': images
            },
            containers={
                'total': len(containers),
                'total_size': container_total_size,
                'by_state': {
                    'running': sum(1 for c in containers if c.get('state') == 'running'),
                    'paused': sum(1 for c in containers if c.get('state') == 'paused'),
                    'stopped': sum(1 for c in containers if c.get('state') == 'exited'),
                    'dead': sum(1 for c in containers if c.get('state') == 'dead')
                },
                'details': containers
            },
            volumes={
                'total': len(volumes),
                'total_size': volume_total_size,
                'by_driver': {
                    vol['driver']: sum(1 for v in volumes if v['driver'] == vol['driver'])
                    for vol in volumes
                },
                'details': volumes
            },
            build_cache={
                'total': len(build_cache),
                'total_size': build_cache_total_size,
                'in_use': sum(1 for c in build_cache if c['in_use']),
                'shared': sum(1 for c in build_cache if c['shared']),
                'details': build_cache
            },
            total_usage=total_usage,
            total_usage_human=format_size(total_usage),
            timestamp=datetime.utcnow().isoformat()
        ).dict()
        
    except Exception as e:
        return SystemResponse.error_response(
            message="Failed to retrieve data usage information",
            error_type="DataUsageError",
            error_details={"error": str(e)},
            status_code=500
        ).dict()


