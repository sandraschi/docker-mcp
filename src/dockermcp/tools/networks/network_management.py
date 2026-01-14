from __future__ import annotations

"""
Docker Network Management for FastMCP 2.12+

This module provides comprehensive tools for managing Docker networks including:
- Creating and removing networks
- Connecting and disconnecting containers
- Inspecting network details
- Listing and filtering networks
- Managing IPAM (IP Address Management) configurations
"""

import ipaddress
from datetime import datetime
from enum import Enum
from ipaddress import IPv4Network, IPv6Network
from typing import Any, Dict, Generic, List, Literal, Optional, Type, TypeVar, Union, get_args, get_origin

import docker
from docker.errors import DockerException, InvalidArgument
from fastmcp.exceptions import ToolError as ToolError
# Import the mcp instance for tool registration
from pydantic import (
    BaseModel, 
    ConfigDict, 
    Field, 
    HttpUrl, 
    IPvAnyAddress, 
    IPvAnyNetwork, 
    TypeAdapter,
    field_validator,
    model_validator,
    ValidationInfo,
    field_serializer
)
from pydantic_core import PydanticUndefined, field_validator

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

@mcp.tool
async def remove_network(network_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Remove a Docker network by ID or name.
    
    Args:
        network_id: ID or name of the network to remove
        force: Force removal even if in use
        
    Returns:
        Dictionary with status and message indicating success or failure
    """
    try:
        # Get the Docker client
        client = mcp.docker_client
        if client is None:
            raise DockerException("Docker client not available")
        
        # Remove the network
        network = client.networks.get(network_id)
        network.remove(force=force)
        
        logger.info(f"Successfully removed network: {network_id}")
        return {
            "status": "success",
            "message": f"Network '{network_id}' removed successfully",
            "network_id": network_id
        }
        
    except Exception as e:
        error_msg = f"Failed to remove network {network_id}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "network_id": network_id
        }

# Type variables for generic response models
T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """Base response model for all API responses.

    Generic type T represents the type of the data field.
    """
    status: Literal['success', 'error'] = Field(
        ...,
        description="Status of the operation, either 'success' or 'error'"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable message about the result"
    )
    data: Optional[T] = Field(
        default=None,
        description="Response data if the operation was successful"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the operation failed"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {},
                "error": None
            }
        },
        # Pydantic v2 specific settings
        strict=True,
        validate_assignment=True,
        validate_default=True,
        extra='ignore',
        use_enum_values=True,
        from_attributes=True
    )
    
    @field_validator('data')
    @classmethod
    def validate_data(cls, v: Any, info: ValidationInfo) -> Any:
        if info.data.get('status') == 'error' and v is not None:
            raise ValueError("Data should be None when status is 'error'")
        return v
    
    @field_validator('error')
    @classmethod
    def validate_error(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if info.data.get('status') == 'success' and v is not None:
            raise ValueError("Error should be None when status is 'success'")
        return v
    
    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation of the model with proper serialization."""
        # Use the default serialization but ensure proper handling of custom types
        return super().model_dump_json(
            exclude_none=True,
            **kwargs
        )
        
    @classmethod
    def model_validate_json(
        cls: Type['BaseResponse[T]'],
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: dict[str, Any] | None = None,
    ) -> 'BaseResponse[T]':
        """Parse JSON data into a BaseResponse instance."""
        return super().model_validate_json(
            json_data,
            strict=strict,
            context=context
        )

    @classmethod
    def success(
        cls: Type['BaseResponse[T]'],
        data: T = None,
        message: str = "Operation completed successfully"
    ) -> 'BaseResponse[T]':
        """Create a success response.
        
        Args:
            data: The data to include in the response
            message: Optional success message
            
        Returns:
            A BaseResponse instance with status 'success'
        """
        return cls(status='success', message=message, data=data)

    @classmethod
    def error_response(
        cls: Type['BaseResponse[T]'],
        error: str,
        message: str = None,
        data: Any = None
    ) -> 'BaseResponse[T]':
        """Create an error response.
        
        Args:
            error: Error message or description
            message: Optional human-readable message
            data: Optional additional error data
            
        Returns:
            A BaseResponse instance with status 'error'
        """
        return cls(
            status='error',
            message=message or "An error occurred",
            error=error,
            data=data
        )
        
    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation of the model.
        
        Overrides the default to ensure proper serialization of custom types.
        """
        return super().model_dump_json(
            exclude_none=True,
            **kwargs
        )

class NetworkDriver(str, Enum):
    """Supported Docker network drivers."""
    BRIDGE = "bridge"
    HOST = "host"
    OVERLAY = "overlay"
    MACVLAN = "macvlan"
    IPVLAN = "ipvlan"
    NONE = "none"

class IPAMConfig(BaseModel):
    """IP Address Management configuration for Docker networks."""
    subnet: Optional[Union[IPv4Network, IPv6Network]] = Field(
        None,
        description="The subnet in CIDR format (e.g., '172.28.0.0/16')"
    )
    ip_range: Optional[Union[IPv4Network, IPv6Network]] = Field(
        None,
        description="Range of IPs from which to allocate container IPs"
    )
    gateway: Optional[IPvAnyAddress] = Field(
        None,
        description="IPv4 or IPv6 gateway for the master subnet"
    )
    aux_addresses: Optional[Dict[str, IPvAnyAddress]] = Field(
        None,
        description="Auxiliary IPv4 or IPv6 addresses used by the network driver"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subnet": "172.28.0.0/16",
                "gateway": "172.28.5.1"
            }
        }
    )
    
    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation with proper serialization of IP addresses."""
        # Convert IP addresses and networks to strings for JSON serialization
        data = self.model_dump(exclude_none=True, **kwargs)
        
        # Handle IPv4Network and IPv6Network
        if 'subnet' in data and data['subnet'] is not None:
            if hasattr(data['subnet'], '__str__'):
                data['subnet'] = str(data['subnet'])
                
        if 'ip_range' in data and data['ip_range'] is not None:
            if hasattr(data['ip_range'], '__str__'):
                data['ip_range'] = str(data['ip_range'])
                
        # Handle IPv4Address and IPv6Address in gateway and aux_addresses
        if 'gateway' in data and data['gateway'] is not None:
            if hasattr(data['gateway'], '__str__'):
                data['gateway'] = str(data['gateway'])
                
        if 'aux_addresses' in data and data['aux_addresses'] is not None:
            for key, value in data['aux_addresses'].items():
                if hasattr(value, '__str__'):
                    data['aux_addresses'][key] = str(value)
        
        import json
        return json.dumps(data, default=str)

class NetworkListRequest(BaseModel):
    """Request model for listing Docker networks."""
    names: List[str] = Field(
        default_factory=list,
        description="Filter by network names"
    )
    ids: List[str] = Field(
        default_factory=list,
        description="Filter by network IDs"
    )
    driver: Optional[str] = Field(
        None,
        description="Filter by driver name (e.g., 'bridge', 'overlay')"
    )
    network_type: Literal['custom', 'builtin', 'all'] = Field(
        'all',
        description="Type of networks to list"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Filter by labels (e.g., {'com.example.key': 'value'})"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "names": ["my-network"],
                "driver": "bridge",
                "network_type": "all",
                "labels": {"environment": "development"}
            }
        }
    )

