"""
Docker Watchdog Service

A cross-platform service that monitors the Docker daemon and automatically attempts recovery
if it becomes unresponsive or crashes.
"""

import asyncio
import logging
import platform
import subprocess
from typing import Any

import docker
from docker.errors import DockerException

logger = logging.getLogger(__name__)


class DockerWatchdog:
    def __init__(self, check_interval: int = 30, max_retries: int = 3):
        """
        Initialize the Docker watchdog service.

        Args:
            check_interval: Seconds between health checks
            max_retries: Number of retry attempts before giving up
        """
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.retry_count = 0
        self.is_windows = platform.system().lower() == "windows"
        self.docker_client = self._get_docker_client()

    def _get_docker_client(self) -> docker.DockerClient:
        """Get a Docker client with error handling."""
        try:
            return docker.from_env()
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    async def check_docker_health(self) -> dict[str, Any]:
        """Check if Docker daemon is healthy."""
        try:
            # Test basic API connectivity
            self.docker_client.ping()

            # Test container operations
            self.docker_client.containers.list(limit=1)

            self.retry_count = 0  # Reset retry counter on success
            return {"status": "healthy", "message": "Docker daemon is responding normally"}

        except Exception as e:
            self.retry_count += 1
            logger.warning(f"Docker health check failed (attempt {self.retry_count}/{self.max_retries}): {e}")

            if self.retry_count >= self.max_retries:
                return {
                    "status": "unhealthy",
                    "message": f"Docker daemon is not responding after {self.max_retries} attempts",
                    "error": str(e),
                }
            return {
                "status": "degraded",
                "message": f"Docker daemon check failed (attempt {self.retry_count}/{self.max_retries})",
                "error": str(e),
            }

    async def restart_docker_service(self) -> dict[str, Any]:
        """Attempt to restart the Docker service."""
        try:
            if self.is_windows:
                # Windows service restart
                subprocess.run(["net", "stop", "docker"], check=True, capture_output=True, text=True)  # noqa: S607
                subprocess.run(["net", "start", "docker"], check=True, capture_output=True, text=True)  # noqa: S607
            else:
                # Linux/Unix service restart
                subprocess.run(["sudo", "systemctl", "restart", "docker"], check=True, capture_output=True, text=True)  # noqa: S607  # noqa: S603 S607

            # Give Docker some time to start up
            await asyncio.sleep(5)
            return {"success": True, "message": "Docker service restarted successfully"}

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to restart Docker service: {e.stderr}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Error restarting Docker service: {e!s}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def monitor(self):
        """Main monitoring loop."""
        logger.info("Starting Docker watchdog service...")

        while True:
            health = await self.check_docker_health()

            if health["status"] == "unhealthy":
                logger.warning("Docker daemon is unhealthy, attempting recovery...")
                result = await self.restart_docker_service()

                if not result.get("success"):
                    logger.error(f"Failed to recover Docker: {result.get('error')}")
                    # TODO: Send alert/notification
                else:
                    logger.info("Docker service recovery successful")
                    self.docker_client = self._get_docker_client()  # Reinitialize client

            await asyncio.sleep(self.check_interval)

    @classmethod
    async def start_service(cls, check_interval: int = 30, max_retries: int = 3):
        """Start the watchdog service."""
        watchdog = cls(check_interval=check_interval, max_retries=max_retries)
        await watchdog.monitor()


if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("docker_watchdog.log")],
    )

    # Start the watchdog
    try:
        asyncio.run(DockerWatchdog.start_service())
    except KeyboardInterrupt:
        logger.info("Docker watchdog service stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error in Docker watchdog: {e}", exc_info=True)
        sys.exit(1)
