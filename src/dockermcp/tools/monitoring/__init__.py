"""
Monitoring Tools for DockerMCP

This module provides tools for managing the monitoring stack (Prometheus, Grafana, Loki, etc.).
"""
import subprocess
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from dockermcp.exceptions import DockerOperationError
from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp


class CommandResult(BaseModel):
    """Result of a shell command execution."""
    status: Literal["success", "error"]
    returncode: int
    stdout: str
    stderr: str
    command: str

class MonitoringResponse(BaseModel):
    """Standard response model for monitoring operations."""
    status: Literal["success", "error"]
    message: str
    details: dict[str, Any] | None = Field(default_factory=dict)
    error: str | None = None

class MonitoringManager:
    """Manages the monitoring stack."""

    def __init__(self):
        self.monitoring_dir = Path(__file__).parent.parent.parent.parent.parent / "monitoring"
        self.compose_file = self.monitoring_dir / "docker-compose-monitoring.yml"
        self.compose_cmd = ["docker", "compose", "-f", str(self.compose_file)]

    def run_command(self, cmd: list[str]) -> CommandResult:
        """
        Run a shell command and return the result.

        Args:
            cmd: List of command arguments

        Returns:
            CommandResult with the command execution details

        Raises:
            DockerOperationError: If the command fails
        """
        try:
            logger.debug(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(  # noqa: S603
                cmd,
                cwd=str(self.monitoring_dir),
                capture_output=True,
                text=True,
                check=False
            )

            cmd_result = CommandResult(
                status="success" if result.returncode == 0 else "error",
                returncode=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                command=" ".join(cmd)
            )

            if cmd_result.status == "error":
                logger.error(
                    f"Command failed with code {cmd_result.returncode}: {cmd_result.stderr}"
                )

            return cmd_result

        except Exception as e:
            error_msg = f"Error executing command: {e!s}"
            logger.exception(error_msg)
            raise DockerOperationError(error_msg) from e

    def start_services(self, build: bool = False) -> CommandResult:
        """
        Start the monitoring services.

        Args:
            build: Whether to build images before starting

        Returns:
            CommandResult with the command execution details
        """
        cmd = [*self.compose_cmd, "up", "--detach"]
        if build:
            cmd.append("--build")
        return self.run_command(cmd)

    def stop_services(self, remove_volumes: bool = False, timeout: int = 10) -> CommandResult:
        """
        Stop the monitoring services.

        Args:
            remove_volumes: Whether to remove volumes
            timeout: Timeout in seconds before killing containers

        Returns:
            CommandResult with the command execution details
        """
        cmd = [*self.compose_cmd, "down", f"--timeout={timeout}"]
        if remove_volumes:
            cmd.append("--volumes")
        return self.run_command(cmd)

    def restart_services(self, build: bool = False) -> CommandResult:
        """
        Restart the monitoring services.

        Args:
            build: Whether to rebuild images before starting

        Returns:
            CommandResult with the command execution details
        """
        self.stop_services()
        return self.start_services(build=build)

    def get_status(self, all_containers: bool = True) -> CommandResult:
        """
        Get the status of monitoring services.

        Args:
            all_containers: Whether to show all containers (including stopped ones)

        Returns:
            CommandResult with the command execution details
        """
        cmd = [*self.compose_cmd, "ps", "--all"] if all_containers else [*self.compose_cmd, "ps"]
        return self.run_command(cmd)

    def get_logs(
        self,
        service: str | None = None,
        tail: int = 100,
        follow: bool = False,
        timestamps: bool = False
    ) -> CommandResult:
        """
        Get logs from monitoring services.

        Args:
            service: Optional service name to get logs for
            tail: Number of lines to show from the end
            follow: Follow log output
            timestamps: Include timestamps

        Returns:
            CommandResult with the command execution details
        """
        cmd = [*self.compose_cmd, "logs", f"--tail={tail}"]

        if follow:
            cmd.append("--follow")
        if timestamps:
            cmd.append("--timestamps")
        if service:
            cmd.append(service)

        return self.run_command(cmd)

# Create a singleton instance
monitoring_manager = MonitoringManager()

class StartMonitoringParams(BaseModel):
    """Parameters for starting the monitoring stack."""
    build: Annotated[bool, Field(
        default=False,
        description="Whether to rebuild the container images"
    )] = False

@mcp.tool
async def start_monitoring(params: StartMonitoringParams) -> MonitoringResponse:
    """
    Start the monitoring stack including Prometheus, Grafana, Loki, and other services.

    Args:
        params: StartMonitoringParams containing the build flag

    Returns:
        MonitoringResponse with the result of the operation

    Example:
        >>> await start_monitoring(StartMonitoringParams(build=True))
        {
            'status': 'success',
            'message': 'Monitoring services started',
            'details': {
                'services': ['prometheus', 'grafana', 'loki', 'promtail', 'redis'],
                'output': '...'
            }
        }
    """
    try:
        result = monitoring_manager.start_services(build=params.build)

        if result.status == "success":
            return MonitoringResponse(
                status="success",
                message="Monitoring services started successfully",
                details={
                    "services": ["prometheus", "grafana", "loki", "promtail", "redis"],
                    "output": result.stdout
                }
            ).model_dump()

        return MonitoringResponse(
            status="error",
            message="Failed to start monitoring services",
            error=result.stderr or "Unknown error",
            details={
                "command": result.command,
                "returncode": result.returncode,
                "output": result.stdout
            }
        ).model_dump()

    except Exception as e:
        logger.exception("Error starting monitoring services")
        return MonitoringResponse(
            status="error",
            message="Failed to start monitoring services",
            error=str(e)
        ).model_dump()

class StopMonitoringParams(BaseModel):
    """Parameters for stopping the monitoring stack."""
    remove_volumes: Annotated[bool, Field(
        default=False,
        description="Whether to remove volumes when stopping"
    )] = False

    timeout: Annotated[int, Field(
        default=10,
        ge=1,
        le=300,
        description="Timeout in seconds before killing containers"
    )] = 10

@mcp.tool
async def stop_monitoring(params: StopMonitoringParams) -> MonitoringResponse:
    """
    Stop the monitoring stack.

    Args:
        params: StopMonitoringParams containing stop options

    Returns:
        MonitoringResponse with the result of the operation

    Example:
        >>> await stop_monitoring(StopMonitoringParams(remove_volumes=True, timeout=30))
        {
            'status': 'success',
            'message': 'Monitoring services stopped',
            'details': {
                'volumes_removed': True,
                'output': '...'
            }
        }
    """
    try:
        result = monitoring_manager.stop_services(
            remove_volumes=params.remove_volumes,
            timeout=params.timeout
        )

        if result.status == "success":
            return MonitoringResponse(
                status="success",
                message="Monitoring services stopped successfully",
                details={
                    "volumes_removed": params.remove_volumes,
                    "output": result.stdout
                }
            ).model_dump()

        return MonitoringResponse(
            status="error",
            message="Failed to stop monitoring services",
            error=result.stderr or "Unknown error",
            details={
                "command": result.command,
                "returncode": result.returncode,
                "output": result.stdout
            }
        ).model_dump()

    except Exception as e:
        logger.exception("Error stopping monitoring services")
        return MonitoringResponse(
            status="error",
            message="Failed to stop monitoring services",
            error=str(e)
        ).model_dump()

class MonitoringStatusParams(BaseModel):
    """Parameters for getting monitoring status."""
    detailed: Annotated[bool, Field(
        default=False,
        description="Whether to include detailed container information"
    )] = False

    all_containers: Annotated[bool, Field(
        default=True,
        description="Whether to include stopped containers"
    )] = True

@mcp.tool
async def monitoring_status(params: MonitoringStatusParams) -> MonitoringResponse:
    """
    Get the status of monitoring stack services.

    Args:
        params: MonitoringStatusParams containing status options

    Returns:
        MonitoringResponse with the status of monitoring services

    Example:
        >>> await monitoring_status(MonitoringStatusParams(detailed=True))
        {
            'status': 'success',
            'message': 'Found 5 monitoring services',
            'details': {
                'services': [
                    {
                        'name': 'prometheus',
                        'status': 'running',
                        'ports': '0.0.0.0:9090->9090/tcp'
                    },
                    ...
                ]
            }
        }
    """
    try:
        if params.detailed:
            result = monitoring_manager.run_command(
                ["docker", "ps", "--filter", "name=monitoring_", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"]
            )

            if result.status != "success":
                return MonitoringResponse(
                    status="error",
                    message="Failed to get detailed monitoring status",
                    error=result.stderr or "Unknown error",
                    details={
                        "command": result.command,
                        "returncode": result.returncode
                    }
                ).model_dump()

            # Parse the detailed output
            services = []
            for line in result.stdout.splitlines():
                if "|" in line:
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        name, status, ports = parts
                        services.append({
                            "name": name,
                            "status": status.lower(),
                            "ports": ports
                        })
        else:
            result = monitoring_manager.get_status(all_containers=params.all_containers)

            if result.status != "success":
                return MonitoringResponse(
                    status="error",
                    message="Failed to get monitoring status",
                    error=result.stderr or "Unknown error",
                    details={
                        "command": result.command,
                        "returncode": result.returncode
                    }
                ).model_dump()

            # Parse the standard output
            services = []
            for line in result.stdout.splitlines():
                if not line.strip() or ('NAME' in line and 'STATUS' in line):
                    continue

                parts = line.split()
                if len(parts) >= 4:
                    service = {
                        'name': parts[0],
                        'status': parts[3].lower(),
                        'ports': ' '.join(parts[4:]) if len(parts) > 4 else ''
                    }
                    services.append(service)

        return MonitoringResponse(
            status="success",
            message=f"Found {len(services)} monitoring services",
            details={
                "services": services or [{"error": "No monitoring services found or not running"}],
                "raw_output": result.stdout if params.detailed else None
            }
        ).model_dump()

    except Exception as e:
        logger.exception("Error getting monitoring status")
        return MonitoringResponse(
            status="error",
            message="Failed to get monitoring status",
            error=str(e)
        ).model_dump()

class MonitoringLogsParams(BaseModel):
    """Parameters for getting monitoring logs."""
    service: Annotated[str | None, Field(
        default=None,
        description="Name of the service to get logs from (optional)"
    )] = None

    tail: Annotated[int, Field(
        default=100,
        ge=1,
        le=10000,
        description="Number of lines to show from the end of the logs"
    )] = 100

    follow: Annotated[bool, Field(
        default=False,
        description="Whether to follow the log output"
    )] = False

    timestamps: Annotated[bool, Field(
        default=False,
        description="Whether to include timestamps in logs"
    )] = False

@mcp.tool
async def monitoring_logs(params: MonitoringLogsParams) -> MonitoringResponse:
    """
    Get logs from monitoring services.

    Args:
        params: MonitoringLogsParams containing log retrieval options

    Returns:
        MonitoringResponse with the logs and metadata

    Example:
        >>> await monitoring_logs(MonitoringLogsParams(
        ...     service="grafana",
        ...     tail=50,
        ...     timestamps=True
        ... ))
        {
            'status': 'success',
            'message': 'Retrieved 50 log lines',
            'details': {
                'service': 'grafana',
                'lines_returned': 50,
                'follow': False,
                'timestamps': True
            }
        }
    """
    try:
        result = monitoring_manager.get_logs(
            service=params.service,
            tail=params.tail,
            follow=params.follow,
            timestamps=params.timestamps
        )

        if result.status == "success":
            lines = len(result.stdout.splitlines()) if result.stdout else 0

            return MonitoringResponse(
                status="success",
                message=f"Retrieved {lines} log lines" if not params.follow else "Following logs...",
                details={
                    "service": params.service or "all",
                    "lines_returned": lines,
                    "follow": params.follow,
                    "timestamps": params.timestamps
                }
            ).model_dump()

        return MonitoringResponse(
            status="error",
            message="Failed to retrieve logs",
            error=result.stderr or "Unknown error",
            details={
                "command": result.command,
                "returncode": result.returncode
            }
        ).model_dump()

    except Exception as e:
        logger.exception("Error retrieving logs")
        return MonitoringResponse(
            status="error",
            message="Failed to retrieve logs",
            error=str(e)
        ).model_dump()