class NetworkSummary(BaseModel):
    """Summary information about a Docker network.
    
    This model provides a summary view of a Docker network, including its
    configuration and connected containers.
    """
    id: str = Field(..., description="Unique identifier for the network")
    name: str = Field(..., description="Name of the network")
    driver: str = Field(..., description="Driver used by the network")
    scope: str = Field(..., description="Scope of the network (e.g., 'local', 'swarm')")
    created: Optional[datetime] = Field(
        default=None,
        description="When the network was created"
    )
    internal: bool = Field(
        default=False,
        description="Whether the network is internal (no external access)"
    )
    enable_ipv6: bool = Field(
        default=False,
        description="Whether IPv6 is enabled on the network"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="User-defined key/value metadata for the network"
    )
    containers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Containers connected to the network, keyed by container ID"
    )
    ipam: Dict[str, Any] = Field(
        default_factory=dict,
        description="IP Address Management configuration"
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7d86d31b1478...",
                "name": "my-network",
                "driver": "bridge",
                "scope": "local",
                "created": "2023-01-01T12:00:00Z",
                "internal": False,
                "enable_ipv6": False,
                "labels": {"environment": "development"},
                "containers": {
                    "container1": {
                        "Name": "web",
                        "EndpointID": "abcd1234...",
                        "MacAddress": "02:42:ac:1c:00:02",
                        "IPv4Address": "172.28.0.2/16",
                        "IPv6Address": ""
                    }
                },
                "ipam": {
                    "Driver": "default",
                    "Config": [
                        {
                            "Subnet": "172.28.0.0/16",
                            "Gateway": "172.28.0.1"
                        }
                    ]
                },
                "options": {
                    "com.docker.network.bridge.name": "docker0"
                }
            }
        }
    )
    
    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation with proper datetime serialization."""
        data = self.model_dump(exclude_none=True, **kwargs)
        
        # Ensure datetime is properly formatted
        if 'created' in data and data['created'] is not None:
            if hasattr(data['created'], 'isoformat'):
                data['created'] = data['created'].isoformat()
                
        import json
        return json.dumps(data, default=str)
    
    @classmethod
    def from_docker_network(cls, network: Any) -> 'NetworkSummary':
        """Create a NetworkSummary from a Docker network object.
        
        Args:
            network: A Docker SDK network object
            
        Returns:
            A NetworkSummary instance populated from the Docker network
        """
        if not network:
            raise ValueError("Network cannot be None")
            
        return cls(
            id=network.id,
            name=network.name,
            driver=network.attrs.get('Driver', ''),
            scope=network.attrs.get('Scope', ''),
            created=network.attrs.get('Created'),
            internal=network.attrs.get('Internal', False),
            enable_ipv6=network.attrs.get('EnableIPv6', False),
            labels=network.attrs.get('Labels', {}),
            containers=network.attrs.get('Containers', {}),
            ipam=network.attrs.get('IPAM', {}),
            options=network.attrs.get('Options', {})
        )
        
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Generate a dictionary representation of the model.
        
        Overrides the default to ensure proper serialization of custom types.
        """
        data = super().model_dump(exclude_none=True, **kwargs)
        
        # Ensure datetime is properly formatted
        if 'created' in data and data['created']:
            if isinstance(data['created'], datetime):
                data['created'] = data['created'].isoformat()
                
        return data

class NetworkListResponse(BaseModel):
    """Response model for listing Docker networks.
    
    This extends BaseResponse with additional fields specific to network listing.
    """
    status: Literal['success', 'error'] = Field(
        ...,
        description="Status of the operation, either 'success' or 'error'"
    )
    message: str = Field(
        ...,
        description="Human-readable message about the result"
    )
    data: List[NetworkSummary] = Field(
        default_factory=list,
        description="List of network summaries"
    )
    count: int = Field(
        default=0,
        description="Number of networks returned in the response"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the operation failed"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Networks listed successfully",
                "data": [
                    {
                        "id": "network1",
                        "name": "bridge",
                        "driver": "bridge",
                        "scope": "local",
                        "created": "2023-01-01T12:00:00Z",
                        "internal": False,
                        "enable_ipv6": False,
                        "labels": {"environment": "development"},
                        "containers": {},
                        "ipam": {"Driver": "default"},
                        "options": {}
                    }
                ],
                "count": 1,
                "error": None
            }
        },
        # Pydantic v2 specific settings
        strict=True,
        validate_assignment=True,
        validate_default=True,
        extra='ignore',
        use_enum_values=True,
        from_attributes=True
    )
    
    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None
    ) -> 'NetworkListResponse':
        """Validate and parse the input data into a model instance."""
        # Ensure data is properly converted to NetworkSummary objects
        if isinstance(obj, dict):
            data = obj.get('data', [])
            if data and not all(isinstance(item, NetworkSummary) for item in data):
                obj['data'] = [NetworkSummary.model_validate(item) for item in data]
        return super().model_validate(
            obj,
            strict=strict,
            from_attributes=from_attributes,
            context=context
        )
    
    @field_validator('data', mode='before')
    @classmethod
    def validate_data(cls, v: Any) -> List[NetworkSummary]:
        """Validate and convert data field to List[NetworkSummary]."""
        if v is None:
            return []
        if isinstance(v, list):
            return [
                item if isinstance(item, NetworkSummary) else NetworkSummary.model_validate(item)
                for item in v
            ]
        return [NetworkSummary.model_validate(v)]
    
    @classmethod
    def from_networks(
        cls,
        networks: List[Any],
        message: str = "Networks listed successfully"
    ) -> 'NetworkListResponse':
        """Create a response from a list of Docker network objects.
        
        Args:
            networks: List of Docker SDK network objects
            message: Optional success message
            
        Returns:
            A NetworkListResponse instance with the network data
        """
        network_summaries = [
            NetworkSummary.from_docker_network(network)
            for network in networks
        ]
        
        return cls(
            status="success",
            message=message,
            data=network_summaries,
            count=len(network_summaries)
        )
    
    @classmethod
    def success(
        cls,
        data: List[Union[NetworkSummary, dict]],
        message: str = "Networks listed successfully"
    ) -> 'NetworkListResponse':
        """Create a success response for network listing.
        
        Args:
            data: List of NetworkSummary objects or dicts
            message: Optional success message
            
        Returns:
            A NetworkListResponse instance with status 'success'
        """
        validated_data = [
            item if isinstance(item, NetworkSummary) else NetworkSummary.model_validate(item)
            for item in data
        ]
        return cls(
            status="success",
            message=message,
            data=validated_data,
            count=len(validated_data)
        )
    
    @classmethod
    def error(
        cls,
        error: Union[str, Exception],
        message: str = "Failed to list networks"
    ) -> 'NetworkListResponse':
        """Create an error response for network listing.
        
        Args:
            error: Error message or exception
            message: Optional error message
            
        Returns:
            A NetworkListResponse instance with status 'error'
        """
        error_msg = str(error)
        return cls(
            status="error",
            message=message,
            error=error_msg,
            data=[],
            count=0
        )
        
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Generate a dictionary representation of the model."""
        return super().model_dump(exclude_none=True, **kwargs)
        
    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation of the model."""
        return super().model_dump_json(exclude_none=True, **kwargs)

