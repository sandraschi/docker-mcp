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

from dockermcp.logging_config import configure_logging, logging

# Configure logging
configure_logging()

# Import FastMCP components
from fastmcp.tools import Tool, tool, tool, tool
from fastmcp.exceptions import ToolException
from pydantic import ValidationError

from dockermcp.core.compose import ComposeManager

# Get a logger for this module
logger = logging.getLogger('dockermcp.tools.compose')

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
    cmd = ["docker-compose", "--project-name", request.get("project_name", "default")]
    
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
    name="compose_build",
    description="Build or rebuild services in a Docker Compose project",
    parameters={
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Name of the Compose project"},
            "file_path": {"type": "string", "description": "Path to the Compose file"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "List of Compose files"},
            "no_cache": {"type": "boolean", "description": "Do not use cache when building the image"},
            "force_rm": {"type": "boolean", "description": "Always remove intermediate containers"},
            "pull": {"type": "boolean", "description": "Always attempt to pull a newer version of the image"},
            "parallel": {"type": "boolean", "description": "Build images in parallel"},
            "quiet": {"type": "boolean", "description": "Suppress build output"},
            "services": {"type": "array", "items": {"type": "string"}, "description": "List of services to build"}
        },
        "required": ["project_name"]
    }
)
async def compose_build(request: dict) -> Dict[str, Any]:
    """
    Build or rebuild services in a Docker Compose project.
    
    This command builds images for services defined in the Compose file.
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose build command started",
        "project_name": request.get("project_name", "unknown"),
        "command": "build",
        "start_time": start_time
    }
    
    try:
        # Build the command
        cmd_args = []
        
        if request.get('no_cache'):
            cmd_args.append("--no-cache")
        if request.get('force_rm'):
            cmd_args.append("--force-rm")
        if request.get('pull'):
            cmd_args.append("--pull")
        if request.get('parallel'):
            cmd_args.append("--parallel")
        if request.get('quiet'):
            cmd_args.append("--quiet")
        
        # Execute the command
        cmd = _build_compose_command("build", request, cmd_args)
        
        if request.get('dry_run'):
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
            response["message"] = "Compose build completed successfully"
        else:
            response["message"] = f"Compose build failed with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": result.stderr if result.stderr else "Unknown error"
            }]
        
    except Exception as e:
        response["end_time"] = datetime.utcnow()
        response["success"] = False
        response["message"] = f"Error during compose build: {str(e)}"
        response["errors"] = [{
            "code": "COMPOSE_BUILD_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_build: {str(e)}", exc_info=True)
    
    return response

@Tool(
    name="compose_up",
    description="Create and start containers for a Docker Compose project",
    parameters={
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Name of the Compose project"},
            "file_path": {"type": "string", "description": "Path to the Compose file"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "List of Compose files"},
            "services": {"type": "array", "items": {"type": "string"}, "description": "List of services to start"},
            "build": {"type": "boolean", "description": "Build images before starting containers"},
            "no_build": {"type": "boolean", "description": "Don't build an image, even if it's missing"},
            "force_recreate": {"type": "boolean", "description": "Recreate containers even if their configuration and image haven't changed"},
            "no_recreate": {"type": "boolean", "description": "If containers already exist, don't recreate them"},
            "no_start": {"type": "boolean", "description": "Don't start the services after creating them"},
            "detach": {"type": "boolean", "description": "Detached mode: Run containers in the background"},
            "remove_orphans": {"type": "boolean", "description": "Remove containers for services not defined in the Compose file"}
        },
        "required": ["project_name"]
    }
)
async def compose_up(request: dict) -> Dict[str, Any]:
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
        
        if request.get('detach'):
            cmd_args.append("-d")
        if request.get('build'):
            cmd_args.append("--build")
        if request.get('no_build'):
            cmd_args.append("--no-build")
        if request.get('force_recreate'):
            cmd_args.append("--force-recreate")
        if request.get('remove_orphans'):
            cmd_args.append("--remove-orphans")
        if request.get('dry_run'):
            cmd_args.append("--dry-run")
        
        # Execute the command
        cmd = _build_compose_command("up", request, cmd_args)
        
        if request.get('dry_run'):
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

@Tool(
    name="compose_down",
    description="Stop and remove containers, networks, and volumes for a Docker Compose project",
    parameters={
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Name of the Compose project"},
            "file_path": {"type": "string", "description": "Path to the Compose file"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "List of Compose files"},
            "remove_orphans": {"type": "boolean", "description": "Remove containers for services not defined in the Compose file"},
            "rmi": {"type": "string", "enum": ["all", "local"], "description": "Remove images used by services"},
            "volumes": {"type": "boolean", "description": "Remove named volumes declared in the volumes section of the Compose file"},
            "remove_volumes": {"type": "boolean", "description": "Remove named volumes and anonymous volumes attached to containers"},
            "timeout": {"type": "integer", "description": "Specify a shutdown timeout in seconds"}
        },
        "required": ["project_name"]
    }
)
async def compose_down(request: dict) -> Dict[str, Any]:
    """
    Stop and remove containers, networks, and volumes for a Docker Compose project.
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
        
        if request.get('remove_orphans'):
            cmd_args.append("--remove-orphans")
        if request.get('volumes'):
            cmd_args.append("--volumes")
        if request.get('rmi'):
            cmd_args.extend(["--rmi", request.get('rmi')])
        
        # Execute the command
        cmd = _build_compose_command("down", request, cmd_args)
        
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

