"""
Error handling utilities for Docker MCP tools.

This module provides decorators and utilities for consistent error handling
across all Docker MCP tools.
"""

import functools
import logging
from typing import Any, Callable, TypeVar, cast, Optional, Type

import docker.errors
from docker.models.containers import Container

# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])

def handle_docker_errors(func: F) -> F:
    """
    Decorator to handle Docker API errors and provide user-friendly messages.
    
    This decorator should be applied to all tool functions that interact with
    the Docker API. It will catch common Docker exceptions and return
    user-friendly error messages.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
            
        except docker.errors.APIError as e:
            error_msg = f"Docker API error: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return {"status": "error", "message": error_msg}
            
        except docker.errors.DockerException as e:
            error_msg = f"Docker error: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return {"status": "error", "message": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return {"status": "error", "message": error_msg}
            
    return cast(F, wrapper)

def check_container_running(container: Container) -> bool:
    """Check if a container is running."""
    try:
        container.reload()
        return container.status == 'running'
    except docker.errors.APIError:
        return False

def format_container_not_found(container_id: str) -> dict:
    """Format a consistent 'container not found' error response."""
    return {
        "status": "error",
        "message": f"Container not found: {container_id}",
        "suggestions": [
            "Check if the container ID is correct",
            "Use 'list_containers' to see available containers"
        ]
    }

def format_container_not_running(container_id: str) -> dict:
    """Format a consistent 'container not running' error response."""
    return {
        "status": "error",
        "message": f"Container is not running: {container_id}",
        "suggestions": [
            "Start the container first using 'start_container'",
            "Check container status with 'inspect_container'"
        ]
    }

def format_permission_error() -> dict:
    """Format a consistent 'permission denied' error response."""
    return {
        "status": "error",
        "message": "Permission denied when trying to connect to Docker",
        "suggestions": [
            "Make sure your user has permissions to access the Docker daemon",
            "On Linux, add your user to the 'docker' group: 'sudo usermod -aG docker $USER'"
        ]
    }

def format_daemon_not_running() -> dict:
    """Format a consistent 'Docker daemon not running' error response."""
    return {
        "status": "error",
        "message": "Docker daemon is not running",
        "suggestions": [
            "Start Docker Desktop or the Docker service",
            "Run 'docker info' to verify Docker is running"
        ]
    }