class NetworkIPAMConfig(BaseModel):
    """IPAM (IP Address Management) configuration for Docker networks.
    
    This model represents the IPAM configuration used when creating or updating
    a Docker network, including the driver, configuration blocks, and options.
    """
    driver: str = Field(
        default="default",
        description="Name of the IPAM driver to use"
    )
    config: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of IPAM configuration blocks, each with subnet, IP range, and gateway"
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options as key-value pairs"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "default",
                "config": [
                    {
                        "Subnet": "172.28.0.0/16",
                        "IPRange": "172.28.5.0/24",
                        "Gateway": "172.28.5.1"
                    }
                ],
                "options": {
                    "foo": "bar"
                }
            }
        }
    )
    
    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation with proper serialization of IP addresses."""
        # Convert the model to a dictionary
        data = self.model_dump(exclude_none=True, **kwargs)
        
        # Ensure all IP addresses and networks are properly serialized to strings
        if 'config' in data and isinstance(data['config'], list):
            for config_item in data['config']:
                for key, value in config_item.items():
                    if hasattr(value, '__str__'):
                        config_item[key] = str(value)
                        
        # Handle options if needed
        if 'options' in data and data['options'] is not None:
            for key, value in data['options'].items():
                if hasattr(value, '__str__'):
                    data['options'][key] = str(value)
        
        import json
        return json.dumps(data, default=str)
        
    def to_docker_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary compatible with Docker SDK.
        
        Returns:
            Dictionary with the IPAM configuration in Docker SDK format
        """
        return {
            'Driver': self.driver,
            'Config': [
                {k: str(v) for k, v in config.items() if v is not None}
                for config in self.config
            ],
            'Options': self.options or {}
        }
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver": "default",
                "config": [
                    {"Subnet": "172.28.0.0/16",
                     "IPRange": "172.28.5.0/24",
                     "Gateway": "172.28.5.1"}
                ],
                "options": {"foo": "bar"}
            }
        }
    )

class NetworkCreateRequest(BaseModel):
    """Request model for creating a Docker network.
    
    This model defines the parameters required to create a new Docker network,
    including network configuration, IPAM settings, and driver options.
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$',
        description="Name of the network to create (2-255 chars, alphanumeric with ._-)"
    )
    driver: NetworkDriver = Field(
        default=NetworkDriver.BRIDGE,
        description="Network driver to use"
    )
    check_duplicate: bool = Field(
        default=True,
        description="If True, checks for networks with duplicate names"
    )
    internal: bool = Field(
        default=False,
        description="If True, restricts external access to the network"
    )
    attachable: bool = Field(
        default=False,
        description="If True, allows manual container attachment"
    )
    ingress: bool = Field(
        default=False,
        description="If True, creates an ingress network for Swarm services"
    )
    ipam: NetworkIPAMConfig = Field(
        default_factory=NetworkIPAMConfig,
        description="IP Address Management configuration"
    )
    enable_ipv6: bool = Field(
        default=False,
        description="If True, enables IPv6 on the network"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Metadata in key-value pairs"
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options as key-value pairs"
    )
    
    # Pydantic v2 model configuration

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "my-network",
                "driver": "bridge",
                "enable_ipv6": False,
                "internal": False,
                "attachable": False,
                "ingress": False,
                "options": {"com.docker.network.bridge.name": "my-network"},
                "labels": {"environment": "development"},
                "ipam": {
                    "driver": "default",
                    "config": [
                        {"Subnet": "172.28.0.0/16",
                         "IPRange": "172.28.5.0/24",
                         "Gateway": "172.28.5.1"}
                    ]
                }
            }
        }
    )

class NetworkCreateResponse(BaseModel):
    """Response model for creating a Docker network."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message")
    network_id: Optional[str] = Field(
        None,
        description="ID of the created network"
    )
    warning: Optional[str] = Field(
        None,
        description="Optional warning message"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if operation failed"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Network created successfully",
                "network_id": "a1b2c3d4e5f6",
                "warning": "Optional warning message"
            }
        }
    )

    @classmethod
    def success(cls, network_id: str, message: str = "Network created successfully") -> 'NetworkCreateResponse':
        """Create a success response for network creation."""
        return cls(
            status="success",
            message=message,
            network_id=network_id
        )
        
    @classmethod
    def error(cls, error: str, message: str = "Failed to create network") -> 'NetworkCreateResponse':
        """Create an error response for network creation."""
        return cls(
            status="error",
            message=message,
            error=error
        )

    @classmethod
    def from_network(cls, network: Any) -> 'NetworkCreateResponse':
        """Create a response from a Docker network object."""
        return cls(
            status="success",
            message="Network created successfully",
            network_id=network.id,
            warning=getattr(network, 'warning', None)
        )

class NetworkRemoveRequest(BaseModel):
    """Request model for removing a Docker network."""
    network_id: str = Field(
        ...,
        description="ID or name of the network to remove"
    )
    force: bool = Field(
        default=False,
        description="Force the removal of the network even if in use"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "network_id": "my-network",
                "force": False
            }
        }
    )


class NetworkRemoveResponse(BaseResponse[Dict[str, Any]]):
    """Response model for removing a Docker network."""
    network_id: str = Field(
        ...,
        description="ID of the removed network"
    )
    
    @classmethod
    def success_response(
        cls,
        network_id: str,
        message: str = "Network removed successfully"
    ) -> 'NetworkRemoveResponse':
        """Create a success response for network removal."""
        return cls(
            status="success",
            message=message,
            data={"network_id": network_id},
            network_id=network_id
        )


