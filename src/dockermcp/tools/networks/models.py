"""
Network Models for DockerMCP

This module contains Pydantic models for network-related operations.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NetworkIPAMConfig(BaseModel):
    """IPAM configuration for Docker networks."""
    driver: str = "default"
    config: List[Dict[str, str]] = Field(default_factory=list)
    options: Dict[str, str] = Field(default_factory=dict)


class NetworkCreateRequest(BaseModel):
    """Request model for creating a Docker network."""
    name: str = Field(..., min_length=2, max_length=128, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')
    driver: str = "bridge"
    check_duplicate: bool = True
    internal: bool = False
    attachable: bool = False
    ingress: bool = False
    enable_ipv6: bool = False
    labels: Dict[str, str] = Field(default_factory=dict)
    options: Dict[str, str] = Field(default_factory=dict)
    ipam: Optional[NetworkIPAMConfig] = None
    scope: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "my-network",
                "driver": "bridge",
                "enable_ipv6": False,
                "internal": False,
                "labels": {"environment": "development"},
                "ipam": {
                    "driver": "default",
                    "config": [{"subnet": "172.28.0.0/16"}]
                }
            }
        }
    )


class NetworkSummary(BaseModel):
    """Summary information about a Docker network."""
    id: str
    name: str
    driver: str
    scope: str
    created: Optional[datetime] = None
    internal: bool = False
    enable_ipv6: bool = False
    labels: Dict[str, str] = Field(default_factory=dict)
    ipam: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_docker_network(cls, network) -> 'NetworkSummary':
        """Create a NetworkSummary from a Docker network object."""
        attrs = getattr(network, 'attrs', {})
        created = attrs.get('Created')
        
        if created and isinstance(created, str):
            try:
                if '.' in created:
                    created = datetime.fromisoformat(created.split('.')[0])
                else:
                    created = datetime.fromisoformat(created)
            except (ValueError, TypeError):
                created = None
        
        return cls(
            id=getattr(network, 'id', ''),
            name=getattr(network, 'name', ''),
            driver=attrs.get('Driver', ''),
            scope=attrs.get('Scope', ''),
            created=created,
            internal=attrs.get('Internal', False),
            enable_ipv6=attrs.get('EnableIPv6', False),
            labels=attrs.get('Labels', {}),
            ipam=attrs.get('IPAM', {}),
            options=attrs.get('Options', {})
        )


class NetworkListResponse(BaseModel):
    """Response model for listing Docker networks."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    data: List[NetworkSummary] = Field(default_factory=list, description="List of network summaries")
    count: int = Field(0, description="Number of networks returned")
    error: Optional[str] = Field(None, description="Error message if operation failed")

    @classmethod
    def success(cls, data: List[NetworkSummary], message: str = "Success") -> 'NetworkListResponse':
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            data=data,
            count=len(data)
        )

    @classmethod
    def error(cls, error: str, message: str = "An error occurred") -> 'NetworkListResponse':
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            error=error,
            data=[],
            count=0
        )


class NetworkInspectResponse(BaseModel):
    """Response model for network inspection."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    data: Dict[str, Any] = Field(default_factory=dict, description="Detailed network information")
    error: Optional[str] = Field(None, description="Error message if operation failed")

    @classmethod
    def success(cls, data: Dict[str, Any], message: str = "Success") -> 'NetworkInspectResponse':
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            data=data
        )

    @classmethod
    def error(cls, error: str, message: str = "An error occurred") -> 'NetworkInspectResponse':
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            error=error,
            data={}
        )


class NetworkOperationResponse(BaseModel):
    """Generic response model for network operations."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message about the result")
    network_id: Optional[str] = Field(None, description="ID of the affected network")
    error: Optional[str] = Field(None, description="Error message if operation failed")

    @classmethod
    def success(
        cls,
        network_id: str,
        message: str = "Operation completed successfully"
    ) -> 'NetworkOperationResponse':
        """Create a success response."""
        return cls(
            status="success",
            message=message,
            network_id=network_id
        )

    @classmethod
    def error(
        cls,
        error: str,
        network_id: Optional[str] = None,
        message: str = "An error occurred"
    ) -> 'NetworkOperationResponse':
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            network_id=network_id,
            error=error
        )
