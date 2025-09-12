"""
System-level Docker operations.

This module provides functions for system-wide Docker operations including
system information, disk usage, and cleanup.
"""
from typing import Dict, List, Optional, Any
import asyncio
import logging
from ..logging_config import ContextLogger

logger = ContextLogger(logging.getLogger(f"dockermcp.core.{__name__}"), {})

# TODO: Move system operations from docker_ops/system.py to here

class SystemManager:
    """Manager for system-level Docker operations."""
    
    def __init__(self, docker_client):
        """Initialize with a Docker client."""
        self.client = docker_client
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get Docker system information."""
        try:
            info = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.info
            )
            return {
                'containers': info['Containers'],
                'containers_running': info['ContainersRunning'],
                'containers_paused': info['ContainersPaused'],
                'containers_stopped': info['ContainersStopped'],
                'images': info['Images'],
                'driver': info['Driver'],
                'os': info['OperatingSystem'],
                'architecture': info['Architecture'],
                'cpus': info['NCPU'],
                'memory': info['MemTotal'],
                'docker_root_dir': info['DockerRootDir']
            }
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            raise

    # Add other system operations here...
