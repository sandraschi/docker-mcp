"""
Custom exceptions for the Docker MCP application.

This module defines custom exceptions that are used throughout the application.
"""

class DockerMCPError(Exception):
    """Base exception for all Docker MCP errors."""
    pass

class ToolError(DockerMCPError):
    """Raised when a tool encounters an error during execution."""
    pass

class ContainerError(DockerMCPError):
    """Raised when a container operation fails."""
    pass

class ImageError(DockerMCPError):
    """Raised when an image operation fails."""
    pass

class NetworkError(DockerMCPError):
    """Raised when a network operation fails."""
    pass

class VolumeError(DockerMCPError):
    """Raised when a volume operation fails."""
    pass

class ValidationError(DockerMCPError):
    """Raised when input validation fails."""
    pass

class ConfigurationError(DockerMCPError):
    """Raised when there is a configuration error."""
    pass

class NotFoundError(DockerMCPError):
    """Raised when a resource is not found."""
    pass

class UnauthorizedError(DockerMCPError):
    """Raised when authentication or authorization fails."""
    pass

class TimeoutError(DockerMCPError):
    """Raised when an operation times out."""
    pass

# For backward compatibility
ToolException = ToolError
