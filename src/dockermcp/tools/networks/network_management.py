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
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

import docker
from docker.errors import DockerException, InvalidArgument
from fastmcp.exceptions import ToolError as ToolError
# Import the mcp instance for tool registration
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, IPvAnyAddress, IPvAnyNetwork, TypeAdapter, field_validator

from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

@mcp.tool("remove_network")
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
    """Base response model for all API responses."""
    status: Literal['success', 'error'] = Field(..., description="Status of the operation")
    message: Optional[str] = Field(None, description="Human-readable message about the result")
    data: Optional[T] = Field(None, description="Response data if successful")
    error: Optional[str] = Field(None, description="Error message if operation failed")

    @classmethod
    def success(
        cls: Type['BaseResponse[T]'],
        data: T = None,
        message: str = "Operation completed successfully"
    ) -> 'BaseResponse[T]':
        """Create a success response."""
        return cls(status='success', message=message, data=data)

    @classmethod
    def error_response(
        cls: Type['BaseResponse[T]'],
        error: str,
        message: str = None
    ) -> 'BaseResponse[T]':
        """Create an error response."""
        return cls(
            status='error',
            message=message or "An error occurred",
            error=error
        )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            IPv4Network: str,
            IPv6Network: str,
            ipaddress.IPv4Address: str,
            ipaddress.IPv6Address: str
        }

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
        json_encoders={
            IPv4Network: str,
            IPv6Network: str,
            ipaddress.IPv4Address: str,
            ipaddress.IPv6Address: str
        },
        json_schema_extra={
            "example": {
                "subnet": "172.28.0.0/16",
                "gateway": "172.28.5.1"
            }
        }
    )

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
    """Summary information about a Docker network."""
    id: str = Field(..., description="Network ID")
    name: str = Field(..., description="Network name")
    driver: str = Field(..., description="Network driver")
    scope: str = Field(..., description="Network scope (e.g., 'local', 'swarm')")
    created: Optional[datetime] = Field(None, description="When the network was created")
    internal: bool = Field(..., description="Whether the network is internal")
    enable_ipv6: bool = Field(..., description="Whether IPv6 is enabled")
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Network labels"
    )
    containers: Dict[str, Any] = Field(
        default_factory=dict,
        description="Containers connected to the network"
    )
    ipam: Dict[str, Any] = Field(
        default_factory=dict,
        description="IPAM configuration"
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7d86d31b1478...",
                "name": "my-network",
                "driver": "bridge",
                "scope": "local",
                "internal": False,
                "enable_ipv6": False,
                "labels": {"environment": "development"},
                "containers": {},
                "ipam": {"Driver": "default", "Config": [{"Subnet": "172.28.0.0/16"}]},
                "options": {}
            }
        }
    )

class NetworkListResponse(BaseModel):
    """Response model for listing Docker networks."""
    status: str = Field(..., description="Status of the operation")
    message: Optional[str] = Field(None, description="Human-readable message")
    data: List[NetworkSummary] = Field(default_factory=list, description="List of network summaries")
    count: int = Field(0, description="Number of networks returned")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
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
                        "internal": False,
                        "enable_ipv6": False,
                        "ipam": {"Driver": "default"},
                        "options": {},
                        "labels": {}
                    }
                ],
                "count": 1
            }
        }
    )
    
    @classmethod
    def model_validate(cls, data):
        """Validate and parse the response data."""
        if isinstance(data, dict):
            if 'data' not in data:
                data = {'data': data}
            if 'count' not in data:
                data['count'] = len(data.get('data', []))
        return cls(**data)

    @classmethod
    def success(cls, data: List[NetworkSummary], message: str = "Networks listed successfully") -> 'NetworkListResponse':
        """Create a success response for network listing."""
        return cls(
            status="success",
            message=message,
            data=data,
            count=len(data)
        )
        
    @classmethod
    def error(cls, error: str, message: str = "Failed to list networks") -> 'NetworkListResponse':
        """Create an error response for network listing."""
        return cls(
            status="error",
            message=message,
            error=error,
            data=[],
            count=0
        )

class NetworkIPAMConfig(BaseModel):
    """IPAM configuration for creating a Docker network."""
    driver: str = Field(
        default="default",
        description="IPAM driver to use"
    )
    config: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of IPAM config blocks"
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )

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
    """Request model for creating a new Docker network."""
    name: str = Field(..., description="Name of the network")
    driver: NetworkDriver = Field(
        default=NetworkDriver.BRIDGE,
        description="Driver to manage the Network"
    )
    check_duplicate: bool = Field(
        default=True,
        description="Check for networks with duplicate names"
    )
    internal: bool = Field(
        default=False,
        description="Restrict external access to the network"
    )
    attachable: bool = Field(
        default=False,
        description="Enable manual container attachment"
    )
    ingress: bool = Field(
        default=False,
        description="Create an ingress network which provides the routing-mesh"
    )
    enable_ipv6: bool = Field(
        default=False,
        description="Enable IPv6 on the network"
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to set on the network"
    )
    ipam: Optional[NetworkIPAMConfig] = Field(
        default=None,
        description="Optional custom IPAM configuration"
    )

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