class NetworkConnectResponse(BaseResponse[Dict[str, str]]):
    """Response model for connecting a container to a Docker network.
    
    This model extends BaseResponse with container and network identifiers
    to provide detailed feedback about the connection operation.
    """
    container_id: str = Field(
        default="",
        description="ID of the container that was connected"
    )
    network_id: str = Field(
        default="",
        description="ID of the network the container was connected to"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Container connected to network successfully",
                "data": {
                    "container_id": "c1d2e3f4g5h6",
                    "network_id": "n1m2n3m4n5m6"
                },
                "container_id": "c1d2e3f4g5h6",
                "network_id": "n1m2n3m4n5m6",
                "error": None
            }
        }
    )
    
    @classmethod
    def success(
        cls,
        container_id: str,
        network_id: str,
        message: str = "Container connected to network successfully"
    ) -> 'NetworkConnectResponse':
        """Create a success response for network connection.
        
        Args:
            container_id: ID of the connected container
            network_id: ID of the network
            message: Optional success message
            
        Returns:
            A NetworkConnectResponse instance with status 'success'
        """
        return cls(
            status="success",
            message=message,
            data={"container_id": container_id, "network_id": network_id},
            container_id=container_id,
            network_id=network_id
        )
        
    @classmethod
    def error(
        cls,
        error: Union[str, Exception],
        message: str = "Failed to connect container to network",
        container_id: str = "",
        network_id: str = ""
    ) -> 'NetworkConnectResponse':
        """Create an error response for network connection.
        
        Args:
            error: Error message or exception
            message: Optional error message
            container_id: Optional container ID if known
            network_id: Optional network ID if known
            
        Returns:
            A NetworkConnectResponse instance with status 'error'
        """
        error_msg = str(error)
        return cls(
            status="error",
            message=message,
            error=error_msg,
            data={"container_id": container_id, "network_id": network_id},
            container_id=container_id,
            network_id=network_id
        )
        
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Generate a dictionary representation of the model.
        
        Overrides the default to ensure proper serialization of nested models.
        """
        data = super().model_dump(exclude_none=True, **kwargs)
        return data


class NetworkConnectRequest(BaseModel):
    """Request model for connecting a container to a Docker network.
    
    This model defines the parameters required to connect a container to a network,
    including IP addressing, aliases, and driver options.
    """
    container: str = Field(
        ...,
        min_length=1,
        description="ID or name of the container to connect"
    )
    network: str = Field(
        ...,
        min_length=1,
        description="ID or name of the network to connect to"
    )
    ipv4_address: Optional[IPvAnyAddress] = Field(
        default=None,
        description="IPv4 address to assign to the container (e.g., 172.30.100.104)"
    )
    ipv6_address: Optional[IPvAnyAddress] = Field(
        default=None,
        description="IPv6 address to assign to the container (e.g., 2001:db8::33)"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Network-scoped aliases for the container"
    )
    links: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of container names to aliases for service discovery"
    )
    link_local_ips: List[str] = Field(
        default_factory=list,
        description="List of link-local IP addresses for the container"
    )
    driver_opt: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options for the endpoint"
    )
    mac_address: Optional[str] = Field(
        default=None,
        pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        description="MAC address for the container's network interface (format: 00:11:22:33:44:55)"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container": "my-container",
                "network": "my-network",
                "ipv4_address": "172.30.100.104",
                "aliases": ["web", "app"],
                "driver_opt": {"com.docker.network.driver.mtu": "1500"}
            }
        }
    )


class NetworkDisconnectRequest(BaseModel):
    """Request model for disconnecting a container from a Docker network.
    
    This model defines the parameters required to disconnect a container from a network,
    including an option to force the disconnection if the container is running.
    """
    container: str = Field(
        ...,
        min_length=1,
        description="ID or name of the container to disconnect"
    )
    network: str = Field(
        ...,
        min_length=1,
        description="ID or name of the network to disconnect from"
    )
    force: bool = Field(
        default=False,
        description="Force disconnection even if the container is running"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container": "my-container",
                "network": "my-network",
                "force": False
            }
        }
    )
    
    def to_docker_params(self) -> Dict[str, Any]:
        """Convert the request to parameters for Docker SDK.
        
        Returns:
            Dictionary of parameters for Docker SDK disconnect operation
        """
        return {
            "container": self.container,
            "force": self.force
        }


class NetworkDisconnectResponse(BaseResponse[Dict[str, str]]):
    """Response model for disconnecting a container from a Docker network.
    
    This model extends BaseResponse with container and network identifiers
    to provide detailed feedback about the disconnection operation.
    """
    container_id: str = Field(
        default="",
        description="ID of the container that was disconnected"
    )
    network_id: str = Field(
        default="",
        description="ID of the network the container was disconnected from"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Container disconnected from network successfully",
                "data": {
                    "container_id": "c1d2e3f4g5h6",
                    "network_id": "n1m2n3m4n5m6"
                },
                "container_id": "c1d2e3f4g5h6",
                "network_id": "n1m2n3m4n5m6",
                "error": None
            }
        }
    )
    
    @classmethod
    def success(
        cls,
        container_id: str,
        network_id: str,
        message: str = "Container disconnected from network successfully"
    ) -> 'NetworkDisconnectResponse':
        """Create a success response for network disconnection.
        
        Args:
            container_id: ID of the disconnected container
            network_id: ID of the network
            message: Optional success message
            
        Returns:
            A NetworkDisconnectResponse instance with status 'success'
        """
        return cls(
            status="success",
            message=message,
            data={"container_id": container_id, "network_id": network_id},
            container_id=container_id,
            network_id=network_id
        )
        
    @classmethod
    def error(
        cls,
        error: Union[str, Exception],
        message: str = "Failed to disconnect container from network",
        container_id: str = "",
        network_id: str = ""
    ) -> 'NetworkDisconnectResponse':
        """Create an error response for network disconnection.
        
        Args:
            error: Error message or exception
            message: Optional error message
            container_id: Optional container ID if known
            network_id: Optional network ID if known
            
        Returns:
            A NetworkDisconnectResponse instance with status 'error'
        """
        error_msg = str(error)
        return cls(
            status="error",
            message=message,
            error=error_msg,
            data={"container_id": container_id, "network_id": network_id},
            container_id=container_id,
            network_id=network_id
        )
        
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Generate a dictionary representation of the model.
        
        Overrides the default to ensure proper serialization of nested models.
        """
        data = super().model_dump(exclude_none=True, **kwargs)
        return data


