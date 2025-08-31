"""
Network models for Docker MCP.

This module contains Pydantic models for network-related requests and responses.
"""
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo
from pydantic.networks import IPv4Address, IPv6Address
from typing import Annotated
from datetime import datetime
from enum import Enum

class NetworkDriver(str, Enum):
    """Supported network drivers."""
    BRIDGE = "bridge"
    OVERLAY = "overlay"
    HOST = "host"
    NONE = "none"
    MACVLAN = "macvlan"
    IPVLAN = "ipvlan"

class NetworkScope(str, Enum):
    """Network scope types."""
    LOCAL = "local"
    SWARM = "swarm"

class NetworkStatus(str, Enum):
    """Network status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"

class NetworkInfo(BaseModel):
    """Network information model."""
    Id: str = Field(..., description="Network ID")
    Name: str = Field(..., description="Network name")
    Driver: str = Field(..., description="Network driver")
    Scope: str = Field(..., description="Network scope (local, swarm)")
    EnableIPv6: bool = Field(False, description="IPv6 enabled on the network")
    IPAM: Dict[str, Any] = Field(default_factory=dict, description="IPAM configuration")
    Internal: bool = Field(False, description="Restricts external access to the network")
    Attachable: bool = Field(False, description="Manual container attachment enabled")
    Ingress: bool = Field(False, description="Swarm routing-mesh network")
    Containers: Dict[str, Any] = Field(default_factory=dict, description="Containers in the network")
    Options: Dict[str, str] = Field(default_factory=dict, description="Driver-specific options")
    Labels: Dict[str, str] = Field(default_factory=dict, description="User-defined key/value metadata")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "Id": "7d86d31b1478e7cc9a2c8b8c4b982a5eafc70b5349d0d5a5875a855d0f2d2b3d",
                "Name": "my_network",
                "Driver": "bridge",
                "Scope": "local",
                "EnableIPv6": False,
                "Internal": False,
                "Attachable": False,
                "Ingress": False
            }
        }
    )
    
    def model_dump_json(self, **kwargs):
        # Custom JSON serialization for datetime fields
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
            
        return super().model_dump_json(
            **kwargs,
            default=default_serializer
        )

class NetworkResponse(BaseModel):
    """Standard network operation response."""
    success: bool
    message: str
    network: Optional[NetworkInfo] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class NetworkListResponse(BaseModel):
    """Response model for listing networks."""
    success: bool
    message: str
    networks: List[NetworkInfo]
    error: Optional[str] = None

class IPAMPoolConfig(BaseModel):
    """IPAM pool configuration."""
    subnet: str = Field(..., description="Subnet in CIDR format")
    iprange: Optional[str] = Field(None, description="Allocate container IPs from a sub-range")
    gateway: Optional[str] = Field(None, description="Gateway address")
    aux_addresses: Optional[Dict[str, str]] = Field(
        None,
        description="Auxiliary IPv4 or IPv6 addresses used by the network driver"
    )

class IPAMConfig(BaseModel):
    """IP Address Management configuration."""
    driver: str = Field("default", description="IPAM driver to use")
    options: Optional[Dict[str, str]] = Field(None, description="Driver-specific options")
    config: Optional[List[IPAMPoolConfig]] = Field(None, description="List of IPAM configuration options")

class NetworkConfig(BaseModel):
    """Base network configuration options."""
    enable_ipv6: bool = Field(False, description="Enable IPv6 on the network")
    attachable: bool = Field(False, description="Enable manual container attachment")
    ingress: bool = Field(False, description="Create swarm routing-mesh network")
    scope: NetworkScope = Field(NetworkScope.LOCAL, description="Network scope")
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="User-defined key/value metadata"
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="Driver-specific options"
    )

class CreateNetworkRequest(NetworkConfig):
    """Request model for creating a network."""
    name: str = Field(
        ...,
        description="Name of the network to create",
        min_length=2,
        max_length=64,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
    )
    driver: NetworkDriver = Field(
        default=NetworkDriver.BRIDGE,
        description="Network driver to use"
    )
    check_duplicate: bool = Field(
        default=True,
        description="Check for networks with duplicate names"
    )
    internal: bool = Field(
        default=False,
        description="Restrict external access to the network"
    )
    ipam: Optional[IPAMConfig] = Field(
        None,
        description="Custom IPAM configuration"
    )
    mtu: Optional[int] = Field(
        None,
        ge=68,
        le=65535,
        description="Set the containers network MTU"
    )
    encrypted: bool = Field(
        default=False,
        description="Enable MAC learning for the network (overlay networks only)"
    )
    attachable: bool = Field(
        default=False,
        description="Enable manual container attachment"
    )
    ipam: Optional[Dict[str, Any]] = Field(
        default=None,
        description="IPAM configuration"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels to apply to the network"
    )

class NetworkOperationRequest(BaseModel):
    """Base request model for network operations."""
    network_id: str = Field(
        ...,
        description="Name or ID of the network"
    )

class EndpointIPAMConfig(BaseModel):
    """Endpoint IPAM configuration."""
    ipv4_address: Optional[str] = Field(None, description="IPv4 address")
    ipv6_address: Optional[str] = Field(None, description="IPv6 address")
    link_local_ips: List[str] = Field(
        default_factory=list,
        description="List of link-local IPv4/IPv6 addresses"
    )

class EndpointSettings(BaseModel):
    """Network endpoint settings."""
    ipam_config: Optional[EndpointIPAMConfig] = Field(
        None,
        description="IPAM configuration for the endpoint"
    )
    links: Optional[List[str]] = Field(
        None,
        description="List of links for this endpoint"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="List of DNS names for this endpoint"
    )
    network_id: Optional[str] = Field(
        None,
        description="Unique ID of the network"
    )
    endpoint_id: Optional[str] = Field(
        None,
        description="Unique ID for the service endpoint"
    )
    gateway: Optional[str] = Field(
        None,
        description="Gateway address for this network"
    )
    ip_address: Optional[str] = Field(
        None,
        description="IPv4 address"
    )
    ip_prefix_len: Optional[int] = Field(
        None,
        ge=0,
        le=32,
        description="Mask length of the IPv4 address"
    )
    ipv6_gateway: Optional[str] = Field(
        None,
        description="IPv6 gateway address"
    )
    global_ipv6_address: Optional[str] = Field(
        None,
        description="Global IPv6 address"
    )
    global_ipv6_prefix_len: Optional[int] = Field(
        None,
        ge=0,
        le=128,
        description="Mask length of the global IPv6 address"
    )
    mac_address: Optional[str] = Field(
        None,
        description="MAC address for the endpoint"
    )

class ConnectContainerRequest(BaseModel):
    """Request model for connecting a container to a network."""
    network_id: str = Field(
        ...,
        description="Name or ID of the network"
    )
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    endpoint_config: Optional[EndpointSettings] = Field(
        None,
        description="Advanced endpoint configuration"
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="List of network-scoped aliases for the container"
    )
    ipv4_address: Optional[str] = Field(
        None,
        description="IPv4 address for the container on this network"
    )
    ipv6_address: Optional[str] = Field(
        None,
        description="IPv6 address for the container on this network"
    )
    links: Optional[List[str]] = Field(
        None,
        description="List of links for this endpoint"
    )
    link_local_ips: Optional[List[str]] = Field(
        None,
        description="List of link-local IP addresses"
    )

class DisconnectContainerRequest(BaseModel):
    """Request model for disconnecting a container from a network."""
    network_id: str = Field(
        ...,
        description="Name or ID of the network"
    )
    container_id: str = Field(
        ...,
        description="ID or name of the container"
    )
    force: bool = Field(
        default=False,
        description="Force the container to disconnect from the network"
    )

class PruneNetworksRequest(BaseModel):
    """Request model for pruning unused networks."""
    filters: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Filters to process on the prune list"
    )
    until: Optional[str] = Field(
        None,
        description="Only remove networks created before this timestamp"
    )

class PruneNetworksResponse(BaseModel):
    """Response model for pruning networks."""
    networks_deleted: List[str] = Field(
        default_factory=list,
        description="List of deleted network IDs"
    )
    space_reclaimed: int = Field(
        0,
        description="Disk space reclaimed in bytes"
    )

class NetworkInspectRequest(NetworkOperationRequest):
    """Request model for inspecting a network."""
    verbose: bool = Field(
        default=False,
        description="Detailed inspect output for the network"
    )
    scope: Optional[str] = Field(
        None,
        description="Filter the network by scope (swarm, global, or local)"
    )

class NetworkStatsRequest(NetworkOperationRequest):
    """Request model for getting network statistics."""
    containers: bool = Field(
        default=True,
        description="Include container statistics"
    )
    interfaces: bool = Field(
        default=False,
        description="Include network interface statistics"
    )

class NetworkConnectivityTestRequest(BaseModel):
    """Request model for testing network connectivity."""
    source: str = Field(
        ...,
        description="Source container ID or name"
    )
    target: str = Field(
        ...,
        description="Target container ID, name, or IP address"
    )
    protocol: str = Field(
        "tcp",
        description="Protocol to test (tcp, udp, or icmp)",
        pattern="^(tcp|udp|icmp)$"
    )
    port: Optional[int] = Field(
        None,
        ge=1,
        le=65535,
        description="Port number to test (required for tcp/udp)"
    )
    timeout: int = Field(
        5,
        ge=1,
        le=60,
        description="Timeout in seconds"
    )

    @field_validator('port')
    def validate_port(cls, v, info: ValidationInfo):
        data = info.data
        if data.get('protocol') in ['tcp', 'udp'] and v is None:
            raise ValueError("Port is required for tcp/udp protocols")
        return v