class NetworkConnectResponse(BaseModel):
    """Response model for connecting a container to a network."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message")
    container_id: str = Field(..., description="ID of the container")
    network_id: str = Field(..., description="ID of the network")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Container connected to network successfully",
                "container_id": "c1d2e3f4g5h6",
                "network_id": "n1m2n3m4n5m6"
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
        """Create a success response for network connection."""
        return cls(
            status="success",
            message=message,
            container_id=container_id,
            network_id=network_id
        )
        
    @classmethod
    def error(
        cls,
        error: str,
        message: str = "Failed to connect container to network"
    ) -> 'NetworkConnectResponse':
        """Create an error response for network connection."""
        return cls(
            status="error",
            message=message,
            error=error,
            container_id="",
            network_id=""
        )


class NetworkConnectRequest(BaseModel):
    """Request model for connecting a container to a network."""
    container: str = Field(..., description="Container ID or name")
    network: str = Field(..., description="Network ID or name")
    ipv4_address: Optional[IPvAnyAddress] = Field(
        default=None,
        description="IPv4 address (e.g., 172.30.100.104)"
    )
    ipv6_address: Optional[IPvAnyAddress] = Field(
        default=None,
        description="IPv6 address (e.g., 2001:db8::33)"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="List of network-scoped aliases for the container"
    )
    links: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of container name to alias for linking"
    )
    link_local_ips: List[str] = Field(
        default_factory=list,
        description="List of link-local IP addresses"
    )
    driver_opt: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver options for the endpoint"
    )
    mac_address: Optional[str] = Field(
        default=None,
        description="MAC address for the container on this network"
    )

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
    """Request model for disconnecting a container from a network."""
    container: str = Field(..., description="Container ID or name")
    network: str = Field(..., description="Network ID or name")
    force: bool = Field(
        default=False,
        description="Force the container to disconnect from the network"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container": "my-container",
                "network": "my-network",
                "force": False
            }
        }
    )


class NetworkDisconnectResponse(BaseModel):
    """Response model for disconnecting a container from a network."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message")
    container_id: str = Field(..., description="ID of the container")
    network_id: str = Field(..., description="ID of the network")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response data"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if operation failed"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Container disconnected from network successfully",
                "container_id": "c1d2e3f4g5h6",
                "network_id": "n1m2n3m4n5m6",
                "data": {
                    "container_id": "c1d2e3f4g5h6",
                    "network_id": "n1m2n3m4n5m6"
                }
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
        """Create a success response for network disconnection."""
        return cls(
            status="success",
            message=message,
            container_id=container_id,
            network_id=network_id,
            data={"container_id": container_id, "network_id": network_id}
        )
        
    @classmethod
    def error(
        cls,
        error: str,
        message: str = "Failed to disconnect container from network"
    ) -> 'NetworkDisconnectResponse':
        """Create an error response for network disconnection."""
        return cls(
            status="error",
            message=message,
            error=error,
            container_id="",
            network_id="",
            data={}
        )


class NetworkInspectResult(BaseModel):
    """Detailed information about a Docker network."""
    name: str = Field(..., description="Name of the network")
    id: str = Field(..., description="ID of the network")
    created: datetime = Field(..., description="When the network was created")
    scope: str = Field(..., description="Scope of the network (e.g., 'local', 'swarm')")
    driver: str = Field(..., description="Driver used by the network")
    enable_ipv6: bool = Field(..., description="Whether IPv6 is enabled")
    internal: bool = Field(..., description="Whether the network is internal")
    attachable: bool = Field(..., description="Whether the network is attachable")
    ingress: bool = Field(..., description="Whether this is the ingress network")
    ipam: Dict[str, Any] = Field(..., description="IPAM configuration")
    options: Dict[str, str] = Field(..., description="Driver-specific options")
    labels: Dict[str, str] = Field(..., description="User-defined key/value metadata")
    containers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Information about containers in the network"
    )
    
    @classmethod
    def from_network(cls, network: Any) -> 'NetworkInspectResult':
        """Create a NetworkInspectResult from a Docker network object."""
        attrs = network.attrs
        return cls(
            name=attrs.get('Name', ''),
            id=attrs.get('Id', ''),
            created=attrs.get('Created', ''),
            scope=attrs.get('Scope', ''),
            driver=attrs.get('Driver', ''),
            enable_ipam=attrs.get('EnableIPv6', False),
            internal=attrs.get('Internal', False),
            attachable=attrs.get('Attachable', False),
            ingress=attrs.get('Ingress', False),
            ipam=attrs.get('IPAM', {}),
            options=attrs.get('Options', {}),
            labels=attrs.get('Labels', {}),
            containers=attrs.get('Containers', {})
        )