class NetworkInspectResult(BaseModel):
    """Detailed information about a Docker network.
    
    This model provides a comprehensive view of a Docker network's configuration,
    including its properties, connected containers, and IPAM settings.
    """
    name: str = Field(
        ...,
        description="Name of the network"
    )
    id: str = Field(
        ...,
        description="Unique identifier for the network"
    )
    created: datetime = Field(
        ...,
        description="Timestamp when the network was created"
    )
    scope: str = Field(
        ...,
        description="Scope of the network (e.g., 'local', 'swarm')"
    )
    driver: str = Field(
        ...,
        description="Network driver in use"
    )
    enable_ipv6: bool = Field(
        ...,
        description="Whether IPv6 is enabled on the network"
    )
    internal: bool = Field(
        ...,
        description="Whether the network is internal (no external access)"
    )
    attachable: bool = Field(
        ...,
        description="Whether containers can be attached to this network"
    )
    ingress: bool = Field(
        ...,
        description="Whether this is the ingress network for a Swarm"
    )
    ipam: Dict[str, Any] = Field(
        ...,
        description="IP Address Management configuration"
    )
    options: Dict[str, str] = Field(
        ...,
        description="Driver-specific options as key-value pairs"
    )
    labels: Dict[str, str] = Field(
        ...,
        description="User-defined metadata as key-value pairs"
    )
    containers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Containers connected to the network, keyed by container ID"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        },
        json_schema_extra={
            "example": {
                "name": "bridge",
                "id": "7d86d31b1478...",
                "created": "2023-01-01T12:00:00Z",
                "scope": "local",
                "driver": "bridge",
                "enable_ipv6": False,
                "internal": False,
                "attachable": False,
                "ingress": False,
                "ipam": {
                    "Driver": "default",
                    "Config": [
                        {
                            "Subnet": "172.17.0.0/16",
                            "Gateway": "172.17.0.1"
                        }
                    ]
                },
                "options": {
                    "com.docker.network.bridge.default_bridge": "true",
                    "com.docker.network.bridge.enable_icc": "true",
                    "com.docker.network.bridge.enable_ip_masquerade": "true",
                    "com.docker.network.bridge.host_binding_ipv4": "0.0.0.0",
                    "com.docker.network.bridge.name": "docker0",
                    "com.docker.network.driver.mtu": "1500"
                },
                "labels": {
                    "com.docker.compose.network": "default",
                    "com.docker.compose.project": "myproject"
                },
                "containers": {
                    "container1": {
                        "Name": "web",
                        "EndpointID": "abcd1234...",
                        "MacAddress": "02:42:ac:11:00:02",
                        "IPv4Address": "172.17.0.2/16",
                        "IPv6Address": ""
                    }
                }
            }
        }
    )
    
    @classmethod
    def from_network(cls, network: Any) -> 'NetworkInspectResult':
        """Create a NetworkInspectResult from a Docker network object.
        
        Args:
            network: A Docker SDK network object
            
        Returns:
            A NetworkInspectResult instance populated from the Docker network
            
        Raises:
            ValueError: If the network object is None or invalid
        """
        if not network:
            raise ValueError("Network cannot be None")
            
        attrs = network.attrs
        return cls(
            name=attrs.get('Name', ''),
            id=attrs.get('Id', ''),
            created=attrs.get('Created', ''),
            scope=attrs.get('Scope', ''),
            driver=attrs.get('Driver', ''),
            enable_ipv6=attrs.get('EnableIPv6', False),
            internal=attrs.get('Internal', False),
            attachable=attrs.get('Attachable', False),
            ingress=attrs.get('Ingress', False),
            ipam=attrs.get('IPAM', {}),
            options=attrs.get('Options', {}),
            labels=attrs.get('Labels', {}),
            containers=attrs.get('Containers', {})
        )
        
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Generate a dictionary representation of the model.
        
        Overrides the default to ensure proper serialization of custom types.
        """
        data = super().model_dump(exclude_none=True, **kwargs)
        
        # Ensure datetime is properly formatted
        if 'created' in data and data['created']:
            if isinstance(data['created'], datetime):
                data['created'] = data['created'].isoformat()
                
        return data


class NetworkInspectRequest(BaseModel):
    """Request model for inspecting a Docker network.
    
    This model defines the parameters for retrieving detailed information
    about a Docker network, including its configuration and connected containers.
    """
    network_id: str = Field(
        ...,
        min_length=1,
        description="ID or name of the network to inspect"
    )
    verbose: bool = Field(
        default=False,
        description="If True, includes additional low-level information"
    )
    scope: str = Field(
        default="local",
        description="Scope of the network ('local' or 'swarm')",
        pattern=r'^(local|swarm)$'
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "network_id": "my-network",
                "verbose": False,
                "scope": "local"
            }
        }
    )
    
    def to_docker_params(self) -> Dict[str, Any]:
        """Convert the request to parameters for Docker SDK.
        
        Returns:
            Dictionary of parameters for Docker SDK inspect operation
        """
        return {
            "name": self.network_id,
            "verbose": self.verbose,
            "scope": self.scope
        }


class NetworkInspectResponse(BaseResponse[NetworkInspectResult]):
    """Response model for inspecting a Docker network.
    
    This model extends BaseResponse with detailed network information
    retrieved from the Docker daemon.
    """
    data: NetworkInspectResult = Field(
        ...,
        description="Detailed network information and configuration"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Network details retrieved successfully",
                "data": {
                    "name": "bridge",
                    "id": "7d86d31b1478...",
                    "created": "2023-01-01T12:00:00Z",
                    "scope": "local",
                    "driver": "bridge",
                    "enable_ipv6": False,
                    "internal": False,
                    "attachable": False,
                    "ingress": False,
                    "ipam": {
                        "Driver": "default",
                        "Config": [
                            {
                                "Subnet": "172.17.0.0/16",
                                "Gateway": "172.17.0.1"
                            }
                        ]
                    },
                    "options": {
                        "com.docker.network.bridge.default_bridge": "true",
                        "com.docker.network.bridge.enable_icc": "true"
                    },
                    "labels": {
                        "com.docker.compose.network": "default"
                    },
                    "containers": {
                        "container1": {
                            "Name": "web",
                            "EndpointID": "abcd1234...",
                            "MacAddress": "02:42:ac:11:00:02",
                            "IPv4Address": "172.17.0.2/16"
                        }
                    }
                },
                "error": None
            }
        }
    )
    
    @classmethod
    def success(
        cls,
        data: NetworkInspectResult,
        message: str = "Network details retrieved successfully"
    ) -> 'NetworkInspectResponse':
        """Create a success response with network details.
        
        Args:
            data: NetworkInspectResult containing the network details
            message: Optional success message
            
        Returns:
            A NetworkInspectResponse instance with status 'success'
        """
        return cls(
            status="success",
            message=message,
            data=data
        )
    
    @classmethod
    def from_network(cls, network: Any) -> 'NetworkInspectResponse':
        """Create a response from a Docker network object.
        
        Args:
            network: A Docker SDK network object
            
        Returns:
            A NetworkInspectResponse with the network details
            
        Raises:
            ValueError: If the network object is None or invalid
        """
        if not network:
            raise ValueError("Network cannot be None")
            
        return cls.success(
            data=NetworkInspectResult.from_network(network)
        )
        
    @classmethod
    def error(
        cls,
        error: Union[str, Exception],
        message: str = "Failed to inspect network",
        network_id: str = ""
    ) -> 'NetworkInspectResponse':
        """Create an error response."""
        return cls(
            status="error",
            message=message,
            error=error,
            data=NetworkInspectResult(
                id="",
                name="",
                driver="",
                scope="",
                created=datetime.now(),
                enable_ipv6=False,
                internal=False,
                attachable=False,
                ingress=False,
                ipam={},
                options={},
                labels={},
                containers={}
            )
        )


class NetworkListRequest(BaseModel):
    """Request model for listing Docker networks with filtering options.
    
    This model defines the parameters for listing Docker networks with various
    filtering capabilities to narrow down the results.
    """
    names: Optional[List[str]] = Field(
        default=None,
        description="List of network names to include in the results"
    )
    ids: Optional[List[str]] = Field(
        default=None,
        description="List of network IDs to include in the results"
    )
    driver: Optional[str] = Field(
        default=None,
        description="Filter networks by driver (e.g., 'bridge', 'host')"
    )
    network_type: str = Field(
        default="all",
        description="Type of networks to include: 'all', 'custom', or 'builtin'"
    )
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Filter networks by label key-value pairs"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "names": ["bridge", "host"],
                "driver": "bridge",
                "network_type": "builtin",
                "labels": {"environment": "development"}
            }
        }
    )
    
    def to_docker_filters(self) -> Dict[str, Any]:
        """Convert the request to Docker API filters.
        
        Returns:
            Dictionary of filters compatible with Docker SDK
        """
        filters = {}
        
        if self.names:
            filters["name"] = self.names
            
        if self.ids:
            filters["id"] = self.ids
            
        if self.driver:
            filters["driver"] = [self.driver]
            
        if self.network_type != 'all':
            is_builtin = self.network_type == 'builtin'
            builtin_names = ['bridge', 'host', 'none']
            
            if is_builtin:
                if 'name' in filters:
                    filters['name'] = [n for n in filters['name'] if n in builtin_names]
                else:
                    filters['name'] = builtin_names
            else:
                if 'name' in filters:
                    filters['name'] = [n for n in filters['name'] if n not in builtin_names]
                else:
                    # This is a bit of a hack since Docker doesn't have a 'not in' filter
                    # We'll need to handle this in the actual filtering logic
                    pass
                    
        if self.labels:
            filters["label"] = [f"{k}={v}" for k, v in self.labels.items()]
            
        return filters


class NetworkSummary(BaseModel):
    """Summary information about a Docker network.
    
    This model provides a condensed view of a Docker network's properties,
    suitable for listing multiple networks without the full detail of inspection.
    """
    id: str = Field(
        ...,
        description="Unique identifier for the network"
    )
    name: str = Field(
        ...,
        description="Name of the network"
    )
    driver: str = Field(
        ...,
        description="Network driver in use (e.g., 'bridge', 'host', 'overlay')"
    )
    scope: str = Field(
        ...,
        description="Scope of the network ('local' or 'swarm')"
    )
    created: Optional[datetime] = Field(
        None,
        description="Timestamp when the network was created"
    )
    internal: bool = Field(
        ...,
        description="Whether the network is internal (no external access)"
    )
    enable_ipv6: bool = Field(
        ...,
        description="Whether IPv6 is enabled on the network"
    )
    ipam: Dict[str, Any] = Field(
        ...,
        description="IP Address Management configuration"
    )
    options: Dict[str, str] = Field(
        ...,
        description="Driver-specific options as key-value pairs"
    )
    labels: Dict[str, str] = Field(
        ...,
        description="User-defined metadata as key-value pairs"
    )
    containers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Containers connected to the network, keyed by container ID"
    )
    
    # Pydantic v2 model configuration
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        },
        json_schema_extra={
            "example": {
                "id": "7d86d31b1478...",
                "name": "bridge",
                "driver": "bridge",
                "scope": "local",
                "created": "2023-01-01T12:00:00Z",
                "internal": False,
                "enable_ipv6": False,
                "ipam": {
                    "Driver": "default",
                    "Config": [
                        {
                            "Subnet": "172.17.0.0/16",
                            "Gateway": "172.17.0.1"
                        }
                    ]
                },
                "options": {
                    "com.docker.network.bridge.default_bridge": "true"
                },
                "labels": {
                    "com.docker.compose.network": "default"
                },
                "containers": {
                    "container1": {
                        "Name": "web",
                        "EndpointID": "abcd1234...",
                        "MacAddress": "02:42:ac:11:00:02",
                        "IPv4Address": "172.17.0.2/16"
                    }
                }
            }
        }
    )
    
    @classmethod
    def from_network(cls, network: Any) -> 'NetworkSummary':
        """Create a NetworkSummary from a Docker network object.
        
        Args:
            network: A Docker SDK network object
            
        Returns:
            A NetworkSummary instance populated from the Docker network
            
        Raises:
            ValueError: If the network object is None or invalid
        """
        if not network:
            raise ValueError("Network cannot be None")
            
        attrs = network.attrs
        return cls(
            id=network.id,
            name=network.name,
            driver=attrs.get('Driver', ''),
            scope=attrs.get('Scope', ''),
            created=attrs.get('Created'),
            internal=attrs.get('Internal', False),
            enable_ipv6=attrs.get('EnableIPv6', False),
            ipam=attrs.get('IPAM', {}),
            options=attrs.get('Options', {}),
            labels=attrs.get('Labels', {}),
            containers=attrs.get('Containers', {})
        )
        
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Generate a dictionary representation of the model.
        
        Overrides the default to ensure proper serialization of custom types.
        """
        data = super().model_dump(exclude_none=True, **kwargs)
        
        # Ensure datetime is properly formatted
        if 'created' in data and data['created']:
            if isinstance(data['created'], datetime):
                data['created'] = data['created'].isoformat()
                
        return data


