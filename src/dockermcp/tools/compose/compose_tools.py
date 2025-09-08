"""
Docker Compose Tools for DockerMCP.

This module provides FastMCP 2.12 compatible tools for managing Docker Compose applications.
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
import yaml

from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Import FastMCP components
from fastmcp import FastMCP
from pydantic import ValidationError

from dockermcp.core.compose import ComposeManager

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastMCP instance
mcp = FastMCP("docker-compose")

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

@mcp.tool
def compose_up(request: dict) -> Dict[str, Any]:
    """
    Create and start containers for a Docker Compose project.
    
    This command builds, (re)creates, and starts containers for all services
    defined in the Compose file, or for the specified services.
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose up command started",
        "project_name": request.get("project_name", "unknown"),
        "command": "up",
        "start_time": start_time
    }
    
    try:
        # Build the command
        cmd_args = []
        
        if hasattr(request, 'detach') and request.detach:
            cmd_args.append("-d")
        if hasattr(request, 'build') and request.build:
            cmd_args.append("--build")
        if hasattr(request, 'no_build') and request.no_build:
            cmd_args.append("--no-build")
        if hasattr(request, 'force_recreate') and request.force_recreate:
            cmd_args.append("--force-recreate")
        if hasattr(request, 'always_recreate_deps') and request.always_recreate_deps:
            cmd_args.append("--always-recreate-deps")
        if hasattr(request, 'no_recreate') and request.no_recreate:
            cmd_args.append("--no-recreate")
        if hasattr(request, 'renew_anon_volumes') and request.renew_anon_volumes:
            cmd_args.append("-V")
        if hasattr(request, 'remove_orphans') and request.remove_orphans:
            cmd_args.append("--remove-orphans")
        if hasattr(request, 'no_deps') and request.no_deps:
            cmd_args.append("--no-deps")
        if hasattr(request, 'timeout') and request.timeout:
            cmd_args.extend(["--timeout", str(request.timeout)])
        if hasattr(request, 'exit_code_from') and request.exit_code_from:
            cmd_args.extend(["--exit-code-from", request.exit_code_from])
        if hasattr(request, 'scale') and request.scale:
            for service, num in request.scale.items():
                cmd_args.extend(["--scale", f"{service}={num}"])
        if hasattr(request, 'no_color') and request.no_color:
            cmd_args.append("--no-color")
        if hasattr(request, 'quiet_pull') and request.quiet_pull:
            cmd_args.append("--quiet-pull")
        if hasattr(request, 'no_log_prefix') and request.no_log_prefix:
            cmd_args.append("--no-log-prefix")
        if hasattr(request, 'log_level') and request.log_level:
            cmd_args.extend(["--log-level", request.log_level])
        if hasattr(request, 'json') and request.json:
            cmd_args.append("--json")
        if hasattr(request, 'parallel') and request.parallel:
            cmd_args.extend(["--parallel", str(request.parallel)])
        if hasattr(request, 'dry_run') and request.dry_run:
            cmd_args.append("--dry-run")
        
        # Add profiles if specified
        if hasattr(request, 'profiles') and request.profiles:
            cmd_args.extend(["--profile", ",".join(request.profiles)])
        
        # Execute the command (simplified sync version for now)
        cmd = _build_compose_command("up", request, cmd_args)
        
        if hasattr(request, 'dry_run') and request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        # Run synchronously for now
        result = subprocess.run(cmd, capture_output=True, text=True)
        exit_code = result.returncode
        
        # Update response
        response["success"] = exit_code == 0
        response["exit_code"] = exit_code
        response["stdout"] = result.stdout if result.stdout else None
        response["stderr"] = result.stderr if result.stderr else None
        response["end_time"] = datetime.utcnow()
        
        if exit_code == 0:
            response["message"] = "Compose up completed successfully"
        else:
            response["message"] = f"Compose up failed with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": result.stderr if result.stderr else "Unknown error"
            }]
        
    except Exception as e:
        response["end_time"] = datetime.utcnow()
        response["success"] = False
        response["message"] = f"Error during compose up: {str(e)}"
        response["errors"] = [{
            "code": "COMPOSE_UP_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_up: {str(e)}", exc_info=True)
    
    return response

@mcp.tool
async def compose_down(request: dict) -> Dict[str, Any]:
    """
    Stop and remove containers, networks, and volumes for a Docker Compose project.
    
    This command stops and removes all the resources created by `compose up`.
    
    Args:
        request: ComposeDownRequest with the following optional parameters:
            - project_name: Name of the Compose project
            - file_path: Path to the Compose file
            - files: List of additional Compose files
            - remove_orphans: Remove containers for services not defined in the Compose file
            - rmi: Remove images used by services ("local" or "all")
            - timeout: Timeout in seconds for stopping containers
            - volumes: Remove named volumes declared in the `volumes` section
            - remove_volumes: Remove all volumes (including anonymous ones)
            - remove_all: Remove all images used by services
            - dry_run: Show what would be done without making changes
            
    Returns:
        Dict containing the operation result with:
            - success: Boolean indicating if the operation was successful
            - message: Status message
            - project_name: Name of the Compose project
            - command: The command that was executed
            - start_time: When the command started
            - end_time: When the command completed
            - exit_code: The exit code from the command
            - stdout: Standard output from the command
            - stderr: Standard error from the command
            - errors: List of any errors that occurred
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose down command started",
        "project_name": request.get("project_name", "unknown"),
        "command": "down",
        "start_time": start_time
    }
    
    try:
        # Build the command
        cmd_args = []
        
        if hasattr(request, 'remove_orphans') and request.remove_orphans:
            cmd_args.append("--remove-orphans")
        if hasattr(request, 'rmi') and request.rmi:
            cmd_args.extend(["--rmi", request.rmi])
        if hasattr(request, 'timeout') and request.timeout:
            cmd_args.extend(["--timeout", str(request.timeout)])
        if hasattr(request, 'volumes') and request.volumes:
            cmd_args.append("--volumes")
        if hasattr(request, 'remove_volumes') and request.remove_volumes:
            cmd_args.append("-v")
        if hasattr(request, 'remove_all') and request.remove_all:
            cmd_args.append("--rmi=all")
        if hasattr(request, 'dry_run') and request.dry_run:
            cmd_args.append("--dry-run")
        
        # Execute the command
        cmd = _build_compose_command("down", request, cmd_args)
        
        if hasattr(request, 'dry_run') and request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        exit_code = result.returncode
        
        # Update response
        response["success"] = exit_code == 0
        response["exit_code"] = exit_code
        response["stdout"] = result.stdout if result.stdout else None
        response["stderr"] = result.stderr if result.stderr else None
        response["end_time"] = datetime.utcnow()
        
        if exit_code == 0:
            response["message"] = "Compose down completed successfully"
        else:
            response["message"] = f"Compose down failed with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": result.stderr if result.stderr else "Unknown error"
            }]
        
    except Exception as e:
        response["end_time"] = datetime.utcnow()
        response["success"] = False
        response["message"] = f"Error during compose down: {str(e)}"
        response["errors"] = [{
            "code": "COMPOSE_DOWN_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_down: {str(e)}", exc_info=True)
    
    return response

@mcp.tool
async def compose_logs(request: dict) -> Dict[str, Any]:
    """
    View output from containers in a Docker Compose project.
    
    This command shows the logs for all services or the specified services.
    
    Args:
        request: ComposeLogsRequest with the following parameters:
            - project_name: Name of the Compose project
            - file_path: Path to the Compose file
            - files: List of additional Compose files
            - follow: Follow log output (like tail -f)
            - tail: Number of lines to show from the end of the logs
            - timestamps: Show timestamps
            - since: Show logs since a timestamp or duration
            - until: Show logs before a timestamp or duration
            - no_color: Produce monochrome output
            - no_log_prefix: Don't print prefix in logs
            - services: List of services to show logs for
            
    Returns:
        Dict containing the log output with:
            - success: Boolean indicating if the operation was successful
            - message: Status message
            - project_name: Name of the Compose project
            - command: The command that was executed
            - start_time: When the command started
            - end_time: When the command completed
            - exit_code: The exit code from the command
            - stdout: Standard output from the command
            - stderr: Standard error from the command
            - errors: List of any errors that occurred
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose logs command started",
        "project_name": request.get("project_name", "unknown"),
        "command": "logs",
        "start_time": start_time
    }
    
    try:
        # Build the command
        cmd_args = []
        
        if hasattr(request, 'follow') and request.follow:
            cmd_args.append("--follow")
        if hasattr(request, 'tail') and request.tail:
            cmd_args.extend(["--tail", str(request.tail)])
        if hasattr(request, 'timestamps') and request.timestamps:
            cmd_args.append("--timestamps")
        if hasattr(request, 'since') and request.since:
            cmd_args.extend(["--since", request.since])
        if hasattr(request, 'until') and request.until:
            cmd_args.extend(["--until", request.until])
        if hasattr(request, 'no_color') and request.no_color:
            cmd_args.append("--no-color")
        if hasattr(request, 'no_log_prefix') and request.no_log_prefix:
            cmd_args.append("--no-log-prefix")
        
        # Add services if specified
        if hasattr(request, 'services') and request.services:
            cmd_args.extend(request.services)
        
        # Execute the command
        cmd = _build_compose_command("logs", request, cmd_args)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        exit_code = result.returncode
        
        # Update response
        response["success"] = exit_code == 0
        response["exit_code"] = exit_code
        response["stdout"] = result.stdout if result.stdout else None
        response["stderr"] = result.stderr if result.stderr else None
        response["end_time"] = datetime.utcnow()
        
        if exit_code == 0:
            response["message"] = "Compose logs retrieved successfully"
        else:
            response["message"] = f"Failed to retrieve compose logs with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": result.stderr if result.stderr else "Unknown error"
            }]
        
    except Exception as e:
        response["end_time"] = datetime.utcnow()
        response["success"] = False
        response["message"] = f"Error retrieving compose logs: {str(e)}"
        response["errors"] = [{
            "code": "COMPOSE_LOGS_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_logs: {str(e)}", exc_info=True)
    
    return response

@mcp.tool
async def compose_ps(request: dict) -> Dict[str, Any]:
    """
    List containers for a Docker Compose project.
    
    This command shows the status of all containers or the specified services.
    
    Args:
        request: ComposePsRequest with the following parameters:
            - project_name: Name of the Compose project
            - file_path: Path to the Compose file
            - files: List of additional Compose files
            - services: List of services to show
            - all: Show all stopped containers
            - filter: Filter services by a property
            - quiet: Only display container IDs
            - services: Print the service name
            - status: Filter containers by status
            
    Returns:
        Dict containing the container list with:
            - success: Boolean indicating if the operation was successful
            - message: Status message
            - project_name: Name of the Compose project
            - command: The command that was executed
            - containers: List of container information
            - errors: List of any errors that occurred
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose ps command started",
        "project_name": request.get("project_name"),
        "command": "ps",
        "start_time": start_time
    }
    
    try:
        # Build the command
        cmd_args = []
        
        if hasattr(request, 'all') and request.all:
            cmd_args.append("-a")
        if hasattr(request, 'filter') and request.filter:
            cmd_args.extend(["--filter", request.filter])
        if hasattr(request, 'format') and request.format:
            cmd_args.extend(["--format", request.format])
        if hasattr(request, 'quiet') and request.quiet:
            cmd_args.append("-q")
        if hasattr(request, 'status') and request.status:
            cmd_args.extend(["--status", ",".join(request.status)])
        if hasattr(request, 'dry_run') and request.dry_run:
            cmd_args.append("--dry-run")
        
        # Execute the command
        cmd = _build_compose_command("ps", request, cmd_args)
        
        if hasattr(request, 'dry_run') and request.dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "command": " ".join(cmd),
                "dry_run": True
            }
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        exit_code = result.returncode
        
        # Parse the output if successful
        services = {}
        if exit_code == 0 and result.stdout:
            lines = result.stdout.splitlines()
            
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
        response.stdout = result.stdout if result.stdout else None
        response.stderr = result.stderr if result.stderr else None
        response.services = services
        response.end_time = datetime.utcnow()
        
        if exit_code == 0:
            response.message = f"Found {len(services)} containers"
        else:
            response.message = f"Failed to list containers with exit code {exit_code}"
            response.errors = [{
                "code": exit_code,
                "message": result.stderr if result.stderr else "Unknown error"
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


