"""
Service-related models for the workflow system.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import Field
from .base import BaseModel


class ServiceHealth(str, Enum):
    """Health status of a service."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    
    @classmethod
    def is_healthy(cls, health: 'ServiceHealth') -> bool:
        """Check if a health status is considered healthy."""
        return health == cls.HEALTHY
    
    @classmethod
    def is_unhealthy(cls, health: 'ServiceHealth') -> bool:
        """Check if a health status is considered unhealthy."""
        return health in (cls.UNHEALTHY, cls.STOPPED, cls.DEGRADED)


class ServiceDefinition(BaseModel):
    """Definition of a service in a workflow."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$',
        description="Name of the service. Must be a valid DNS label.",
        example="web"
    )
    image: str = Field(..., description="Container image to use for the service")
    version: str = Field("latest", description="Version of the service image")
    command: Optional[Union[str, List[str]]] = Field(
        None,
        description="Command to run in the container"
    )
    args: Optional[Union[str, List[str]]] = Field(
        None,
        description="Arguments to pass to the container command"
    )
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the service"
    )
    ports: List[Union[str, int, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Port mappings for the service"
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description="Services that this service depends on"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "web",
                "image": "nginx:alpine",
                "ports": ["80:80"],
                "environment": {"DEBUG": "true"},
                "depends_on": ["redis"]
            }
        }
    }
