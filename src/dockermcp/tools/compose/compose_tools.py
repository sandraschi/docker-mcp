"""
Docker Compose Tools for DockerMCP.

This module provides FastMCP 2.11.3 compatible tools for managing Docker Compose applications.
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, AsyncGenerator

from fastmcp.tools import Tool
from pydantic import ValidationError

from dockermcp.core.compose import ComposeManager
from dockermcp.tools.compose.compose_models import (
    ComposeProject, ComposeService, ComposeVolume, ComposeNetwork, ComposeConfig,
    ComposeUpRequest, ComposeDownRequest, ComposeBuildRequest, 
    ComposeLogsRequest, ComposePsRequest, ComposeResponse,
    ComposeServiceState, ComposeHealthStatus, ComposeRestartPolicy,
    ComposeDeploymentMode, ComposeVolumeType, ComposeNetworkDriver
)
from dockermcp.utils.helpers import format_size, parse_size, human_readable_to_bytes

# Configure logging
logger = logging.getLogger(__name__)

# Initialize compose manager
compose_mgr = ComposeManager()

def _get_compose_files(request) -> List[str]:
    """Get the list of Compose files from the request."""
    files = []
    if hasattr(request, 'file_path') and request.file_path:
        files.append(request.file_path)
    if hasattr(request, 'files') and request.files:
        files.extend(request.files)
    return files if files else None

def _get_env_files(request) -> List[str]:
    """Get the list of environment files from the request."""
    env_files = []
    if hasattr(request, 'env_file') and request.env_file:
        env_files.append(request.env_file)
    if hasattr(request, 'env_files') and request.env_files:
        env_files.extend(request.env_files)
    return env_files if env_files else None

def _build_compose_command(
    base_cmd: str,
    request: Any,
    additional_args: Optional[List[str]] = None
) -> List[str]:
    """Build a Docker Compose command with common options."""
    cmd = ["docker-compose", "--project-name", request.project_name]
    
    # Add compose files
    files = _get_compose_files(request)
    if files:
        for f in files:
            cmd.extend(["-f", f])
    
    # Add environment files
    env_files = _get_env_files(request)
    if env_files:
        for env_file in env_files:
            cmd.extend(["--env-file", env_file])
    
    # Add the base command
    cmd.append(base_cmd)
    
    # Add additional arguments
    if additional_args:
        cmd.extend(additional_args)
    
    # Add services if specified
    if hasattr(request, 'services') and request.services:
        cmd.extend(request.services)
    
    return cmd

@Tool(
    name="compose_up",
    description="Create and start containers for a Docker Compose project"
)
async def compose_up(request: ComposeUpRequest) -> Dict[str, Any]:
    """
    Create and start containers for a Docker Compose project.
    
    This command builds, (re)creates, and starts containers for all services
    defined in the Compose file, or for the specified services.
    """
    start_time = datetime.utcnow()
    response = ComposeResponse(
        success=False,
        message="Compose up command started",
        project_name=request.project_name,
        command="up",
        start_time=start_time
    )
    
    try:
        # Build the command
        cmd_args = []
        
        if request.detach:
            cmd_args.append("-d")
        if request.build:
            cmd_args.append("--build")
        if request.no_build:
            cmd_args.append("--no-build")
        if request.force_recreate:
            cmd_args.append("--force-recreate")
        if request.always_recreate_deps:
            cmd_args.append("--always-recreate-deps")
        if request.no_recreate:
            cmd_args.append("--no-recreate")
        if request.renew_anon_volumes:
            cmd_args.append("-V")
        if request.remove_orphans:
            cmd_args.append("--remove-orphans")
        if request.no_deps:
            cmd_args.append("--no-deps")
        if request.timeout:
            cmd_args.extend(["--timeout", str(request.timeout)])
        if request.exit_code_from:
            cmd_args.extend(["--exit-code-from", request.exit_code_from])
        if request.scale:
            for service, num in request.scale.items():
                cmd_args.extend(["--scale", f"{service}={num}"])
        if request.no_color:
            cmd_args.append("--no-color")
        if request.quiet_pull:
            cmd_args.append("--quiet-pull")
        if request.no_log_prefix:
            cmd_args.append("--no-log-prefix")
        if request.log_level:
            cmd_args.extend(["--log-level", request.log_level])
        if request.json:
            cmd_args.append("--json")
        if request.parallel:
            cmd_args.extend(["--parallel", str(request.parallel)])
        if request.dry_run:
            cmd_args.append("--dry-run")
        
        # Add profiles if specified
        if hasattr(request, 'profiles') and request.profiles:
            cmd_args.extend(["--profile", ",".join(request.profiles)])
        
        # Execute the command
        cmd = _build_compose_command("up", request, cmd_args)
        
        if request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        # Update response
        response.success = exit_code == 0
        response.exit_code = exit_code
        response.stdout = stdout.decode() if stdout else None
        response.stderr = stderr.decode() if stderr else None
        response.end_time = datetime.utcnow()
        
        if exit_code == 0:
            response.message = "Compose up completed successfully"
            
            # Get container status
            ps_request = ComposePsRequest(
                project_name=request.project_name,
                file_path=request.file_path,
                files=request.files,
                all=True
            )
            ps_result = await compose_ps(ps_request)
            
            if ps_result.get('success'):
                response.services = ps_result.get('services', {})
        else:
            response.message = f"Compose up failed with exit code {exit_code}"
            response.errors = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.end_time = datetime.utcnow()
        response.success = False
        response.message = f"Error during compose up: {str(e)}"
        response.errors = [{
            "code": "COMPOSE_UP_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_up: {str(e)}", exc_info=True)
    
    return response.dict()

@Tool(
    name="compose_down",
    description="Stop and remove containers, networks, and volumes for a Docker Compose project"
)
async def compose_down(request: ComposeDownRequest) -> Dict[str, Any]:
    """
    Stop and remove containers, networks, and volumes for a Docker Compose project.
    
    This command stops and removes all the resources created by `compose up`.
    """
    start_time = datetime.utcnow()
    response = ComposeResponse(
        success=False,
        message="Compose down command started",
        project_name=request.project_name,
        command="down",
        start_time=start_time
    )
    
    try:
        # Build the command
        cmd_args = []
        
        if request.remove_orphans:
            cmd_args.append("--remove-orphans")
        if request.rmi:
            cmd_args.extend(["--rmi", request.rmi])
        if request.timeout:
            cmd_args.extend(["--timeout", str(request.timeout)])
        if request.volumes:
            cmd_args.append("--volumes")
        if request.remove_volumes:
            cmd_args.append("-v")
        if request.remove_all:
            cmd_args.append("--rmi=all")
        if request.dry_run:
            cmd_args.append("--dry-run")
        
        # Execute the command
        cmd = _build_compose_command("down", request, cmd_args)
        
        if request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        # Update response
        response.success = exit_code == 0
        response.exit_code = exit_code
        response.stdout = stdout.decode() if stdout else None
        response.stderr = stderr.decode() if stderr else None
        response.end_time = datetime.utcnow()
        
        if exit_code == 0:
            response.message = "Compose down completed successfully"
        else:
            response.message = f"Compose down failed with exit code {exit_code}"
            response.errors = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.end_time = datetime.utcnow()
        response.success = False
        response.message = f"Error during compose down: {str(e)}"
        response.errors = [{
            "code": "COMPOSE_DOWN_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_down: {str(e)}", exc_info=True)
    
    return response.dict()

@Tool(
    name="compose_build",
    description="Build or rebuild services defined in a Docker Compose file"
)
async def compose_build(request: ComposeBuildRequest) -> Dict[str, Any]:
    """
    Build or rebuild services defined in a Docker Compose file.
    
    This command builds Docker images for services that have a `build` section
    in the Compose file, or for the specified services.
    """
    start_time = datetime.utcnow()
    response = ComposeResponse(
        success=False,
        message="Compose build command started",
        project_name=request.project_name,
        command="build",
        start_time=start_time
    )
    
    try:
        # Build the command
        cmd_args = []
        
        if request.no_cache:
            cmd_args.append("--no-cache")
        if request.pull:
            cmd_args.append("--pull")
        if request.force_rm:
            cmd_args.append("--force-rm")
        if request.memory:
            cmd_args.extend(["--memory", request.memory])
        if request.build_args:
            for k, v in request.build_args.items():
                cmd_args.extend(["--build-arg", f"{k}={v}"])
        if request.compress:
            cmd_args.append("--compress")
        if not request.parallel:
            cmd_args.append("--no-parallel")
        if request.progress:
            cmd_args.extend(["--progress", request.progress])
        if request.quiet:
            cmd_args.append("--quiet")
        if request.no_rm:
            cmd_args.append("--no-rm")
        if request.dry_run:
            cmd_args.append("--dry-run")
        
        # Execute the command
        cmd = _build_compose_command("build", request, cmd_args)
        
        if request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        # Update response
        response.success = exit_code == 0
        response.exit_code = exit_code
        response.stdout = stdout.decode() if stdout else None
        response.stderr = stderr.decode() if stderr else None
        response.end_time = datetime.utcnow()
        
        if exit_code == 0:
            response.message = "Compose build completed successfully"
        else:
            response.message = f"Compose build failed with exit code {exit_code}"
            response.errors = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.end_time = datetime.utcnow()
        response.success = False
        response.message = f"Error during compose build: {str(e)}"
        response.errors = [{
            "code": "COMPOSE_BUILD_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_build: {str(e)}", exc_info=True)
    
    return response.dict()

@Tool(
    name="compose_logs",
    description="View output from containers in a Docker Compose project"
)
async def compose_logs(request: ComposeLogsRequest) -> Dict[str, Any]:
    """
    View output from containers in a Docker Compose project.
    
    This command shows the logs for all services or the specified services.
    """
    start_time = datetime.utcnow()
    response = ComposeResponse(
        success=False,
        message="Compose logs command started",
        project_name=request.project_name,
        command="logs",
        start_time=start_time
    )
    
    try:
        # Build the command
        cmd_args = []
        
        if request.follow:
            cmd_args.append("--follow")
        if request.tail:
            cmd_args.extend(["--tail", str(request.tail)])
        if request.no_color:
            cmd_args.append("--no-color")
        if request.no_log_prefix:
            cmd_args.append("--no-log-prefix")
        if request.since:
            cmd_args.extend(["--since", request.since])
        if request.until:
            cmd_args.extend(["--until", request.until])
        if request.timestamps:
            cmd_args.append("--timestamps")
        if request.dry_run:
            cmd_args.append("--dry-run")
        
        # Execute the command
        cmd = _build_compose_command("logs", request, cmd_args)
        
        if request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # For follow mode, we need to stream the output
        if request.follow:
            # Start a background task to read the output
            async def read_stream(stream, is_stdout=True):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line = line.decode().strip()
                    if is_stdout:
                        print(line)
                    else:
                        print(f"[stderr] {line}", file=sys.stderr)
            
            # Start reading from both streams
            stdout_task = asyncio.create_task(read_stream(process.stdout, True))
            stderr_task = asyncio.create_task(read_stream(process.stderr, False))
            
            # Wait for both tasks to complete
            await asyncio.gather(stdout_task, stderr_task)
            
            # Get the exit code
            exit_code = await process.wait()
            stdout, stderr = "", ""  # Streamed to console
        else:
            # For non-follow mode, just wait for the process to complete
            stdout, stderr = await process.communicate()
            exit_code = process.returncode
        
        # Update response
        response.success = exit_code == 0
        response.exit_code = exit_code
        
        # Only include stdout/stderr if not in follow mode
        if not request.follow:
            response.stdout = stdout.decode() if stdout else None
            response.stderr = stderr.decode() if stderr else None
        
        response.end_time = datetime.utcnow()
        
        if exit_code == 0:
            response.message = "Compose logs retrieved successfully"
        else:
            response.message = f"Failed to retrieve compose logs with exit code {exit_code}"
            response.errors = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.end_time = datetime.utcnow()
        response.success = False
        response.message = f"Error retrieving compose logs: {str(e)}"
        response.errors = [{
            "code": "COMPOSE_LOGS_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_logs: {str(e)}", exc_info=True)
    
    return response.dict()

@Tool(
    name="compose_ps",
    description="List containers for a Docker Compose project"
)
async def compose_ps(request: ComposePsRequest) -> Dict[str, Any]:
    """
    List containers for a Docker Compose project.
    
    This command shows the status of all containers or the specified services.
    """
    start_time = datetime.utcnow()
    response = ComposeResponse(
        success=False,
        message="Compose ps command started",
        project_name=request.project_name,
        command="ps",
        start_time=start_time
    )
    
    try:
        # Build the command
        cmd_args = []
        
        if request.all:
            cmd_args.append("-a")
        if request.filter:
            cmd_args.extend(["--filter", request.filter])
        if request.format:
            cmd_args.extend(["--format", request.format])
        if request.quiet:
            cmd_args.append("-q")
        if request.status:
            cmd_args.extend(["--status", ",".join(request.status)])
        if request.dry_run:
            cmd_args.append("--dry-run")
        
        # Execute the command
        cmd = _build_compose_command("ps", request, cmd_args)
        
        if request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        # Parse the output if successful
        services = {}
        if exit_code == 0 and stdout:
            lines = stdout.decode().splitlines()
            
            # Simple parsing of the output (this can be enhanced based on the format)
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 4:
                    service_name = parts[0]
                    container_id = parts[0][:12]  # Short ID
                    status = " ".join(parts[1:-2])
                    ports = parts[-1]
                    
                    services[service_name] = {
                        "container_id": container_id,
                        "status": status,
                        "ports": ports,
                        "name": service_name
                    }
        
        # Update response
        response.success = exit_code == 0
        response.exit_code = exit_code
        response.stdout = stdout.decode() if stdout else None
        response.stderr = stderr.decode() if stderr else None
        response.services = services
        response.end_time = datetime.utcnow()
        
        if exit_code == 0:
            response.message = f"Found {len(services)} containers"
        else:
            response.message = f"Failed to list containers with exit code {exit_code}"
            response.errors = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.end_time = datetime.utcnow()
        response.success = False
        response.message = f"Error listing containers: {str(e)}"
        response.errors = [{
            "code": "COMPOSE_PS_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_ps: {str(e)}", exc_info=True)
    
    return response.dict()

@Tool(
    name="compose_config",
    description="Validate and view the Compose file configuration"
)
async def compose_config(project_name: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate and view the Compose file configuration.
    
    This command parses the Compose file and returns the combined configuration.
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose config command started",
        "project_name": project_name,
        "command": "config",
        "start_time": start_time.isoformat(),
        "config": None
    }
    
    try:
        # Build the command
        cmd = ["docker-compose", "--project-name", project_name]
        
        if file_path:
            cmd.extend(["-f", file_path])
        
        cmd.append("config")
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        # Parse the output
        config = None
        if exit_code == 0 and stdout:
            try:
                config = yaml.safe_load(stdout)
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse compose config: {str(e)}")
                config = stdout.decode()
        
        # Update response
        response.update({
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout.decode() if stdout else None,
            "stderr": stderr.decode() if stderr else None,
            "config": config,
            "end_time": datetime.utcnow().isoformat()
        })
        
        if exit_code == 0:
            response["message"] = "Compose config retrieved successfully"
        else:
            response["message"] = f"Failed to retrieve compose config with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.update({
            "end_time": datetime.utcnow().isoformat(),
            "success": False,
            "message": f"Error retrieving compose config: {str(e)}",
            "errors": [{
                "code": "COMPOSE_CONFIG_ERROR",
                "message": str(e)
            }]
        })
        logger.error(f"Error in compose_config: {str(e)}", exc_info=True)
    
    return response

@Tool(
    name="compose_exec",
    description="Execute a command in a running container"
)
async def compose_exec(
    project_name: str,
    service: str,
    command: Union[str, List[str]],
    file_path: Optional[str] = None,
    detach: bool = False,
    privileged: bool = False,
    user: Optional[str] = None,
    workdir: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    index: int = 1
) -> Dict[str, Any]:
    """
    Execute a command in a running container.
    
    This command runs a command in a running service container.
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose exec command started",
        "project_name": project_name,
        "service": service,
        "command": "exec",
        "start_time": start_time.isoformat(),
        "exit_code": None,
        "stdout": None,
        "stderr": None
    }
    
    try:
        # Build the command
        cmd = ["docker-compose", "--project-name", project_name]
        
        if file_path:
            cmd.extend(["-f", file_path])
        
        cmd.append("exec")
        
        if detach:
            cmd.append("-d")
        if privileged:
            cmd.append("--privileged")
        if user:
            cmd.extend(["-u", user])
        if workdir:
            cmd.extend(["-w", workdir])
        if env:
            for k, v in env.items():
                cmd.extend(["-e", f"{k}={v}"])
        if index > 1:
            cmd.extend(["--index", str(index)])
        
        # Add the service and command
        cmd.append(service)
        
        # Handle both string and list commands
        if isinstance(command, str):
            cmd.extend(["sh", "-c", command])
        else:
            cmd.extend(command)
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        # Update response
        response.update({
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout.decode() if stdout else None,
            "stderr": stderr.decode() if stderr else None,
            "end_time": datetime.utcnow().isoformat()
        })
        
        if exit_code == 0:
            response["message"] = "Command executed successfully"
        else:
            response["message"] = f"Command failed with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.update({
            "end_time": datetime.utcnow().isoformat(),
            "success": False,
            "message": f"Error executing command: {str(e)}",
            "errors": [{
                "code": "COMPOSE_EXEC_ERROR",
                "message": str(e)
            }]
        })
        logger.error(f"Error in compose_exec: {str(e)}", exc_info=True)
    
    return response