@Tool(
    name="compose_logs",
    description="View output from containers in a Docker Compose project",
    parameters={
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Name of the Compose project"},
            "file_path": {"type": "string", "description": "Path to the Compose file"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "List of Compose files"},
            "services": {"type": "array", "items": {"type": "string"}, "description": "List of services to show logs for"},
            "follow": {"type": "boolean", "description": "Follow log output"},
            "tail": {"type": "string", "description": "Number of lines to show from the end of the logs"},
            "since": {"type": "string", "description": "Show logs since a timestamp or duration"},
            "until": {"type": "string", "description": "Show logs before a timestamp or duration"},
            "timestamps": {"type": "boolean", "description": "Show timestamps"},
            "no_color": {"type": "boolean", "description": "Produce monochrome output"},
            "no_log_prefix": {"type": "boolean", "description": "Don't print prefix in logs"}
        },
        "required": ["project_name"]
    }
)
async def compose_logs(request: dict) -> Dict[str, Any]:
    """
    View output from containers in a Docker Compose project.
    
    This command shows the logs for all services or the specified services.
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
        
        if request.get('follow'):
            cmd_args.append("--follow")
        if request.get('tail'):
            cmd_args.extend(["--tail", str(request.get('tail'))])
        if request.get('timestamps'):
            cmd_args.append("--timestamps")
        if request.get('since'):
            cmd_args.extend(["--since", request.get('since')])
        
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

@Tool(
    name="compose_ps",
    description="List containers for a Docker Compose project",
    parameters={
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Name of the Compose project"},
            "file_path": {"type": "string", "description": "Path to the Compose file"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "List of Compose files"},
            "services": {"type": "array", "items": {"type": "string"}, "description": "List of services to show"},
            "all": {"type": "boolean", "description": "Show all stopped containers"},
            "filter": {"type": "string", "description": "Filter services by a property"},
            "format": {"type": "string", "description": "Format the output using the given Go template"},
            "quiet": {"type": "boolean", "description": "Only display container IDs"},
            "status": {"type": "array", "items": {"type": "string"}, "description": "Filter services by status (running, paused, restarting, removing, exited, dead, created)"}
        },
        "required": ["project_name"]
    }
)
async def compose_ps(request: dict) -> Dict[str, Any]:
    """
    List containers for a Docker Compose project.
    
    This command shows the status of all containers or the specified services.
    """
    start_time = datetime.utcnow()
    response = {
        "success": False,
        "message": "Compose ps command started",
        "project_name": request.get("project_name", "unknown"),
        "command": "ps",
        "start_time": start_time
    }
    
    try:
        # Build the command
        cmd_args = []
        
        if request.get('all'):
            cmd_args.append("-a")
        if request.get('quiet'):
            cmd_args.append("-q")
        
        # Execute the command
        cmd = _build_compose_command("ps", request, cmd_args)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        exit_code = result.returncode
        
        # Parse the output if successful
        services = {}
        if exit_code == 0 and result.stdout:
            lines = result.stdout.splitlines()
            
            # Simple parsing of the output
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 4:
                    service_name = parts[0]
                    container_id = parts[0][:12]  # Short ID
                    status = " ".join(parts[1:-2]) if len(parts) > 2 else "unknown"
                    ports = parts[-1] if len(parts) > 1 else ""
                    
                    services[service_name] = {
                        "container_id": container_id,
                        "status": status,
                        "ports": ports,
                        "name": service_name
                    }
        
        # Update response
        response["success"] = exit_code == 0
        response["exit_code"] = exit_code
        response["stdout"] = result.stdout if result.stdout else None
        response["stderr"] = result.stderr if result.stderr else None
        response["services"] = services
        response["end_time"] = datetime.utcnow()
        
        if exit_code == 0:
            response["message"] = f"Found {len(services)} containers"
        else:
            response["message"] = f"Failed to list containers with exit code {exit_code}"
            response["errors"] = [{
                "code": exit_code,
                "message": result.stderr if result.stderr else "Unknown error"
            }]
        
    except Exception as e:
        response["end_time"] = datetime.utcnow()
        response["success"] = False
        response["message"] = f"Error listing containers: {str(e)}"
        response["errors"] = [{
            "code": "COMPOSE_PS_ERROR",
            "message": str(e)
        }]
        logger.error(f"Error in compose_ps: {str(e)}", exc_info=True)
    
    return response
