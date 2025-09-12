"""
Container Utilities for Docker MCP.

This module provides utility functions and classes for container operations.
Compatible with FastMCP 2.12+.
"""
import logging
from typing import Any, Dict, List, Optional, Union, cast, AsyncGenerator, TypeVar, Type

# FastMCP imports
from fastmcp.tools import tool, tool

# Import custom exceptions
from .container_models import ContainerError

# Pydantic models
from pydantic import BaseModel

# Docker SDK
import aiodocker
from aiodocker.exceptions import DockerError

# Local imports
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

# Type variable for response models
T = TypeVar('T', bound=BaseModel)

async def create_response(
    success: bool,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    model: Optional[Type[T]] = None
) -> Union[Dict[str, Any], T]:
    """
    Create a standardized response dictionary or Pydantic model.
    
    Args:
        success: Whether the operation was successful
        message: Human-readable message
        data: Optional result data
        error: Optional error details
        model: Optional Pydantic model class to validate the response against
        
    Returns:
        Dictionary with response data or an instance of the provided model
        
    Example:
        >>> response = await create_response(
        ...     success=True,
        ...     message="Operation completed",
        ...     data={"result": 42},
        ...     model=MyResponseModel
        ... )
    """
    import datetime
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response['data'] = data
        
    if error is not None:
        response['error'] = error
    
    # If a model class is provided, validate the response against it
    if model is not None:
        try:
            return model(**response)
        except Exception as e:
            error_msg = f"Failed to create response model: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ContainerError(error_msg)
    
    return response

async def handle_error(
    error: Exception, 
    context: str = "",
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Handle an error and return a standardized error response.
    
    Args:
        error: The exception that was raised
        context: Additional context about where the error occurred
        include_traceback: Whether to include the full traceback in the response
        
    Returns:
        Dictionary with error details
        
    Example:
        >>> try:
        ...     # Some operation that might fail
        ...     pass
        ... except Exception as e:
        ...     return await handle_error(e, "Failed to process container")
    """
    error_msg = f"{context}: {str(error)}" if context else str(error)
    
    # Log the error with full traceback
    logger.error(error_msg, exc_info=True)
    
    # Prepare error details
    error_details = {
        'type': error.__class__.__name__,
        'message': str(error),
    }
    
    # Include traceback if requested
    if include_traceback:
        import traceback
        error_details['traceback'] = traceback.format_exc()
    
    # Handle specific error types
    if isinstance(error, aiodocker.exceptions.DockerError):
        error_details['docker_code'] = getattr(error, 'status', None)
        
    return await create_response(
        success=False,
        message="An error occurred",
        error=error_msg,
        data=error_details
    )

class ContainerManager:
    """Manager for Docker container operations."""
    
    def __init__(self, docker_client: Optional[aiodocker.Docker] = None):
        """Initialize the ContainerManager.
        
        Args:
            docker_client: Optional Docker client instance. If not provided,
                a new client will be created.
        """
        self.docker = docker_client or get_docker_client()
    
    def get_container(self, container_id: str) -> Any:
        """Get a container by ID or name.
        
        Args:
            container_id: Container ID or name.
            
        Returns:
            The container object.
            
        Raises:
            DockerException: If the container is not found or another error occurs.
        """
        try:
            return self.docker.containers.get(container_id)
        except DockerException as e:
            logger.error("Failed to get container %s: %s", container_id, e)
            raise
    
    def list_containers(self, all_containers: bool = True, **filters: Any) -> List[Dict[str, Any]]:
        """List containers.
        
        Args:
            all_containers: If True, show all containers. If False, show only running containers.
            **filters: Additional filters to apply.
            
        Returns:
            List of container dictionaries.
        """
        try:
            containers = self.docker.containers.list(
                all=all_containers,
                filters=filters or None
            )
            return [{
                'id': c.id,
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else c.image.id,
                'created': c.attrs['Created'],
                'ports': c.ports,
                'labels': c.labels,
            } for c in containers]
        except DockerException as e:
            logger.error("Failed to list containers: %s", e)
            raise

    def container_exists(self, container_id: str) -> bool:
        """Check if a container exists.
        
        Args:
            container_id: Container ID or name.
            
        Returns:
            bool: True if the container exists, False otherwise.
        """
        try:
            self.get_container(container_id)
            return True
        except DockerException:
            return False

    def get_container_stats(self, container_id: str, stream: bool = False) -> Dict[str, Any]:
        """Get container statistics.
        
        Args:
            container_id: Container ID or name.
            stream: If True, return a stream of stats. If False, return a single snapshot.
            
        Returns:
            Container statistics.
        """
        container = self.get_container(container_id)
        return container.stats(stream=stream, decode=True)

    def get_container_logs(
        self,
        container_id: str,
        follow: bool = False,
        tail: Union[str, int] = "all",
        since: Optional[Union[str, int]] = None,
        until: Optional[Union[str, int]] = None,
        timestamps: bool = False
    ) -> str:
        """Get container logs.
        
        Args:
            container_id: Container ID or name.
            follow: Follow log output.
            tail: Number of lines to show from the end of the logs.
            since: Show logs since this timestamp or relative time.
            until: Show logs before this timestamp or relative time.
            timestamps: Show timestamps.
            
        Returns:
            Container logs as a string.
        """
        container = self.get_container(container_id)
        return container.logs(
            follow=follow,
            tail=tail,
            since=since,
            until=until,
            timestamps=timestamps
        ).decode('utf-8')

    def execute_command(
        self,
        container_id: str,
        command: Union[str, List[str]],
        user: Optional[str] = None,
        workdir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        privileged: bool = False,
        tty: bool = False,
        detach: bool = False
    ) -> Dict[str, Any]:
        """Execute a command in a container.
        
        Args:
            container_id: Container ID or name.
            command: Command to execute.
            user: Username or UID to run the command as.
            workdir: Working directory for the command.
            environment: Environment variables to set for the command.
            privileged: Run the command in privileged mode.
            tty: Allocate a pseudo-TTY.
            detach: If True, detach from the command immediately.
            
        Returns:
            Dictionary containing the command output and exit code.
        """
        container = self.get_container(container_id)
        
        exec_id = container.client.api.exec_create(
            container.id,
            cmd=command,
            user=user,
            workdir=workdir,
            environment=environment,
            privileged=privileged,
            tty=tty
        )
        
        output = container.client.api.exec_start(
            exec_id=exec_id['Id'],
            detach=detach,
            tty=tty
        )
        
        if not detach:
            if isinstance(output, bytes):
                output = output.decode('utf-8')
            
            inspect = container.client.api.exec_inspect(exec_id['Id'])
            return {
                'output': output,
                'exit_code': inspect['ExitCode'] if 'ExitCode' in inspect else None,
                'running': inspect.get('Running', False)
            }
        
        return {'exec_id': exec_id['Id'], 'detached': True}


def get_tools() -> List[Any]:
    """
    Return all tools in this module for registration.
    
    Returns:
        List of tool objects that should be registered with FastMCP
    """
    # This module contains internal utilities, no tools to register directly
    return []

# Create a default instance for convenience
container_mgr = None

async def get_container_manager() -> ContainerManager:
    """Get or create a ContainerManager instance.
    
    Returns:
        ContainerManager: A container manager instance.
    """
    global container_mgr
    if container_mgr is None:
        container_mgr = ContainerManager()
    return container_mgr

