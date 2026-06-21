"""
Docker Network Management for FastMCP 3.1+

This module provides comprehensive tools for managing Docker networks including:
- Creating and removing networks
- Connecting and disconnecting containers
- Inspecting network details
- Listing and filtering networks
- Managing IPAM (IP Address Management) configurations
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Network, IPv6Network
from typing import Any, Literal, TypeVar

from docker.errors import DockerException
from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, ValidationInfo, field_validator

from dockermcp.docker_context import check_docker_available, docker_client
from dockermcp.logging_config import logger
from dockermcp.mcp_instance import mcp

# Type variables for generic response models
T = TypeVar("T")


class BaseResponse[T](BaseModel):
    """Base response model for all API responses."""

    status: Literal["success", "error"] = Field(..., description="Status of the operation, either 'success' or 'error'")
    message: str | None = Field(default=None, description="Human-readable message about the result")
    data: T | None = Field(default=None, description="Response data if the operation was successful")
    error: str | None = Field(default=None, description="Error message if the operation failed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "success", "message": "Operation completed successfully", "data": {}, "error": None}
        },
        strict=True,
        validate_assignment=True,
        validate_default=True,
        extra="ignore",
        use_enum_values=True,
        from_attributes=True,
    )

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: Any, info: ValidationInfo) -> Any:
        if info.data.get("status") == "error" and v is not None:
            raise ValueError("Data should be None when status is 'error'")
        return v

    @field_validator("error")
    @classmethod
    def validate_error(cls, v: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("status") == "success" and v is not None:
            raise ValueError("Error should be None when status is 'success'")
        return v

    def model_dump_json(self, **kwargs) -> str:
        """Generate a JSON representation of the model with proper serialization."""
        return super().model_dump_json(exclude_none=True, **kwargs)

    @classmethod
    def success(
        cls: type[BaseResponse[T]], data: T = None, message: str = "Operation completed successfully"
    ) -> BaseResponse[T]:
        """Create a success response."""
        return cls(status="success", message=message, data=data)

    @classmethod
    def error_response(
        cls: type[BaseResponse[T]], error: str, message: str | None = None, data: Any = None
    ) -> BaseResponse[T]:
        """Create an error response."""
        return cls(status="error", message=message or "An error occurred", error=error, data=data)


class NetworkDriver(StrEnum):
    """Supported Docker network drivers."""

    BRIDGE = "bridge"
    HOST = "host"
    OVERLAY = "overlay"
    MACVLAN = "macvlan"
    IPVLAN = "ipvlan"
    NONE = "none"


class IPAMConfig(BaseModel):
    """IP Address Management configuration for Docker networks."""

    subnet: IPv4Network | IPv6Network | None = Field(
        None, description="The subnet in CIDR format (e.g., '172.28.0.0/16')"
    )
    ip_range: IPv4Network | IPv6Network | None = Field(
        None, description="Range of IPs from which to allocate container IPs"
    )
    gateway: IPvAnyAddress | None = Field(None, description="IPv4 or IPv6 gateway for the master subnet")
    aux_addresses: dict[str, IPvAnyAddress] | None = Field(
        None, description="Auxiliary IPv4 or IPv6 addresses used by the network driver"
    )

    model_config = ConfigDict(json_schema_extra={"example": {"subnet": "172.28.0.0/16", "gateway": "172.28.5.1"}})


class NetworkListRequest(BaseModel):
    """Request model for listing Docker networks with filtering options."""

    names: list[str] | None = Field(default=None, description="List of network names to include in the results")
    ids: list[str] | None = Field(default=None, description="List of network IDs to include in the results")
    driver: str | None = Field(default=None, description="Filter networks by driver (e.g., 'bridge', 'host')")
    network_type: str = Field(default="all", description="Type of networks to include: 'all', 'custom', or 'builtin'")
    labels: dict[str, str] | None = Field(default=None, description="Filter networks by label key-value pairs")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "names": ["bridge", "host"],
                "driver": "bridge",
                "network_type": "builtin",
                "labels": {"environment": "development"},
            }
        }
    )


class NetworkSummary(BaseModel):
    """Summary information about a Docker network."""

    id: str = Field(..., description="Unique identifier for the network")
    name: str = Field(..., description="Name of the network")
    driver: str = Field(..., description="Network driver in use")
    scope: str = Field(..., description="Scope of the network ('local' or 'swarm')")
    created: datetime | None = Field(None, description="Creation timestamp")
    internal: bool = Field(..., description="Whether the network is internal")
    enable_ipv6: bool = Field(..., description="Whether IPv6 is enabled")
    ipam: dict[str, Any] = Field(..., description="IPAM configuration")
    options: dict[str, str] = Field(..., description="Driver-specific options")
    labels: dict[str, str] = Field(..., description="User-defined labels")
    containers: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Connected containers")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_docker_network(cls, network: Any) -> NetworkSummary:
        """Create a NetworkSummary from a Docker network object."""
        attrs = network.attrs

        # Safely parse creation time
        created_str = attrs.get("Created", "")
        created_dt = None
        if created_str:
            try:
                # Docker uses ISO format but can have long precision
                iso_str = created_str.split(".")[0] + "Z"
                created_dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            except Exception:
                logger.debug("Failed to parse creation timestamp, ignoring")

        return cls(
            id=network.id,
            name=network.name,
            driver=attrs.get("Driver", ""),
            scope=attrs.get("Scope", "local"),
            created=created_dt,
            internal=attrs.get("Internal", False),
            enable_ipv6=attrs.get("EnableIPv6", False),
            ipam=attrs.get("IPAM", {}),
            options=attrs.get("Options", {}),
            labels=attrs.get("Labels", {}),
            containers=attrs.get("Containers", {}),
        )


class NetworkListResponse(BaseResponse[list[NetworkSummary]]):
    """Response model for network listing."""

    count: int = Field(0, description="Number of networks returned")


class NetworkCreateRequest(BaseModel):
    """Request model for creating a Docker network."""

    name: str = Field(..., description="Name of the network")
    driver: str = Field("bridge", description="Network driver")
    internal: bool = Field(False, description="Restrict external access")
    enable_ipv6: bool = Field(False, description="Enable IPv6 networking")
    attachable: bool = Field(True, description="Enable manual container attachment")
    labels: dict[str, str] = Field(default_factory=dict, description="Metadata labels")
    options: dict[str, str] = Field(default_factory=dict, description="Driver options")
    check_duplicate: bool = Field(True, description="Check for existing networks")
    ingress: bool = Field(False, description="Whether to create ingress network")
    ipam: dict[str, Any] | None = Field(None, description="IPAM configuration")


class NetworkCreateResponse(BaseResponse[NetworkSummary]):
    """Response model for network creation."""

    pass


class NetworkConnectRequest(BaseModel):
    """Request model for connecting a container to a network."""

    network: str = Field(..., description="ID or name of the network")
    container: str = Field(..., description="ID or name of the container")
    ipv4_address: IPvAnyAddress | None = Field(None, description="Static IPv4")
    ipv6_address: IPvAnyAddress | None = Field(None, description="Static IPv6")
    aliases: list[str] = Field(default_factory=list, description="Network aliases")
    links: list[str] | None = Field(default=None, description="Container links")
    link_local_ips: list[str] | None = Field(default=None, description="Link-local IPs")
    driver_opt: dict[str, str] | None = Field(default=None, description="Driver options")
    mac_address: str | None = Field(default=None, description="MAC address")


class NetworkConnectResponse(BaseResponse[dict[str, str]]):
    """Response model for network connection."""

    pass


class NetworkDisconnectRequest(BaseModel):
    """Request model for disconnecting a container from a network."""

    network: str = Field(..., description="ID or name of the network")
    container: str = Field(..., description="ID or name of the container")
    force: bool = Field(False, description="Force disconnection")


class NetworkDisconnectResponse(BaseResponse[dict[str, str]]):
    """Response model for network disconnection."""

    pass


class NetworkInspectResult(NetworkSummary):
    """Detailed information about a Docker network from inspection."""

    attachable: bool = Field(..., description="Attachable status")
    ingress: bool = Field(..., description="Ingress status")

    @classmethod
    def from_network(cls, network: Any) -> NetworkInspectResult:
        """Convert a Docker SDK network object to NetworkInspectResult."""
        summary = NetworkSummary.from_docker_network(network)
        attrs = network.attrs
        return cls(
            **summary.model_dump(), attachable=attrs.get("Attachable", False), ingress=attrs.get("Ingress", False)
        )


class NetworkInspectResponse(BaseResponse[NetworkInspectResult]):
    """Response model for network inspection."""

    pass


# Tools implementation


@mcp.tool
@check_docker_available
async def remove_network(network_id: str, force: bool = False) -> dict[str, Any]:
    """
    Remove a Docker network by ID or name.

    Args:
        network_id: ID or name of the network to remove
        force: Force removal even if in use
    """
    try:
        client = docker_client
        network = client.networks.get(network_id)
        network.remove(force=force)

        logger.info(f"Successfully removed network: {network_id}")
        return {
            "status": "success",
            "message": f"Network '{network_id}' removed successfully",
            "network_id": network_id,
        }
    except Exception as e:
        error_msg = f"Failed to remove network {network_id}: {e!s}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg, "error": str(e)}


@mcp.tool
@check_docker_available
async def list_networks(params: NetworkListRequest) -> NetworkListResponse:
    """
    List Docker networks with optional filtering.
    """
    try:
        client = docker_client
        networks = client.networks.list()

        # Apply filters
        if params.names:
            networks = [n for n in networks if n.name in params.names]
        if params.ids:
            networks = [n for n in networks if n.id in params.ids]
        if params.driver:
            networks = [n for n in networks if n.attrs.get("Driver") == params.driver]
        if params.network_type != "all":
            is_builtin = params.network_type == "builtin"
            networks = [n for n in networks if (n.attrs.get("Name") in ["bridge", "host", "none"]) == is_builtin]
        if params.labels:
            networks = [
                n for n in networks if all(n.attrs.get("Labels", {}).get(k) == v for k, v in params.labels.items())
            ]

        summaries = [NetworkSummary.from_docker_network(n) for n in networks]
        return NetworkListResponse.success(data=summaries, message=f"Found {len(summaries)} networks")
    except DockerException as e:
        return NetworkListResponse.error_response(error=str(e), message="Docker API error")
    except Exception as e:
        return NetworkListResponse.error_response(error=str(e), message="Unexpected error")


@mcp.tool
@check_docker_available
async def create_network(params: NetworkCreateRequest) -> NetworkCreateResponse:
    """
    Create a new Docker network.
    """
    try:
        client = docker_client

        network = client.networks.create(
            name=params.name,
            driver=params.driver,
            internal=params.internal,
            enable_ipv6=params.enable_ipv6,
            attachable=params.attachable,
            labels=params.labels,
            options=params.options,
            check_duplicate=params.check_duplicate,
            ingress=params.ingress,
            ipam=params.ipam,
        )

        return NetworkCreateResponse.success(
            data=NetworkSummary.from_docker_network(network), message=f"Network '{params.name}' created successfully"
        )
    except Exception as e:
        return NetworkCreateResponse.error_response(error=str(e), message="Failed to create network")


@mcp.tool
@check_docker_available
async def connect_container_to_network(params: NetworkConnectRequest) -> NetworkConnectResponse:
    """
    Connect a container to a network.
    """
    try:
        client = docker_client
        container = client.containers.get(params.container)
        network = client.networks.get(params.network)

        endpoint_config = {}
        if params.ipv4_address or params.ipv6_address:
            endpoint_config["ipam_config"] = client.api.create_ipam_config(
                ipv4_address=str(params.ipv4_address) if params.ipv4_address else None,
                ipv6_address=str(params.ipv6_address) if params.ipv6_address else None,
            )

        if params.aliases:
            endpoint_config["aliases"] = params.aliases
        if params.links:
            endpoint_config["links"] = params.links
        if params.link_local_ips:
            endpoint_config["link_local_ips"] = params.link_local_ips
        if params.driver_opt:
            endpoint_config["driver_opt"] = params.driver_opt
        if params.mac_address:
            endpoint_config["mac_address"] = params.mac_address

        network.connect(container, **endpoint_config)

        return NetworkConnectResponse.success(
            data={"container_id": container.id, "network_id": network.id},
            message=f"Container '{container.name}' connected to network '{network.name}'",
        )
    except Exception as e:
        return NetworkConnectResponse.error_response(error=str(e))


@mcp.tool
@check_docker_available
async def disconnect_container_from_network(params: NetworkDisconnectRequest) -> NetworkDisconnectResponse:
    """
    Disconnect a container from a network.
    """
    try:
        client = docker_client
        container = client.containers.get(params.container)
        network = client.networks.get(params.network)

        network.disconnect(container, force=params.force)

        return NetworkDisconnectResponse.success(
            data={"container_id": container.id, "network_id": network.id},
            message=f"Container '{container.name}' disconnected from network '{network.name}'",
        )
    except Exception as e:
        return NetworkDisconnectResponse.error_response(error=str(e))


@mcp.tool
@check_docker_available
async def inspect_network(params: str | dict[str, Any]) -> NetworkInspectResponse:
    """
    Inspect a Docker network.

    Args:
        params: Network ID or name, or a dictionary containing 'network_id'
    """
    try:
        network_id = params if isinstance(params, str) else params.get("network_id")
        if not network_id:
            return NetworkInspectResponse.error_response(error="Missing network_id")

        client = docker_client
        network = client.networks.get(network_id)

        return NetworkInspectResponse.success(
            data=NetworkInspectResult.from_network(network), message=f"Network '{network_id}' inspected successfully"
        )
    except Exception as e:
        return NetworkInspectResponse.error_response(error=str(e))