class NetworkInspectRequest(BaseModel):
    """Request model for inspecting a Docker network."""
    network_id: str = Field(..., description="Network ID or name")
    verbose: bool = Field(
        default=False,
        description="Detailed inspect output for the network"
    )
    scope: str = Field(
        default="local",
        description="Scope of the network (local or swarm)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "network_id": "my-network",
                "verbose": False,
                "scope": "local"
            }
        }
    )


class NetworkInspectResponse(BaseModel):
    """Response model for inspecting a Docker network."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Human-readable message")
    data: NetworkInspectResult = Field(..., description="Detailed network information")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Network details retrieved successfully",
                "data": {
                    "id": "a1b2c3d4e5f6",
                    "name": "my-network",
                    "driver": "bridge",
                    "scope": "local",
                    "created": "2023-01-01T12:00:00Z",
                    "enable_ipv6": False,
                    "internal": False,
                    "attachable": False,
                    "ingress": False,
                    "ipam": {"Driver": "default"},
                    "options": {},
                    "labels": {"environment": "development"},
                    "containers": {}
                }
            }
        }
    )
    
    @classmethod
    def success(
        cls,
        data: NetworkInspectResult,
        message: str = "Network details retrieved successfully"
    ) -> 'NetworkInspectResponse':
        """Create a success response with network details."""
        return cls(
            status="success",
            message=message,
            data=data
        )
    
    @classmethod
    def from_network(cls, network: Any) -> 'NetworkInspectResponse':
        """Create a response from a Docker network object."""
        return cls.success(
            data=NetworkInspectResult.from_network(network)
        )
    
    @classmethod
    def error(
        cls,
        error: str,
        message: str = "Failed to retrieve network details"
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
    """Request model for listing Docker networks."""
    names: Optional[List[str]] = Field(
        default=None,
        description="Filter networks by name"
    )
    ids: Optional[List[str]] = Field(
        default=None,
        description="Filter networks by ID"
    )
    driver: Optional[str] = Field(
        default=None,
        description="Filter by network driver"
    )
    network_type: str = Field(
        default="all",
        description="Filter by network type: 'all', 'custom', or 'builtin'"
    )
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Filter networks by labels"
    )

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


class NetworkSummary(BaseModel):
    """Summary information about a Docker network."""
    id: str = Field(..., description="ID of the network")
    name: str = Field(..., description="Name of the network")
    driver: str = Field(..., description="Driver used by the network")
    scope: str = Field(..., description="Scope of the network (e.g., 'local', 'swarm')")
    created: Optional[datetime] = Field(
        None,
        description="When the network was created"
    )
    internal: bool = Field(..., description="Whether the network is internal")
    enable_ipv6: bool = Field(..., description="Whether IPv6 is enabled")
    ipam: Dict[str, Any] = Field(..., description="IPAM configuration")
    options: Dict[str, str] = Field(..., description="Driver-specific options")
    labels: Dict[str, str] = Field(..., description="User-defined key/value metadata")
    containers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Information about containers in the network"
    )


@mcp.tool(
    name="list_networks",
    description="List Docker networks with optional filtering"
)
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
        client = docker.from_env()
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
        
        # Format the response
        network_summaries = []
        for net in networks:
            attrs = net.attrs
            network_summaries.append(NetworkSummary(
                id=net.id,
                name=net.name,
                driver=attrs.get('Driver', ''),
                scope=attrs.get('Scope', ''),
                created=datetime.fromisoformat(attrs['Created'][:-4]) if 'Created' in attrs else None,
                internal=attrs.get('Internal', False),
                enable_ipv6=attrs.get('EnableIPv6', False),
                labels=attrs.get('Labels', {}),
                containers=attrs.get('Containers', {}),
                ipam=attrs.get('IPAM', {}),
                options=attrs.get('Options', {})
            ))
        
        return NetworkListResponse.success(
            data=network_summaries,
            message=f"Found {len(network_summaries)} networks"
        )
        
    except DockerException as e:
        error_msg = f"Docker error: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "error": "Docker daemon not available"}
        
    except Exception as e:
        error_msg = f"Unexpected error listing networks: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}

@mcp.tool(
    name="create_network",
    description="Create a new Docker network"
)
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


@mcp.tool(
    name="connect_container_to_network",
    description="Connect a container to a network"
)
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

@mcp.tool(
    name="disconnect_container_from_network",
    description="Disconnect a container from a network"
)
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

@mcp.tool(
    name="inspect_network",
    description="Inspect a Docker network"
)
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
