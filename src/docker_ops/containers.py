"""
Container Manager - Docker Container CRUD Operations
Part of Sandra's Docker MCP Server - Austrian Efficiency Edition

Handles all basic container lifecycle operations:
- List containers with enhanced formatting
- Create containers with intelligent defaults
- Start/stop/restart containers with error handling
- Get detailed container information
- Retrieve and format container logs
"""

import json
import subprocess
from datetime import UTC, datetime
from typing import Any

from .transport import run_server


class ContainerManager:
    """
    Manages Docker container operations with Austrian efficiency.
    Focus on reliability, clear error messages, and actionable results.
    """

    def __init__(self):
        self.docker_cmd = ["docker"]

    def _run_docker_command(self, args: list[str], timeout: int = 30) -> dict[str, Any]:
        """
        Execute Docker command with proper error handling.
        
        Args:
            args: Docker command arguments
            timeout: Command timeout in seconds
            
        Returns:
            Result dictionary with success/error information
        """
        try:
            cmd = self.docker_cmd + args
            result = run_server(subprocess, server_name="docker-mcp")

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
                "command": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {e!s}",
                "command": " ".join(cmd)
            }

    def list_containers(self, all_states: bool = True) -> dict[str, Any]:
        """
        List all Docker containers with enhanced formatting.
        
        Args:
            all_states: Include stopped containers
            
        Returns:
            Formatted container list with summary statistics
        """
        # Build command
        args = ["ps", "--format", "json"]
        if all_states:
            args.append("--all")

        result = self._run_docker_command(args)

        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", result.get("stderr", "Unknown error")),
                "containers": [],
                "summary": {"total": 0, "running": 0, "stopped": 0, "error": 0}
            }

        # Parse JSON output
        containers = []
        running_count = 0
        stopped_count = 0
        error_count = 0

        if result["stdout"]:
            for line in result["stdout"].split('\n'):
                if line.strip():
                    try:
                        container_data = json.loads(line)

                        # Enhanced container info
                        container_info = {
                            "id": container_data.get("ID", ""),
                            "name": container_data.get("Names", ""),
                            "image": container_data.get("Image", ""),
                            "status": container_data.get("Status", ""),
                            "state": container_data.get("State", ""),
                            "ports": container_data.get("Ports", ""),
                            "created": container_data.get("CreatedAt", ""),
                            "size": container_data.get("Size", "")
                        }

                        # Count by status
                        state = container_info["state"].lower()
                        if state == "running":
                            running_count += 1
                        elif state in ["exited", "stopped"]:
                            stopped_count += 1
                        else:
                            error_count += 1

                        containers.append(container_info)

                    except json.JSONDecodeError:
                        # Handle non-JSON lines
                        continue

        return {
            "success": True,
            "containers": containers,
            "summary": {
                "total": len(containers),
                "running": running_count,
                "stopped": stopped_count,
                "error": error_count
            },
            "timestamp": datetime.now(UTC).isoformat()
        }

    def get_container_info(self, container_name: str) -> dict[str, Any]:
        """
        Get detailed information about a specific container.
        
        Args:
            container_name: Container name or ID
            
        Returns:
            Detailed container information
        """
        result = self._run_docker_command(["inspect", container_name])

        if not result["success"]:
            return {
                "success": False,
                "error": f"Container '{container_name}' not found or inspect failed",
                "details": result.get("stderr", "")
            }

        try:
            inspect_data = json.loads(result["stdout"])
            if not inspect_data:
                return {
                    "success": False,
                    "error": f"No data returned for container '{container_name}'"
                }

            container_data = inspect_data[0]
            config = container_data.get("Config", {})
            state = container_data.get("State", {})
            network_settings = container_data.get("NetworkSettings", {})

            # Extract key information
            info = {
                "success": True,
                "id": container_data.get("Id", ""),
                "name": container_data.get("Name", "").lstrip("/"),
                "image": config.get("Image", ""),
                "status": state.get("Status", ""),
                "running": state.get("Running", False),
                "restart_count": state.get("RestartCount", 0),
                "created": container_data.get("Created", ""),
                "started": state.get("StartedAt", ""),
                "finished": state.get("FinishedAt", ""),
                "exit_code": state.get("ExitCode", None),
                "environment": config.get("Env", []),
                "ports": network_settings.get("Ports", {}),
                "networks": list(network_settings.get("Networks", {}).keys()),
                "mounts": container_data.get("Mounts", []),
                "labels": config.get("Labels", {}),
                "command": config.get("Cmd", []),
                "entrypoint": config.get("Entrypoint", [])
            }

            # Add restart policy
            restart_policy = container_data.get("HostConfig", {}).get("RestartPolicy", {})
            info["restart_policy"] = {
                "name": restart_policy.get("Name", "no"),
                "max_retry_count": restart_policy.get("MaximumRetryCount", 0)
            }

            # Calculate uptime if running
            if info["running"] and info["started"]:
                try:
                    started_time = datetime.fromisoformat(info["started"].replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(UTC) - started_time).total_seconds()
                    info["uptime_seconds"] = int(uptime_seconds)
                except:
                    info["uptime_seconds"] = None

            return info

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse container inspect data: {e!s}"
            }

    def create_container(
        self,
        image: str,
        name: str,
        ports: dict[str, str] | None = None,
        environment: dict[str, str] | None = None,
        volumes: dict[str, str] | None = None,
        network: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new Docker container with intelligent defaults.
        
        Args:
            image: Docker image name
            name: Container name
            ports: Port mappings {"container_port": "host_port"}
            environment: Environment variables
            volumes: Volume mounts {"host_path": "container_path"}
            network: Network to connect to
            
        Returns:
            Container creation result
        """
        args = ["create", "--name", name]

        # Add port mappings
        if ports:
            for container_port, host_port in ports.items():
                args.extend(["-p", f"{host_port}:{container_port}"])

        # Add environment variables
        if environment:
            for key, value in environment.items():
                args.extend(["-e", f"{key}={value}"])

        # Add volume mounts
        if volumes:
            for host_path, container_path in volumes.items():
                args.extend(["-v", f"{host_path}:{container_path}"])

        # Add network
        if network:
            args.extend(["--network", network])

        # Add image
        args.append(image)

        result = self._run_docker_command(args)

        if result["success"]:
            container_id = result["stdout"]
            return {
                "success": True,
                "container_id": container_id,
                "name": name,
                "image": image,
                "message": f"Container '{name}' created successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to create container '{name}'",
                "details": result.get("stderr", "Unknown error")
            }

    def start_container(self, container_name: str) -> dict[str, Any]:
        """
        Start a stopped container.
        
        Args:
            container_name: Container name or ID
            
        Returns:
            Start operation result
        """
        result = self._run_docker_command(["start", container_name])

        if result["success"]:
            return {
                "success": True,
                "container": container_name,
                "message": f"Container '{container_name}' started successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to start container '{container_name}'",
                "details": result.get("stderr", "Unknown error")
            }

    def stop_container(self, container_name: str, timeout: int = 10) -> dict[str, Any]:
        """
        Stop a running container gracefully.
        
        Args:
            container_name: Container name or ID
            timeout: Seconds to wait before force killing
            
        Returns:
            Stop operation result
        """
        args = ["stop"]
        if timeout != 10:  # Only add if not default
            args.extend(["--time", str(timeout)])
        args.append(container_name)

        result = self._run_docker_command(args, timeout + 10)  # Add buffer

        if result["success"]:
            return {
                "success": True,
                "container": container_name,
                "message": f"Container '{container_name}' stopped successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to stop container '{container_name}'",
                "details": result.get("stderr", "Unknown error")
            }

    def restart_container(self, container_name: str) -> dict[str, Any]:
        """
        Restart a container (stop + start).
        
        Args:
            container_name: Container name or ID
            
        Returns:
            Restart operation result
        """
        result = self._run_docker_command(["restart", container_name])

        if result["success"]:
            return {
                "success": True,
                "container": container_name,
                "message": f"Container '{container_name}' restarted successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to restart container '{container_name}'",
                "details": result.get("stderr", "Unknown error")
            }

    def remove_container(self, container_name: str, force: bool = False) -> dict[str, Any]:
        """
        Remove a container.
        
        Args:
            container_name: Container name or ID
            force: Force removal of running container
            
        Returns:
            Remove operation result
        """
        args = ["rm"]
        if force:
            args.append("--force")
        args.append(container_name)

        result = self._run_docker_command(args)

        if result["success"]:
            return {
                "success": True,
                "container": container_name,
                "message": f"Container '{container_name}' removed successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to remove container '{container_name}'",
                "details": result.get("stderr", "Unknown error")
            }

    def get_container_logs(
        self,
        container_name: str,
        lines: int = 100,
        follow: bool = False,
        timestamps: bool = True
    ) -> dict[str, Any]:
        """
        Get container logs with formatting and error highlighting.
        
        Args:
            container_name: Container name or ID
            lines: Number of recent lines to retrieve
            follow: Stream logs (not recommended for MCP)
            timestamps: Include timestamps
            
        Returns:
            Container logs with metadata
        """
        args = ["logs"]

        if timestamps:
            args.append("--timestamps")

        if lines > 0:
            args.extend(["--tail", str(lines)])

        if follow:
            args.append("--follow")

        args.append(container_name)

        # Use longer timeout for logs
        result = self._run_docker_command(args, timeout=60)

        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to get logs for container '{container_name}'",
                "details": result.get("stderr", "Unknown error")
            }

        # Process logs
        log_lines = result["stdout"].split('\n') if result["stdout"] else []

        # Analyze logs for errors and warnings
        error_count = 0
        warning_count = 0
        recent_errors = []

        for line in log_lines[-50:]:  # Check last 50 lines for errors
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['error', 'exception', 'failed', 'fatal']):
                error_count += 1
                if len(recent_errors) < 10:  # Limit recent errors
                    recent_errors.append(line)
            elif any(keyword in line_lower for keyword in ['warning', 'warn']):
                warning_count += 1

        return {
            "success": True,
            "container": container_name,
            "logs": result["stdout"],
            "line_count": len(log_lines),
            "analysis": {
                "error_count": error_count,
                "warning_count": warning_count,
                "recent_errors": recent_errors,
                "has_recent_activity": len([l for l in log_lines[-10:] if l.strip()]) > 0
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
