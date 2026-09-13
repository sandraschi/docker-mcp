"""Sync Docker queries for the web API.

docker-py calls are blocking. FastAPI handlers must run these via asyncio.to_thread
so GET /system/df (and list/inspect) cannot freeze the event loop for a minute.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dockermcp.docker_context import initialize_docker_connection
from dockermcp.tools.containers.list_containers import container_row, created_iso, format_ports


class DockerUnavailable(RuntimeError):
    """Raised when the daemon is not reachable."""


def require_client():
    """Return the shared docker client, reconnecting once if needed."""
    from dockermcp import docker_context

    client = docker_context.docker_client
    if client is None:
        initialize_docker_connection()
        client = docker_context.docker_client
    if client is None:
        raise DockerUnavailable(docker_context.docker_error or "Docker daemon not available")
    return client


def list_containers_sync(all_states: bool = True) -> dict[str, Any]:
    client = require_client()
    containers = client.containers.list(all=all_states)
    rows = [container_row(container) for container in containers]
    return {"status": "success", "message": f"Found {len(rows)} containers", "containers": rows}


def list_images_sync() -> dict[str, Any]:
    client = require_client()
    images = client.images.list(all=False)
    rows = []
    for image in images:
        attrs = image.attrs or {}
        tags = list(image.tags or [])
        created_raw = attrs.get("Created")
        if isinstance(created_raw, (int, float)):
            created = datetime.fromtimestamp(created_raw, tz=UTC).isoformat()
        else:
            created = str(created_raw or "")
        labels = attrs.get("Labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        rows.append(
            {
                "id": image.id,
                "repo_tags": tags,
                "created": created,
                "size": attrs.get("Size", 0) or 0,
                "shared_size": attrs.get("SharedSize", 0) or 0,
                "virtual_size": attrs.get("VirtualSize") or attrs.get("Size", 0) or 0,
                "labels": labels,
                "os": attrs.get("Os"),
                "architecture": attrs.get("Architecture"),
                "dangling": not tags,
            }
        )
    return {"status": "success", "images": rows, "count": len(rows)}


def inspect_container_sync(container_id: str) -> dict[str, Any]:
    client = require_client()
    container = client.containers.get(container_id)
    attrs = container.attrs or {}
    config = attrs.get("Config") or {}
    env_list = config.get("Env") or []
    environment = {}
    for item in env_list:
        if "=" in item:
            key, value = item.split("=", 1)
            environment[key] = value
        else:
            environment[item] = ""
    labels = config.get("Labels") or attrs.get("Labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    networks = (attrs.get("NetworkSettings") or {}).get("Networks") or {}
    return {
        "status": "success",
        "container": {
            "id": container.id,
            "name": container.name.lstrip("/"),
            "image": config.get("Image") or attrs.get("Image") or "",
            "image_id": attrs.get("Image"),
            "status": container.status,
            "state": attrs.get("State") or {},
            "created": created_iso(attrs.get("Created")),
            "command": config.get("Cmd"),
            "entrypoint": config.get("Entrypoint"),
            "working_dir": config.get("WorkingDir"),
            "user": config.get("User"),
            "hostname": config.get("Hostname"),
            "environment": environment,
            "labels": labels,
            "ports": format_ports(attrs),
            "port_bindings": (attrs.get("HostConfig") or {}).get("PortBindings") or {},
            "networks": {
                name: {
                    "ip_address": net.get("IPAddress"),
                    "gateway": net.get("Gateway"),
                    "mac_address": net.get("MacAddress"),
                    "aliases": net.get("Aliases") or [],
                }
                for name, net in networks.items()
                if isinstance(net, dict)
            },
            "mounts": attrs.get("Mounts") or [],
            "restart_policy": (attrs.get("HostConfig") or {}).get("RestartPolicy") or {},
            "privileged": bool((attrs.get("HostConfig") or {}).get("Privileged")),
            "compose_project": labels.get("com.docker.compose.project"),
            "compose_service": labels.get("com.docker.compose.service"),
            "compose_workdir": labels.get("com.docker.compose.project.working_dir"),
        },
    }


def container_logs_sync(container_id: str, tail: int = 200) -> dict[str, Any]:
    client = require_client()
    container = client.containers.get(container_id)
    raw = container.logs(tail=tail, timestamps=True)
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    return {"status": "success", "id": container.id, "tail": tail, "logs": text}


def inspect_image_sync(image_ref: str) -> dict[str, Any]:
    client = require_client()
    image = client.images.get(image_ref)
    attrs = image.attrs or {}
    config = attrs.get("Config") or {}
    labels = config.get("Labels") or attrs.get("Labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    exposed = list((config.get("ExposedPorts") or {}).keys())
    return {
        "status": "success",
        "image": {
            "id": image.id,
            "tags": list(image.tags or []),
            "repo_digests": attrs.get("RepoDigests") or [],
            "created": created_iso(attrs.get("Created")),
            "size": attrs.get("Size", 0) or 0,
            "architecture": attrs.get("Architecture"),
            "os": attrs.get("Os"),
            "variant": attrs.get("Variant"),
            "author": attrs.get("Author"),
            "comment": attrs.get("Comment"),
            "docker_version": attrs.get("DockerVersion"),
            "parent": attrs.get("Parent"),
            "labels": labels,
            "env": config.get("Env") or [],
            "cmd": config.get("Cmd"),
            "entrypoint": config.get("Entrypoint"),
            "working_dir": config.get("WorkingDir"),
            "user": config.get("User"),
            "exposed_ports": exposed,
            "volumes": list((config.get("Volumes") or {}).keys()),
            "rootfs": attrs.get("RootFS") or {},
        },
    }


def image_history_sync(image_ref: str) -> dict[str, Any]:
    client = require_client()
    image = client.images.get(image_ref)
    history = image.history()
    rows = []
    total = 0
    for item in history:
        size = item.get("Size", 0) or 0
        total += size
        created_raw = item.get("Created")
        if isinstance(created_raw, (int, float)):
            created = datetime.fromtimestamp(created_raw, tz=UTC).isoformat()
        else:
            created = str(created_raw or "")
        rows.append(
            {
                "id": item.get("Id"),
                "created": created,
                "created_by": item.get("CreatedBy") or "",
                "size": size,
                "comment": item.get("Comment") or "",
                "tags": item.get("Tags") or [],
            }
        )
    return {
        "status": "success",
        "image_id": image.id,
        "history": rows,
        "total_size": total,
        "layer_count": len(rows),
    }


def _format_bytes(size_bytes: int) -> str:
    if not size_bytes:
        return "0B"
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size_bytes)
    index = 0
    while value >= 1024 and index < len(size_names) - 1:
        value /= 1024.0
        index += 1
    return f"{value:.1f}{size_names[index]}"


def system_info_sync() -> dict[str, Any]:
    client = require_client()
    info = client.info()
    version = client.version()
    return {
        "status": "success",
        "system_info": {
            "docker_version": version.get("Version", "unknown"),
            "api_version": version.get("ApiVersion", "unknown"),
            "platform": (version.get("Platform") or {}).get("Name", "unknown"),
            "architecture": version.get("Arch", "unknown"),
            "kernel_version": version.get("KernelVersion", "unknown"),
            "operating_system": version.get("Os", "unknown"),
            "containers": {
                "total": info.get("Containers", 0),
                "running": info.get("ContainersRunning", 0),
                "paused": info.get("ContainersPaused", 0),
                "stopped": info.get("ContainersStopped", 0),
            },
            "images": {"total": info.get("Images", 0)},
            "memory": {
                "total": info.get("MemTotal", 0),
                "total_formatted": _format_bytes(info.get("MemTotal", 0) or 0),
            },
            "cpu": {"cores": info.get("NCPU", 0)},
        },
    }


def dashboard_sync() -> dict[str, Any]:
    """Fast overview: info() + running containers + image list. Never calls GET /system/df."""
    system_result = system_info_sync()
    containers = list_containers_sync(all_states=False)
    images = list_images_sync()
    image_total = sum(int(img.get("size") or 0) for img in images.get("images") or [])
    sys_info = system_result.get("system_info") or {}
    counts = sys_info.get("containers") or {}
    running = counts.get("running")
    total = counts.get("total")
    message = containers.get("message")
    if running is not None and total is not None:
        message = f"{running} running / {total} total"
    return {
        "containers": containers.get("containers", []),
        "containers_status": containers.get("status"),
        "containers_message": message,
        "system_info": sys_info,
        "system_status": system_result.get("status"),
        "disk_summary": None,
        "images_size_estimate": image_total,
        "images": (images.get("images") or [])[:12],
        "images_count": images.get("count", 0),
        "images_status": images.get("status"),
    }


def list_volumes_sync() -> dict[str, Any]:
    client = require_client()
    volumes = client.volumes.list()
    rows = []
    for volume in volumes:
        attrs = volume.attrs or {}
        labels = attrs.get("Labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        usage = attrs.get("UsageData") or {}
        rows.append(
            {
                "name": volume.name,
                "driver": attrs.get("Driver") or "local",
                "mountpoint": attrs.get("Mountpoint") or "",
                "created": attrs.get("CreatedAt") or "",
                "scope": attrs.get("Scope") or "local",
                "labels": labels,
                "options": attrs.get("Options") or {},
                "ref_count": usage.get("RefCount"),
                "size": usage.get("Size"),
            }
        )
    return {"status": "success", "volumes": rows, "count": len(rows)}


def inspect_volume_sync(name: str) -> dict[str, Any]:
    client = require_client()
    volume = client.volumes.get(name)
    attrs = volume.attrs or {}
    labels = attrs.get("Labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    return {
        "status": "success",
        "volume": {
            "name": volume.name,
            "driver": attrs.get("Driver") or "local",
            "mountpoint": attrs.get("Mountpoint") or "",
            "created": attrs.get("CreatedAt") or "",
            "scope": attrs.get("Scope") or "local",
            "labels": labels,
            "options": attrs.get("Options") or {},
            "usage_data": attrs.get("UsageData") or {},
        },
    }


def list_networks_sync() -> dict[str, Any]:
    client = require_client()
    networks = client.networks.list()
    rows = []
    for network in networks:
        attrs = network.attrs or {}
        containers = attrs.get("Containers") or {}
        labels = attrs.get("Labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        ipam = attrs.get("IPAM") or {}
        configs = ipam.get("Config") or []
        subnet = configs[0].get("Subnet") if configs and isinstance(configs[0], dict) else None
        rows.append(
            {
                "id": network.id,
                "name": network.name,
                "driver": attrs.get("Driver") or "",
                "scope": attrs.get("Scope") or "local",
                "created": attrs.get("Created") or "",
                "internal": bool(attrs.get("Internal")),
                "enable_ipv6": bool(attrs.get("EnableIPv6")),
                "container_count": len(containers),
                "subnet": subnet,
                "labels": labels,
            }
        )
    return {"status": "success", "networks": rows, "count": len(rows)}


def inspect_network_sync(network_id: str) -> dict[str, Any]:
    client = require_client()
    network = client.networks.get(network_id)
    attrs = network.attrs or {}
    containers = attrs.get("Containers") or {}
    attached = []
    for cid, info in containers.items():
        if not isinstance(info, dict):
            continue
        attached.append(
            {
                "id": cid,
                "name": (info.get("Name") or "").lstrip("/"),
                "ipv4": info.get("IPv4Address"),
                "ipv6": info.get("IPv6Address"),
                "mac": info.get("MacAddress"),
            }
        )
    labels = attrs.get("Labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    return {
        "status": "success",
        "network": {
            "id": network.id,
            "name": network.name,
            "driver": attrs.get("Driver") or "",
            "scope": attrs.get("Scope") or "local",
            "created": attrs.get("Created") or "",
            "internal": bool(attrs.get("Internal")),
            "attachable": bool(attrs.get("Attachable")),
            "ingress": bool(attrs.get("Ingress")),
            "enable_ipv6": bool(attrs.get("EnableIPv6")),
            "ipam": attrs.get("IPAM") or {},
            "options": attrs.get("Options") or {},
            "labels": labels,
            "containers": attached,
        },
    }


def container_action_sync(container_id: str, action: str) -> dict[str, Any]:
    client = require_client()
    container = client.containers.get(container_id)
    if action == "start":
        container.start()
    elif action == "stop":
        container.stop(timeout=10)
    elif action == "restart":
        container.restart(timeout=10)
    else:
        raise ValueError(f"Unsupported action: {action}")
    container.reload()
    return {
        "status": "success",
        "action": action,
        "id": container.id,
        "name": container.name.lstrip("/"),
        "state": container.status,
    }


def disk_usage_sync() -> dict[str, Any]:
    """Slow path: docker system df. Call only from /api/disk, never the dashboard."""
    client = require_client()
    df_info = client.df()
    containers_size = sum((item.get("SizeRw") or 0) for item in df_info.get("Containers") or [])
    images_size = sum((item.get("Size") or 0) for item in df_info.get("Images") or [])
    volumes_size = sum(((item.get("UsageData") or {}).get("Size") or 0) for item in df_info.get("Volumes") or [])
    build_cache_size = sum((item.get("Size") or 0) for item in df_info.get("BuildCache") or [])
    total = containers_size + images_size + volumes_size + build_cache_size
    return {
        "status": "success",
        "disk_usage": {
            "summary": {
                "total_containers_size": containers_size,
                "total_images_size": images_size,
                "total_volumes_size": volumes_size,
                "total_build_cache_size": build_cache_size,
                "total_size": total,
            }
        },
    }