@Tool(
    name="compose_run",
    description="Run a one-off command in a new container"
)
async def compose_run(
    project_name: str,
    service: str,
    command: Optional[Union[str, List[str]]] = None,
    file_path: Optional[str] = None,
    detach: bool = False,
    rm: bool = True,
    service_ports: bool = False,
    use_aliases: bool = False,
    name: Optional[str] = None,
    entrypoint: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    volume: Optional[List[str]] = None,
    workdir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a one-off command in a new container.
    
    This command runs a one-time command against a service.
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose run command started",
        "project_name": project_name,
        "service": service,
        "command": "run",
        "start_time": start_time.isoformat(),
        "exit_code": None,
        "stdout": None,
        "stderr": None
    }
    
    try:
        # Build the command
        cmd = ["docker-compose", "--project-name", project_name]
        
        if file_path:
            cmd.extend(["-f", file_path])
        
        cmd.append("run")
        
        if detach:
            cmd.append("-d")
        if rm:
            cmd.append("--rm")
        if service_ports:
            cmd.append("--service-ports")
        if use_aliases:
            cmd.append("--use-aliases")
        if name:
            cmd.extend(["--name", name])
        if entrypoint:
            cmd.extend(["--entrypoint", entrypoint])
        if env:
            for k, v in env.items():
                cmd.extend(["-e", f"{k}={v}"])
        if volume:
            for v in volume:
                cmd.extend(["-v", v])
        if workdir:
            cmd.extend(["-w", workdir])
        
        # Add the service
        cmd.append(service)
        
        # Add the command if provided
        if command:
            if isinstance(command, str):
                cmd.extend(["sh", "-c", command])
            else:
                cmd.extend(command)
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        # Update response
        response.update({
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout.decode() if stdout else None,
            "stderr": stderr.decode() if stderr else None,
            "end_time": datetime.utcnow().isoformat()
        })
        
        if exit_code == 0:
            response["message"] = "Command executed successfully"
        else:
            response["message"] = f"Command failed with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": stderr.decode() if stderr else "Unknown error"
            }]
        
    except Exception as e:
        response.update({
            "end_time": datetime.utcnow().isoformat(),
            "success": False,
            "message": f"Error executing command: {str(e)}",
            "errors": [{
                "code": "COMPOSE_RUN_ERROR",
                "message": str(e)
            }]
        })
        logger.error(f"Error in compose_run: {str(e)}", exc_info=True)
    
    return response
