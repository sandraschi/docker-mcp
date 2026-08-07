"""
Volume management operations for Docker MCP.
Handles Docker volume operations with proper error handling and type hints.
"""

import json
import subprocess
from typing import Any

from dockermcp.logging_config import logger

# Get a child logger for this module
logger = logger.getChild("volumes")


class VolumeManager:
    """
    Handles Docker volume operations with proper error handling.
    """

    def list_volumes(self) -> dict[str, Any]:
        """
        List all Docker volumes.

        Returns:
            Dict containing volume information or error details
        """
        try:
            result = subprocess.run(
                ["docker", "volume", "ls", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse the JSON output
            volumes = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    volumes.append(json.loads(line))

            return {"success": True, "volumes": volumes, "count": len(volumes)}

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list volumes: {e.stderr}")
            return {"success": False, "error": f"Failed to list volumes: {e.stderr}", "volumes": [], "count": 0}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse volume list: {e}")
            return {"success": False, "error": f"Failed to parse volume list: {e}", "volumes": [], "count": 0}

    def create_volume(self, name: str, driver: str = "local") -> dict[str, Any]:
        """
        Create a new Docker volume.

        Args:
            name: Name of the volume
            driver: Volume driver (default: local)

        Returns:
            Dict containing creation result or error details
        """
        try:
            result = subprocess.run(
                ["docker", "volume", "create", "--driver", driver, name],
                capture_output=True,
                text=True,
                check=True,
            )

            return {"success": True, "volume_name": result.stdout.strip(), "driver": driver}

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create volume {name}: {e.stderr}")
            return {
                "success": False,
                "error": f"Failed to create volume: {e.stderr}",
                "volume_name": name,
                "driver": driver,
            }

    def remove_volume(self, volume_name: str, force: bool = False) -> dict[str, Any]:
        """
        Remove a Docker volume.

        Args:
            volume_name: Name of the volume to remove
            force: Force removal even if in use (default: False)

        Returns:
            Dict containing removal result or error details
        """
        cmd = ["docker", "volume", "rm"]
        if force:
            cmd.append("--force")
        cmd.append(volume_name)

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "success": True,
                "volume_name": volume_name,
                "message": f"Volume {volume_name} removed successfully",
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove volume {volume_name}: {e.stderr}")
            return {"success": False, "error": f"Failed to remove volume: {e.stderr}", "volume_name": volume_name}