@mcp.tool
async def list_networks(params: NetworkListRequest) -> NetworkListResponse:
    """
    List Docker networks with optional filtering.
    
    This function lists all Docker networks, with options to filter by various
    criteria such as names, IDs, driver, and labels. It returns a structured
    response containing network summaries and metadata.
    
    Args:
        params: NetworkListRequest containing filtering parameters
            - names: List of network names to filter by
            - ids: List of network IDs to filter by
            - driver: Filter by network driver (e.g., 'bridge', 'host')
            - network_type: Type of networks to list ('all', 'builtin', 'custom')
            - labels: Dictionary of label key-value pairs to filter by
            
    Returns:
        NetworkListResponse containing:
            - status: Operation status ('success' or 'error')
            - message: Human-readable result message
            - data: List of NetworkSummary objects
            - count: Total number of networks returned
    
    Raises:
        docker.errors.APIError: If the Docker API returns an error
        Exception: For unexpected errors during network listing
    
    Examples:
        >>> # List all networks
        >>> await list_networks(NetworkListRequest())
        
        >>> # List only bridge networks
        >>> await list_networks(NetworkListRequest(driver="bridge"))
        
        >>> # List networks with specific labels
        >>> await list_networks(NetworkListRequest(
        ...     labels={"environment": "production"}
        ... ))
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get all networks
        networks = client.networks.list()
        
        # Apply filters
        if params.names:
            networks = [n for n in networks if n.name in params.names]
            
        if params.ids:
            networks = [n for n in networks if n.id in params.ids]
            
        if params.driver:
            networks = [n for n in networks if n.attrs.get('Driver') == params.driver]
            
        if params.network_type != 'all':
            is_builtin = params.network_type == 'builtin'
            networks = [
                n for n in networks 
                if (n.attrs.get('Name') in ['bridge', 'host', 'none']) == is_builtin
            ]
            
        if params.labels:
            networks = [
                n for n in networks
                if all(n.attrs.get('Labels', {}).get(k) == v 
                      for k, v in params.labels.items())
            ]
        
        # Convert to NetworkSummary objects
        network_summaries = []
        for net in networks:
            try:
                network_summaries.append(NetworkSummary.from_docker_network(net))
            except Exception as e:
                logger.warning(f"Error processing network {net.id}: {str(e)}")
                continue
        
        # Return success response with network summaries
        return NetworkListResponse.success(
            data=network_summaries,
            message=f"Found {len(network_summaries)} networks"
        )
        
    except DockerException as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkListResponse.error(
            error=error_msg,
            message="Failed to list networks due to Docker API error"
        )
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkListResponse.error(
            error=error_msg,
            message="An unexpected error occurred while listing networks"
        )
        return {"status": "error", "error": error_msg}

@mcp.tool
async def create_network(params: NetworkCreateRequest) -> NetworkCreateResponse:
    """
    Create a new Docker network.
    
    This function creates a new Docker network with the specified configuration,
    including IPAM settings, driver options, and labels.
    
    Args:
        params: NetworkCreateRequest containing:
            - name: Name of the network to create
            - driver: Network driver to use (default: 'bridge')
            - check_duplicate: Check for networks with same name (default: True)
            - internal: Restrict external access (default: False)
            - attachable: Enable manual container attachment (default: False)
            - ingress: Create an ingress network (default: False)
            - enable_ipv6: Enable IPv6 on the network (default: False)
            - labels: Dictionary of labels to apply to the network
            - options: Driver-specific options as key-value pairs
            - ipam: IPAM configuration (optional)
    
    Returns:
        NetworkCreateResponse containing:
            - status: Operation status ('success' or 'error')
            - message: Human-readable result message
            - data: Network creation details
            - network_id: ID of the created network
            - warning: Optional warning message if any
    
    Raises:
        docker.errors.APIError: If the Docker API returns an error
        ValueError: If the network configuration is invalid
        Exception: For unexpected errors during network creation
    
    Examples:
        >>> # Create a simple bridge network
        >>> await create_network(NetworkCreateRequest(
        ...     name="my-network",
        ...     driver="bridge"
        ... ))
        
        >>> # Create a network with custom IPAM settings
        >>> await create_network(NetworkCreateRequest(
        ...     name="custom-network",
        ...     ipam=NetworkIPAMConfig(
        ...         driver="default",
        ...         config=[{"subnet": "172.28.0.0/16"}]
        ...     )
        ... ))
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Prepare IPAM config if provided
        ipam_config = None
        if params.ipam:
            ipam_config = docker.types.IPAMConfig(
                driver=params.ipam.driver,
                pool_configs=params.ipam.config,
                options=params.ipam.options
            )
        
        # Create the network
        network = client.networks.create(
            name=params.name,
            driver=params.driver,
            check_duplicate=params.check_duplicate,
            internal=params.internal,
            attachable=params.attachable,
            ingress=params.ingress,
            enable_ipv6=params.enable_ipv6,
            options=params.options,
            labels=params.labels,
            ipam=ipam_config
        )
        
        # Get the network details
        network.reload()
        
        return NetworkCreateResponse.from_network(network)
        
    except docker.errors.APIError as e:
        error_msg = f'Docker API error: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return NetworkCreateResponse.error(
            error=error_msg,
            message="Failed to create network due to Docker API error"
        )
        
    except Exception as e:
        error_msg = f"Unexpected error creating network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkCreateResponse.error(
            error=error_msg,
            message="Failed to create network"
        )


