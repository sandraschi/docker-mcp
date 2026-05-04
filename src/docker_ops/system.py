"""
System management operations for Docker MCP.
Handles Docker system operations with proper error handling and type hints.
"""
import json
import subprocess
from typing import Any

from dockermcp.logging_config import logger

# Get a child logger for this module
logger = logger.getChild('system')

class SystemManager:
    """
    Handles Docker system operations with proper error handling.
    """

    def system_info(self) -> dict[str, Any]:
        """
        Get Docker system information.
        
        Returns:
            Dict containing system information or error details
        """
        try:
            result = subprocess.run(
                ['docker', 'system', 'info', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                check=True
            )

            return {
                'success': True,
                'info': json.loads(result.stdout)
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get system info: {e.stderr}")
            return {
                'success': False,
                'error': f"Failed to get system info: {e.stderr}"
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse system info: {e}")
            return {
                'success': False,
                'error': f"Failed to parse system info: {e}"
            }

    def version_info(self) -> dict[str, Any]:
        """
        Get Docker version information.
        
        Returns:
            Dict containing version information or error details
        """
        try:
            result = subprocess.run(
                ['docker', 'version', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                check=True
            )

            return {
                'success': True,
                'version': json.loads(result.stdout)
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get version info: {e.stderr}")
            return {
                'success': False,
                'error': f"Failed to get version info: {e.stderr}"
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse version info: {e}")
            return {
                'success': False,
                'error': f"Failed to parse version info: {e}"
            }

    def disk_usage(self) -> dict[str, Any]:
        """
        Get Docker disk usage information.
        
        Returns:
            Dict containing disk usage information or error details
        """
        try:
            result = subprocess.run(
                ['docker', 'system', 'df', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                check=True
            )

            return {
                'success': True,
                'disk_usage': json.loads(f'[{result.stdout.replace("}\n{", "},{")}]')
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get disk usage: {e.stderr}")
            return {
                'success': False,
                'error': f"Failed to get disk usage: {e.stderr}"
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse disk usage: {e}")
            return {
                'success': False,
                'error': f"Failed to parse disk usage: {e}"
            }

    def system_prune(self, volumes: bool = False, networks: bool = False, force: bool = False) -> dict[str, Any]:
        """
        Remove unused Docker data.
        
        Args:
            volumes: Prune volumes (default: False)
            networks: Prune networks (default: False)
            force: Do not prompt for confirmation (default: False)
            
        Returns:
            Dict containing prune results or error details
        """
        cmd = ['docker', 'system', 'prune', '--force'] if force else ['docker', 'system', 'prune']

        if volumes:
            cmd.append('--volumes')
        if networks:
            cmd.append('--networks')

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            return {
                'success': True,
                'output': result.stdout,
                'pruned_volumes': volumes,
                'pruned_networks': networks
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to prune system: {e.stderr}")
            return {
                'success': False,
                'error': f"Failed to prune system: {e.stderr}",
                'pruned_volumes': False,
                'pruned_networks': False
            }
