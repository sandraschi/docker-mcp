"""
Docker Compose Manager for DockerMCP.

This module provides a high-level interface for managing Docker Compose projects.
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from docker import DockerClient
from docker.errors import DockerException
from pydantic import ValidationError

from dockermcp.logging_config import logger
from dockermcp.tools.compose.compose_models import (
    ComposeConfig,
    ComposeProject,
    ComposeResponse,
    ComposeService,
    ComposeVolume,
    ComposeNetwork,
)


class ComposeError(Exception):
    """Base exception for Docker Compose related errors."""
    pass


class ComposeManager:
    """Manager for Docker Compose operations."""

    def __init__(self, docker_client: Optional[DockerClient] = None):
        """Initialize the ComposeManager.
        
        Args:
            docker_client: Optional Docker client instance. If not provided,
                a new client will be created.
        """
        self.docker = docker_client
        self._compose_cmd = self._find_compose_cmd()
        self.logger = logger.getChild("compose")

    @staticmethod
    def _find_compose_cmd() -> str:
        """Find the appropriate docker-compose command.
        
        Returns:
            The docker-compose command to use (either 'docker compose' or 'docker-compose').
        """
        # Try 'docker compose' (newer versions)
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return "docker compose"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Fall back to 'docker-compose' (older versions)
        try:
            subprocess.run(
                ["docker-compose", "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return "docker-compose"
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            raise RuntimeError(
                "Neither 'docker compose' nor 'docker-compose' command found. "
                "Please ensure Docker Compose is installed and available in PATH."
            ) from e

    async def _run_compose_command(
        self,
        command: List[str],
        project_dir: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
    ) -> Tuple[int, str, str]:
        """Run a docker-compose command.
        
        Args:
            command: List of command arguments to pass to docker-compose.
            project_dir: Directory containing the docker-compose.yml file.
            env: Environment variables to set for the command.
            capture_output: Whether to capture and return command output.
            
        Returns:
            Tuple of (exit_code, stdout, stderr).
        """
        if project_dir:
            project_dir = Path(project_dir).resolve()
            if not project_dir.is_dir():
                raise ValueError(f"Project directory not found: {project_dir}")

        cmd = self._compose_cmd.split() + command
        
        self.logger.debug("Running command: %s", " ".join(cmd))
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project_dir) if project_dir else None,
            env=env or {},
            stdout=asyncio.subprocess.PIPE if capture_output else None,
            stderr=asyncio.subprocess.PIPE if capture_output else None,
        )
        
        if capture_output:
            stdout, stderr = await process.communicate()
            stdout = stdout.decode().strip() if stdout else ""
            stderr = stderr.decode().strip() if stderr else ""
            return process.returncode, stdout, stderr
        else:
            return process.returncode, "", ""

    async def up(
        self,
        project_name: str,
        file_path: Optional[Union[str, Path]] = None,
        build: bool = False,
        detach: bool = True,
        force_recreate: bool = False,
        no_recreate: bool = False,
        **kwargs: Any,
    ) -> ComposeResponse:
        """Start containers for a Compose project.
        
        Args:
            project_name: Name of the Compose project.
            file_path: Path to the docker-compose.yml file.
            build: Whether to build images before starting containers.
            detach: Run containers in the background.
            force_recreate: Recreate containers even if their configuration hasn't changed.
            no_recreate: Don't recreate containers that are already running.
            **kwargs: Additional arguments to pass to the docker-compose up command.
            
        Returns:
            ComposeResponse with the result of the operation.
        """
        cmd = ["up", "--project-name", project_name]
        
        if build:
            cmd.append("--build")
        if detach:
            cmd.append("-d")
        if force_recreate:
            cmd.append("--force-recreate")
        if no_recreate:
            cmd.append("--no-recreate")
            
        if file_path:
            cmd.extend(["-f", str(Path(file_path).resolve())])
            
        # Add any additional arguments
        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        
        exit_code, stdout, stderr = await self._run_compose_command(
            cmd, project_dir=Path(file_path).parent if file_path else None
        )
        
        response = ComposeResponse(
            success=exit_code == 0,
            message="Containers started successfully" if exit_code == 0 else "Failed to start containers",
            project_name=project_name,
            command="up",
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )
        
        return response

    # Add other Compose operations (down, build, logs, ps, etc.) as needed
    # The actual implementation would follow the same pattern as the 'up' method

    async def get_project_config(self, project_dir: Union[str, Path]) -> ComposeConfig:
        """Get the Compose configuration for a project.
        
        Args:
            project_dir: Directory containing the docker-compose.yml file.
            
        Returns:
            Parsed Compose configuration.
            
        Raises:
            ComposeError: If the configuration is invalid or cannot be loaded.
        """
        project_dir = Path(project_dir).resolve()
        config_path = project_dir / "docker-compose.yml"
        
        if not config_path.exists():
            raise ComposeError(f"docker-compose.yml not found in {project_dir}")
            
        try:
            # Use docker-compose config to parse and validate the file
            exit_code, stdout, stderr = await self._run_compose_command(
                ["config", "--format", "json"],
                project_dir=project_dir,
            )
            
            if exit_code != 0:
                raise ComposeError(f"Invalid Compose file: {stderr}")
                
            config_data = json.loads(stdout)
            return ComposeConfig(**config_data)
            
        except json.JSONDecodeError as e:
            raise ComposeError(f"Failed to parse Compose config: {e}") from e
        except ValidationError as e:
            raise ComposeError(f"Invalid Compose configuration: {e}") from e

    async def get_services(self, project_name: str) -> Dict[str, Dict[str, Any]]:
        """Get information about services in a Compose project.
        
        Args:
            project_name: Name of the Compose project.
            
        Returns:
            Dictionary mapping service names to their information.
        """
        exit_code, stdout, stderr = await self._run_compose_command(
            ["ps", "--format", "json", "--all"],
            project_dir=project_name,
        )
        
        if exit_code != 0:
            self.logger.warning("Failed to get services: %s", stderr)
            return {}
            
        try:
            containers = json.loads(stdout)
            return {container["Service"]: container for container in containers}
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error("Failed to parse service information: %s", e)
            return {}
