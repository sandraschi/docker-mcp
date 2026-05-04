"""
Network management operations for Docker MCP.
Implements network-related operations with proper error handling and type hints.
"""
import json
import subprocess
from typing import Any

from dockermcp.logging_config import logger

# Get a child logger for this module
logger = logger.getChild('networks')

class NetworkManager:
    """
    Handles Docker network operations with proper error handling.
    """

    def list_networks(self) -> dict[str, Any]:
        """
        List all Docker networks.
        
        Returns:
            Dict containing network information or error details
        """
        try:
            result = subprocess.run(
                ['docker', 'network', 'ls', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse the JSON output
            networks = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    networks.append(json.loads(line))

            return {
                'success': True,
                'networks': networks,
                'count': len(networks)
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list networks: {e.stderr}")
            return {
                'success': False,
                'error': f"Failed to list networks: {e.stderr}",
                'networks': [],
                'count': 0
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse network list: {e}")
            return {
                'success': False,
                'error': f"Failed to parse network list: {e}",
                'networks': [],
                'count': 0
            }

    def create_network(self, name: str, driver: str = "bridge") -> dict[str, Any]:
        """
        Create a new Docker network.
        
        Args:
            name: Name of the network
            driver: Network driver (default: bridge)
            
        Returns:
            Dict containing creation result or error details
        """
        try:
            result = subprocess.run(
                ['docker', 'network', 'create', '--driver', driver, name],
                capture_output=True,
                text=True,
                check=True
            )

            return {
                'success': True,
                'network_id': result.stdout.strip(),
                'name': name,
                'driver': driver
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create network {name}: {e.stderr}")
            return {
                'success': False,
                'error': f"Failed to create network: {e.stderr}",
                'name': name,
                'driver': driver
            }

    def remove_network(self, network_id: str) -> dict[str, Any]:
        """
        Remove a Docker network.
        
        Args:
            network_id: ID or name of the network to remove
            
        Returns:
            Dict containing removal result or error details
        """
        try:
            subprocess.run(
                ['docker', 'network', 'rm', network_id],
                capture_output=True,
                text=True,
                check=True
            )

            return {
                'success': True,
                'network_id': network_id,
                'message': f"Network {network_id} removed successfully"
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove network {network_id}: {e.stderr}")
            return {
                'success': False,
                'error': f"Failed to remove network: {e.stderr}",
                'network_id': network_id
            }