@mcp.tool
async def connect_container_to_network(
    params: NetworkConnectRequest
) -> NetworkConnectResponse:
    """
    Connect a container to a network.
    
    This function connects a container to a Docker network with optional
    network-specific parameters like IP address and aliases.
    
    Args:
        params: NetworkConnectRequest containing:
            - container: Container ID or name to connect
            - network: Network ID or name to connect to
            - ipv4_address: IPv4 address to assign to the container
            - ipv6_address: IPv6 address to assign to the container
            - aliases: List of network-scoped aliases for the container
            - links: Mapping of container names to aliases for this connection
            - link_local_ips: List of link-local IP addresses
            - driver_opts: Driver options as key-value pairs
    
    Returns:
        NetworkConnectResponse containing:
            - status: Operation status ('success' or 'error')
            - message: Human-readable result message
            - data: Connection details
            - container_id: ID of the connected container
            - network_id: ID of the network connected to
    
    Raises:
        docker.errors.APIError: If the Docker API returns an error
        docker.errors.NotFound: If container or network doesn't exist
        docker.errors.ContainerError: If the container cannot be connected
        Exception: For unexpected errors during connection
    
    Examples:
        >>> # Basic container connection
    Example:
        >>> await connect_container_to_network(NetworkConnectRequest(
        ...     container="my-container",
        ...     network="my-network",
        ...     ipv4_address="172.30.100.104",
        ...     aliases=["web", "app"],
        ...     driver_opt={"com.docker.network.driver.mtu": "1500"}
        ... ))
        NetworkConnectResponse(
            status="success",
            message="Container connected to network successfully",
            data={
                "container_id": "a1b2c3d4e5f6",
                "network_id": "n1m2n3m4n5m6"
            },
            container_id="a1b2c3d4e5f6",
            network_id="n1m2n3m4n5m6"
        )
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the container and network objects
        container = client.containers.get(params.container)
        network = client.networks.get(params.network)
        
        # Prepare endpoint configuration
        endpoint_config = {}
        
        # Add IPAM configuration if IP addresses are provided
        if params.ipv4_address or params.ipv6_address:
            endpoint_config['ipam_config'] = client.api.create_ipam_config(
                ipv4_address=str(params.ipv4_address) if params.ipv4_address else None,
                ipv6_address=str(params.ipv6_address) if params.ipv6_address else None
            )
        
        # Add other connection parameters
        if params.aliases:
            endpoint_config['aliases'] = params.aliases
        if params.links:
            endpoint_config['links'] = params.links
        if params.link_local_ips:
            endpoint_config['link_local_ips'] = params.link_local_ips
        if params.driver_opt:
            endpoint_config['driver_opt'] = params.driver_opt
        if params.mac_address:
            endpoint_config['mac_address'] = params.mac_address
        
        # Connect the container to the network
        network.connect(container, **endpoint_config)
        
        # Log the successful connection
        logger.info(
            f"Connected container {container.id} to network {network.id} "
            f"with config: {endpoint_config}"
        )
        
        return NetworkConnectResponse.success_response(
            container_id=container.id,
            network_id=network.id,
            message=f"Container '{container.name}' connected to network '{network.name}'"
        )
        
    except docker.errors.NotFound as e:
        error_msg = f"Container or network not found: {str(e)}"
        logger.warning(error_msg)
        return NetworkConnectResponse.error(
            error=error_msg,
            message=f"Failed to find container or network: {str(e)}",
            container_id=params.container,
            network_id=params.network
        )
        
    except docker.errors.APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkConnectResponse.error(
            error=error_msg,
            message=f"Failed to connect container to network: {str(e)}",
            container_id=params.container,
            network_id=params.network
        )
        
    except Exception as e:
        error_msg = f"Unexpected error connecting container to network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkConnectResponse.error(
            error=error_msg,
            message="Failed to connect container to network due to an unexpected error",
            container_id=params.container,
            network_id=params.network
        )

@mcp.tool
async def disconnect_container_from_network(
    params: NetworkDisconnectRequest
) -> NetworkDisconnectResponse:
    """
    Disconnect a container from a network.
    
    This function disconnects a container from a Docker network.
    
    Args:
        params: NetworkDisconnectRequest containing disconnection parameters
        
    Returns:
        NetworkDisconnectResponse with the disconnection result
        
    Example:
        >>> await disconnect_container_from_network(NetworkDisconnectRequest(
        ...     container="my-container",
        ...     network="my-network",
        ...     force=False
        ... ))
        NetworkDisconnectResponse(
            status="success",
            message="Container disconnected from network successfully",
            data={
                "container_id": "a1b2c3d4e5f6",
                "network_id": "n1m2n3m4n5m6"
            },
            container_id="a1b2c3d4e5f6",
            network_id="n1m2n3m4n5m6"
        )
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the container and network objects
        container = client.containers.get(params.container)
        network = client.networks.get(params.network)
        
        # Disconnect the container from the network
        network.disconnect(container, force=params.force)
        
        # Log the successful disconnection
        logger.info(
            f"Disconnected container {container.id} from network {network.id}"
        )
        
        return NetworkDisconnectResponse.success_response(
            container_id=container.id,
            network_id=network.id,
            message=f"Container '{container.name}' disconnected from network '{network.name}'"
        )
        
    except docker.errors.NotFound as e:
        error_msg = f"Container or network not found: {str(e)}"
        logger.warning(error_msg)
        return NetworkDisconnectResponse.error(
            error=error_msg,
            message=f"Failed to find container or network: {str(e)}",
            container_id=params.container,
            network_id=params.network
        )
        
    except docker.errors.APIError as e:
        error_msg = f'Docker API error: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return NetworkDisconnectResponse.error(
            error=error_msg,
            message=f"Failed to disconnect container from network: {str(e)}",
            container_id=params.container,
            network_id=params.network
        )
        
    except Exception as e:
        error_msg = f"Unexpected error disconnecting container from network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkDisconnectResponse.error(
            error=error_msg,
            message=(
                "Failed to disconnect container from network due to an unexpected "
                "error"
            ),
            container_id=params.container,
            network_id=params.network
        )

