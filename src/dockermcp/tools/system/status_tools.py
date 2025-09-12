"""
Enhanced Docker status tool with graceful failure handling.

This replaces the existing system_tools.py status function with one that
works even when Docker daemon is unavailable.
"""
import os
import logging
import platform
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional
from fastmcp.tools import Tool, tool, tool, tool
from dockermcp.logging_config import logger

@Tool(
    name="docker_status",
    description="Get comprehensive Docker connection status and diagnostic information. Works even when Docker is unavailable.",
    parameters={
        'type': 'object',
        'properties': {},
        'required': []
    }
)
async def docker_status() -> Dict[str, Any]:
from dockermcp.logging_config import logger

async def docker_status() -> Dict[str, Any]:
    """
    Get comprehensive Docker connection status and diagnostic information.
    
    This tool ALWAYS works, even when Docker daemon is unavailable.
    
    Returns:
        Dict containing detailed Docker status and diagnostic info
    """
    try:
        # Import Docker connection utilities from __init__.py
        from dockermcp import (
            docker_available, 
            docker_client, 
            docker_error,
            get_docker_status,
            retry_docker_connection
        )
        
        result = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'docker_status': get_docker_status(),
            'system_info': {},
            'troubleshooting': {},
            'recovery_actions': []
        }
        
        # Add system information regardless of Docker status
        result['system_info'] = {
            'platform': platform.system(),
            'platform_version': platform.release(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'current_user': os.getenv('USERNAME') or os.getenv('USER', 'unknown')
        }
        
        # Docker-specific diagnostics
        if not docker_available:
            result['troubleshooting'] = await _get_docker_troubleshooting()
            result['recovery_actions'] = await _get_recovery_actions()
        else:
            # Docker is available - get additional info
            try:
                if docker_client:
                    # Get detailed Docker info
                    info = docker_client.info()
                    version = docker_client.version()
                    
                    result['docker_details'] = {
                        'server_version': info.get('ServerVersion'),
                        'api_version': version.get('ApiVersion'),
                        'build_version': version.get('Version'),
                        'git_commit': version.get('GitCommit'),
                        'go_version': version.get('GoVersion'),
                        'os_type': info.get('OSType'),
                        'architecture': info.get('Architecture'),
                        'cpu_count': info.get('NCPU'),
                        'total_memory': info.get('MemTotal'),
                        'docker_root_dir': info.get('DockerRootDir'),
                        'storage_driver': info.get('Driver'),
                        'cgroup_version': info.get('CgroupVersion'),
                        'runtime': info.get('DefaultRuntime'),
                        'containers_total': info.get('Containers', 0),
                        'containers_running': info.get('ContainersRunning', 0),
                        'containers_paused': info.get('ContainersPaused', 0),
                        'containers_stopped': info.get('ContainersStopped', 0),
                        'images_count': info.get('Images', 0)
                    }
                    
                    result['connection_test'] = {
                        'ping_successful': True,
                        'api_reachable': True,
                        'containers_listable': True
                    }
                    
                    # Test container listing
                    try:
                        containers = docker_client.containers.list(limit=1)
                        result['connection_test']['containers_listable'] = True
                    except Exception as e:
                        result['connection_test']['containers_listable'] = False
                        result['connection_test']['container_list_error'] = str(e)
                        
            except Exception as e:
                result['docker_status']['error'] = f"Error getting detailed Docker info: {str(e)}"
                result['troubleshooting']['detailed_info_error'] = str(e)
        
        # Add quick actions
        result['available_actions'] = {
            'retry_connection': 'Call docker_reconnect() to attempt reconnection',
            'get_logs': 'Check Docker service logs for issues',
@Tool(
    name="docker_reconnect",
    description="Attempt to reconnect to Docker daemon after connection failure",
    parameters={
        'type': 'object',
        'properties': {},
        'required': []
    }
)
async def docker_reconnect() -> Dict[str, Any]:
            'restart_docker': 'Restart Docker service (requires admin)',
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in docker_status: {str(e)}")
        return {
            'success': False,
            'error': f"Status check failed: {str(e)}",
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'basic_info': {
                'platform': platform.system(),
                'docker_available': False
            }
        }

async def docker_reconnect() -> Dict[str, Any]:
    """
    Attempt to reconnect to Docker daemon.
    
    Returns:
        Dict with reconnection attempt results
    """
    try:
        from dockermcp import retry_docker_connection, get_docker_status
        
        logger.info("Attempting Docker reconnection...")
        success = retry_docker_connection()
        
        result = {
            'success': success,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'message': 'Reconnection successful' if success else 'Reconnection failed',
            'docker_status': get_docker_status()
        }
        
        if success:
            result['next_steps'] = [
                'Docker connection restored',
                'All Docker tools should now work normally',
                'Run docker_status() to verify full functionality'
            ]
        else:
            result['next_steps'] = [
                'Reconnection failed - check Docker service status',
                'See troubleshooting info in docker_status()',
                'Consider restarting Docker service'
            ]
            
        return result
        
    except Exception as e:
        logger.error(f"Error in docker_reconnect: {str(e)}")
        return {
            'success': False,
            'error': f"Reconnection attempt failed: {str(e)}",
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

async def _get_docker_troubleshooting() -> Dict[str, Any]:
    """Get Docker troubleshooting information based on platform."""
    troubleshooting = {
        'platform': platform.system(),
        'checks_performed': [],
        'likely_causes': [],
        'service_status': 'unknown'
    }
    
    if platform.system() == 'Windows':
        troubleshooting.update({
            'service_name': 'com.docker.service',
            'likely_causes': [
                'Docker Desktop not running',
                'Docker service not started',
                'Docker Desktop stuck in starting state',
                'Windows Hyper-V issues',
                'WSL2 integration problems',
                'Named pipes connection issues'
            ],
            'common_fixes': [
                'Restart Docker Desktop',
                'Run as Administrator',
                'Check Windows Services for Docker Desktop Service',
                'Restart WSL2: wsl --shutdown',
                'Check Hyper-V is enabled',
                'Clear Docker Desktop data (reset to factory defaults)'
            ]
        })
        
        # Try to check Windows service status
        try:
            result = subprocess.run([
                'powershell', '-Command', 
                'Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue | Select-Object Status'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout:
                troubleshooting['service_status'] = result.stdout.strip()
                troubleshooting['checks_performed'].append('Windows service status checked')
            else:
                troubleshooting['service_status'] = 'Docker Desktop service not found'
                
        except Exception as e:
            troubleshooting['service_check_error'] = str(e)
            
    elif platform.system() == 'Linux':
        troubleshooting.update({
            'service_name': 'docker',
            'likely_causes': [
                'Docker daemon not running',
                'User not in docker group',
                'Docker socket permission issues',
                'Docker daemon crashed',
                'Systemd service issues'
            ],
            'common_fixes': [
                'sudo systemctl start docker',
                'sudo systemctl enable docker',
                'sudo usermod -aG docker $USER (then logout/login)',
                'Check logs: journalctl -u docker.service',
                'Restart daemon: sudo systemctl restart docker'
            ]
        })
        
        # Try to check systemd service status
        try:
            result = subprocess.run([
                'systemctl', 'is-active', 'docker'
            ], capture_output=True, text=True, timeout=5)
            
            troubleshooting['service_status'] = result.stdout.strip()
            troubleshooting['checks_performed'].append('Systemd service status checked')
            
        except Exception as e:
            troubleshooting['service_check_error'] = str(e)
            
    else:
        troubleshooting.update({
            'message': f'Unsupported platform: {platform.system()}',
            'likely_causes': ['Platform-specific Docker installation issues'],
            'common_fixes': ['Check Docker documentation for your platform']
        })
    
    return troubleshooting

async def _get_recovery_actions() -> list:
    """Get platform-specific recovery actions."""
    actions = []
    
    if platform.system() == 'Windows':
        actions = [
            {
                'action': 'restart_docker_desktop',
                'description': 'Restart Docker Desktop application',
                'command': 'Manually restart Docker Desktop from system tray or Start menu',
                'admin_required': False
            },
            {
                'action': 'restart_service',
                'description': 'Restart Docker Desktop Service',
                'command': 'Restart-Service -Name "com.docker.service"',
                'admin_required': True
            },
            {
                'action': 'reset_wsl',
                'description': 'Reset WSL2 integration',
                'command': 'wsl --shutdown',
                'admin_required': False
            }
        ]
    elif platform.system() == 'Linux':
        actions = [
            {
                'action': 'start_service',
                'description': 'Start Docker service',
                'command': 'sudo systemctl start docker',
                'admin_required': True
            },
            {
                'action': 'restart_service', 
                'description': 'Restart Docker service',
                'command': 'sudo systemctl restart docker',
                'admin_required': True
            },
            {
                'action': 'check_permissions',
                'description': 'Add user to docker group',
                'command': 'sudo usermod -aG docker $USER',
                'admin_required': True,
                'note': 'Requires logout/login to take effect'
            }
        ]
    
    return actions