@mcp.tool
async def inspect_network(
    params: NetworkInspectRequest
) -> NetworkInspectResponse:
    """Inspect a Docker network.
    
    This function retrieves detailed information about a specific Docker network.
    
    Args:
        params: NetworkInspectRequest containing inspection parameters
        
    Returns:
        NetworkInspectResponse containing detailed information about the network
        
    Example:
        >>> await inspect_network(NetworkInspectRequest(
        ...     network_id="my-network",
        ...     verbose=True,
        ...     scope="local"
        ... ))
        NetworkInspectResponse(
            status="success",
            message="Network details retrieved successfully",
            data={
                'id': 'a1b2c3d4e5f6',
                'name': 'my-network',
                'driver': 'bridge',
                'scope': 'local',
                'ipam': {...},
                'containers': {...},
                'options': {...},
                'labels': {...}
            }
        )
    """
    try:
        # Initialize Docker client
        client = docker.from_env()
        
        # Get the network
        network = client.networks.get(params.network_id)
        
        # Log the successful inspection
        logger.info(
            f"Inspected network {network.id} (name: {network.name})"
        )
        
        # Return the network information using the response model
        return NetworkInspectResponse.from_network(network)
        
    except docker.errors.NotFound as e:
        error_msg = f"Network not found: {str(e)}"
        logger.warning(error_msg)
        return NetworkInspectResponse.error(
            error=error_msg,
            message=f"Failed to find network: {str(e)}",
            network_id=params.network_id
        )
        
    except docker.errors.APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkInspectResponse.error(
            error=error_msg,
            message=f"Failed to inspect network: {str(e)}",
            network_id=params.network_id
        )
        
    except Exception as e:
        error_msg = f"Unexpected error inspecting network: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return NetworkInspectResponse.error(
            error=error_msg,
            message="Failed to inspect network due to an unexpected error",
            network_id=params.network_id
        )
