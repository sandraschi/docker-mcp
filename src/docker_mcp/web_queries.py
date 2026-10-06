"""Sync Docker queries for the web API.

docker-py calls are blocking. FastAPI handlers must run these via asyncio.to_thread
so GET /system/df (and list/inspect) cannot freeze the event loop for a minute.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docker.errors import DockerException

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


# --- Image provenance: fleet-local build vs external registry ----------------

#: Default fleet checkout location. Overridable at runtime via
#: DOCKER_MCP_FLEET_ROOT, ~/.docker-mcp/settings.json, or PUT /api/settings/fleet.
#: Anyone cloning from GitHub will not have D:/Dev/repos — that is expected,
#: the setting exists precisely so they can point at their own checkout.
DEFAULT_FLEET_ROOT = "D:/Dev/repos"


def _settings_file() -> Path:
    return Path.home() / ".docker-mcp" / "settings.json"


def get_fleet_root() -> Path:
    """Resolve the fleet repos location: settings file > env > default."""
    try:
        raw = _settings_file().read_text(encoding="utf-8") or ""
        data = __import__("json").loads(raw) if raw.strip() else {}
        candidate = str(data.get("fleet_root") or "").strip()
        if candidate:
            return Path(candidate).expanduser()
    except Exception:
        pass
    env = (os.environ.get("DOCKER_MCP_FLEET_ROOT") or "").strip()
    if env:
        return Path(env).expanduser()
    return Path(DEFAULT_FLEET_ROOT)


def get_fleet_settings() -> dict[str, Any]:
    root = get_fleet_root()
    exists = root.is_dir()
    repos: list[str] = []
    if exists:
        try:
            repos = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))
        except Exception:
            repos = []
    return {
        "status": "success",
        "fleet_root": str(root),
        "exists": exists,
        "is_default": root.as_posix() == Path(DEFAULT_FLEET_ROOT).as_posix(),
        "repo_count": len(repos),
        "repos": repos[:50],
        "default": DEFAULT_FLEET_ROOT,
    }


def set_fleet_root(path: str) -> dict[str, Any]:
    candidate = (path or "").strip()
    if not candidate:
        raise ValueError("fleet_root is required")
    root = Path(candidate).expanduser()
    try:
        settings_file = _settings_file()
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {}
        try:
            raw = settings_file.read_text(encoding="utf-8")
            data = __import__("json").loads(raw) if raw.strip() else {}
        except Exception:
            data = {}
        data["fleet_root"] = str(root)
        settings_file.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot persist settings: {exc}") from exc
    result = get_fleet_settings()
    result["saved"] = True
    if not result["exists"]:
        result["warning"] = f"{root} does not exist yet — local-image matching is disabled until it does"
    return result


#: Local image name prefixes (no registry component) mapped to fleet repos.
LOCAL_IMAGE_PREFIXES: dict[str, str] = {
    "myai-": "myai",
    "deepfang-": "deepfang",
    "myconf-": "myconf",
    "tailscale-mcp-": "tailscale-mcp",
}

COMPOSE_FILENAMES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
)

#: Directories never descended into when scanning for compose files.
#: _upstream/_archives are third-party clones and frozen repos — never upped.
COMPOSE_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "target",
    "dist",
    "build",
    "_upstream",
    "_archives",
}

MAX_COMPOSE_SCAN_DEPTH = 4
MAX_COMPOSE_FILE_BYTES = 200_000


def _count_compose_services(path: Path) -> int | None:
    """Best-effort service count from a compose file (None when unparseable)."""
    try:
        if path.stat().st_size > MAX_COMPOSE_FILE_BYTES:
            return None
        try:
            import yaml  # type: ignore
        except Exception:
            return None
        raw = path.read_text(encoding="utf-8", errors="replace")
        doc = yaml.safe_load(raw)
        if not isinstance(doc, dict):
            return None
        services = doc.get("services")
        if isinstance(services, dict):
            return len(services)
        return None
    except Exception:
        return None


def scan_compose_files_sync(root: str | None = None) -> dict[str, Any]:
    """Walk the fleet repos folder for compose files (depth-limited, fast).

    Returns [{repo, path, name, size, modified, project_guess, services}].
    project_guess is the parent directory name (what `docker compose` would
    default the project name to); the frontend matches it against running
    projects for the "running" badge.
    """
    base = Path(root).expanduser() if root else get_fleet_root()
    files: list[dict[str, Any]] = []
    scanned_dirs = 0
    if not base.is_dir():
        return {
            "status": "success",
            "root": str(base),
            "exists": False,
            "files": [],
            "count": 0,
            "warning": f"{base} does not exist — set the repos folder in Settings",
        }

    def walk(directory: Path, depth: int) -> None:
        nonlocal scanned_dirs
        if depth > MAX_COMPOSE_SCAN_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name.lower())
        except Exception:
            return
        scanned_dirs += 1
        for entry in entries:
            name = entry.name
            if name.startswith(".") and name not in (".docker",):
                if entry.is_dir():
                    continue
            try:
                if entry.is_dir():
                    if name in COMPOSE_SKIP_DIRS:
                        continue
                    if entry.is_symlink():
                        continue
                    walk(entry, depth + 1)
                elif entry.is_file() and name.lower() in COMPOSE_FILENAMES:
                    try:
                        stat = entry.stat()
                    except Exception:
                        continue
                    try:
                        rel = entry.relative_to(base)
                        repo = rel.parts[0] if len(rel.parts) > 1 else base.name
                    except Exception:
                        repo = base.name
                    files.append(
                        {
                            "repo": repo,
                            "path": str(entry),
                            "name": name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                            "project_guess": entry.parent.name,
                            "services": _count_compose_services(entry),
                        }
                    )
            except Exception:
                continue

    walk(base, 0)
    files.sort(key=lambda f: (f["repo"].lower(), f["path"].lower()))
    return {
        "status": "success",
        "root": str(base),
        "exists": True,
        "files": files,
        "count": len(files),
        "scanned_dirs": scanned_dirs,
    }


_COMPOSE_FILES_CACHE: dict[str, Any] = {"at": 0.0, "payload": None}
COMPOSE_FILES_TTL_SECONDS = 300.0


def scan_compose_files_cached(refresh: bool = False) -> dict[str, Any]:
    """TTL-cached compose scan (5 min). The fleet walk touches 16k+ dirs; the
    file set barely changes, so rescan only on demand (?refresh=true)."""
    import time as _time

    now = _time.time()
    cached_at = float(_COMPOSE_FILES_CACHE.get("at") or 0.0)
    payload = _COMPOSE_FILES_CACHE.get("payload")
    if not refresh and payload is not None and now - cached_at < COMPOSE_FILES_TTL_SECONDS:
        result = dict(payload)
        result["cached"] = True
        return result
    result = scan_compose_files_sync()
    result["cached"] = False
    _COMPOSE_FILES_CACHE["at"] = now
    _COMPOSE_FILES_CACHE["payload"] = dict(result)
    return result


#: Well-known Docker Hub official library names (single-component refs).
DOCKERHUB_OFFICIAL = {
    "postgres",
    "redis",
    "traefik",
    "nginx",
    "mongo",
    "mysql",
    "valkey",
    "python",
    "node",
    "alpine",
    "busybox",
    "hello-world",
}

DEFAULT_NETWORKS = {"bridge", "host", "none"}
LARGE_IMAGE_BYTES = 1_000_000_000
OLD_IMAGE_DAYS = 180


def split_ref_tag(ref: str) -> tuple[str, str]:
    """Split 'name:tag' (or 'name@digest') into (name, tag)."""
    ref = (ref or "").strip()
    if "@" in ref:
        name, digest = ref.split("@", 1)
        return name, "@" + digest
    last = ref.rsplit("/", 1)[-1]
    if ":" in last:
        name, tag = ref.rsplit(":", 1)
        return name, tag
    return ref, "latest"


def image_provenance(ref: str) -> dict[str, Any]:
    """Classify where an image comes from: fleet-local build or external registry.

    Kinds: local | dockerhub-official | dockerhub-user | ghcr | lscr | gcr | registry.
    For local images, fleet_repo names the D:/Dev/repos checkout when it exists.
    hub_url points at Docker Hub (or the GitHub org for ghcr); github_url is a
    repo search for everything else so an external image can be traced in one click.
    """
    name, tag = split_ref_tag(ref or "")
    parts = name.split("/") if name else []
    registry: str | None = None
    namespace: str | None = None
    repo = name
    if parts and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        registry = parts[0]
        rest = parts[1:]
        if len(rest) > 1:
            namespace = "/".join(rest[:-1])
            repo = rest[-1]
        elif rest:
            repo = rest[0]
    elif len(parts) > 1:
        namespace = "/".join(parts[:-1])
        repo = parts[-1]
    elif parts:
        repo = parts[0]

    kind = "local"
    fleet_repo: str | None = None
    if registry == "ghcr.io":
        kind = "ghcr"
    elif registry == "lscr.io":
        kind = "lscr"
    elif registry in ("gcr.io", "k8s.gcr.io"):
        kind = "gcr"
    elif registry:
        kind = "registry"
    elif namespace:
        kind = "dockerhub-user"
    else:
        for prefix, frepo in LOCAL_IMAGE_PREFIXES.items():
            if repo.startswith(prefix):
                fleet_repo = frepo
                break
        if fleet_repo is None and repo in DOCKERHUB_OFFICIAL:
            kind = "dockerhub-official"
        elif fleet_repo is None:
            kind = "local"
            candidate = repo.split("-")[0] if "-" in repo else repo
            if (get_fleet_root() / candidate).is_dir():
                fleet_repo = candidate
        else:
            kind = "local"
    if fleet_repo is not None and not (get_fleet_root() / fleet_repo).is_dir():
        fleet_repo = None

    hub_url: str | None = None
    if kind == "dockerhub-official":
        hub_url = f"https://hub.docker.com/_/{repo}"
    elif kind == "dockerhub-user" and namespace:
        hub_url = f"https://hub.docker.com/r/{namespace}/{repo}"
    elif kind == "ghcr" and namespace:
        hub_url = f"https://github.com/{namespace}/{repo}"

    search_term = f"{namespace}/{repo}" if namespace and kind != "ghcr" else repo
    github_url = f"https://github.com/search?q={search_term}+in:name&type=repositories"
    if kind == "ghcr" and hub_url:
        github_url = hub_url

    return {
        "ref": ref,
        "name": name,
        "tag": tag,
        "registry": registry,
        "namespace": namespace,
        "repo": repo,
        "kind": kind,
        "fleet_repo": fleet_repo,
        "hub_url": hub_url,
        "github_url": github_url,
    }


def _image_usage_map(client) -> dict[str, list[str]]:
    """Map image id -> sorted container names using it (all states).

    Uses only the already-fetched list attrs (ImageID) — zero extra API calls.
    This matters: containers with wedged metadata (e.g. broken network
    endpoints) can stall a full inspect for seconds, and 46 sequential
    inspects turned /api/images into a multi-second call. Attrs are free.
    """
    usage: dict[str, list[str]] = {}
    try:
        containers = client.containers.list(all=True)
    except Exception:
        return usage
    for container in containers:
        try:
            attrs = container.attrs or {}
            iid = attrs.get("ImageID") or attrs.get("Image")
            if not iid:
                continue
            cname = (getattr(container, "name", "") or "").lstrip("/") or str(iid)[:12]
            usage.setdefault(iid, []).append(cname)
        except Exception:
            continue
    return {iid: sorted(names) for iid, names in usage.items()}


def list_images_sync() -> dict[str, Any]:
    client = require_client()
    # NOTE: use the raw list API, NOT client.images.list(). docker-py's
    # ImageCollection.list() is implemented as one full inspect per image
    # (44 images = 44 extra API calls + every per-image stall multiplied).
    # /images/json already carries tags, sizes, labels, os/arch in one call.
    summaries = client.api.images(all=False)
    usage = _image_usage_map(client)
    rows = []
    for item in summaries:
        if not isinstance(item, dict):
            continue
        tags = [t for t in (item.get("RepoTags") or []) if t and t != "<none>:<none>"]
        created_raw = item.get("Created")
        if isinstance(created_raw, (int, float)):
            created = datetime.fromtimestamp(created_raw, tz=UTC).isoformat()
        else:
            created = str(created_raw or "")
        labels = item.get("Labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        image_id = item.get("Id", "")
        primary = next((t for t in tags if t), "")
        used_by = usage.get(image_id, [])
        rows.append(
            {
                "id": image_id,
                "repo_tags": tags,
                "created": created,
                "size": item.get("Size", 0) or 0,
                "shared_size": item.get("SharedSize", 0) or 0,
                "virtual_size": item.get("VirtualSize") or item.get("Size", 0) or 0,
                "labels": labels,
                "os": item.get("Os"),
                "architecture": item.get("Architecture"),
                "dangling": not tags,
                "provenance": image_provenance(primary or image_id),
                "used_by": used_by,
                "used_count": len(used_by),
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
    try:
        system_result = system_info_sync()
        containers = list_containers_sync(all_states=False)
        images = list_images_sync()
    except (DockerUnavailable, DockerException, OSError) as exc:
        return {
            "containers": [],
            "containers_status": "error",
            "containers_message": f"Docker daemon offline: {exc}",
            "system_info": None,
            "system_status": "error",
            "disk_summary": None,
            "images_size_estimate": 0,
            "images": [],
            "images_count": 0,
            "images_status": "error",
            "volumes_count": None,
            "networks_count": None,
        }

    image_total = sum(int(img.get("size") or 0) for img in images.get("images") or [])
    sys_info = system_result.get("system_info") or {}
    counts = sys_info.get("containers") or {}
    running = counts.get("running")
    total = counts.get("total")
    message = containers.get("message")
    if running is not None and total is not None:
        message = f"{running} running / {total} total"
    # Light counts for the dashboard (no per-item inspect) so the overview
    # renders from this single aggregate instead of 4 extra HTTP calls.
    volumes_count = None
    networks_count = None
    try:
        _client = require_client()
        volumes_count = len(_client.volumes.list())
        networks_count = len(_client.networks.list())
    except Exception:
        pass
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
        "volumes_count": volumes_count,
        "networks_count": networks_count,
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
        # NOTE: the list API never populates Containers; inspect for the truth.
        try:
            detail = client.api.inspect_network(network.id) or {}
        except Exception:
            detail = {}
        containers = detail.get("Containers") or attrs.get("Containers") or {}
        labels = attrs.get("Labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        ipam = detail.get("IPAM") or attrs.get("IPAM") or {}
        configs = ipam.get("Config") or []
        subnets = [c.get("Subnet") for c in configs if isinstance(c, dict) and c.get("Subnet")]
        gateways = [c.get("Gateway") for c in configs if isinstance(c, dict) and c.get("Gateway")]
        rows.append(
            {
                "id": network.id,
                "name": network.name,
                "driver": detail.get("Driver") or attrs.get("Driver") or "",
                "scope": detail.get("Scope") or attrs.get("Scope") or "local",
                "created": detail.get("Created") or attrs.get("Created") or "",
                "internal": bool(detail.get("Internal", attrs.get("Internal"))),
                "enable_ipv6": bool(detail.get("EnableIPv6", attrs.get("EnableIPv6"))),
                "container_count": len(containers),
                "subnet": subnets[0] if subnets else None,
                "subnets": subnets,
                "gateway": gateways[0] if gateways else None,
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


def pull_image_sync(repository: str, tag: str = "latest") -> dict[str, Any]:
    """Pull an image and report whether the local copy was already current.

    Compares the image id before/after the pull: same id -> "already current",
    different id -> "updated", no before id -> freshly pulled.
    """
    client = require_client()
    repository = (repository or "").strip()
    if not repository:
        raise ValueError("repository is required")
    tag = (tag or "latest").strip() or "latest"
    last = repository.rsplit("/", 1)[-1]
    if ":" in last and "@" not in repository:
        repository, tag = repository.rsplit(":", 1)
    ref = f"{repository}:{tag}"
    before_id = None
    try:
        before_id = client.images.get(ref).id
    except Exception:
        before_id = None
    pulled = client.images.pull(repository, tag=tag)
    after_id = getattr(pulled, "id", None)
    digests: list[str] = []
    try:
        digests = list((getattr(pulled, "attrs", None) or {}).get("RepoDigests") or [])
    except Exception:
        digests = []
    if not after_id:
        try:
            after_obj = client.images.get(ref)
            after_id = after_obj.id
            digests = list((after_obj.attrs or {}).get("RepoDigests") or [])
        except Exception:
            after_id = None
    if before_id is None:
        message = f"Pulled {ref} (new)"
        already_current = False
        updated = True
    elif before_id == after_id:
        message = f"{ref} is already current"
        already_current = True
        updated = False
    else:
        message = f"{ref} updated"
        already_current = False
        updated = True
    return {
        "status": "success",
        "repository": repository,
        "tag": tag,
        "ref": ref,
        "before_id": before_id,
        "after_id": after_id,
        "updated": updated,
        "already_current": already_current,
        "message": message,
        "digests": digests,
    }


def _age_days(created: Any, now: datetime) -> int | None:
    try:
        text = str(created or "")
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return max(0, (now - parsed).days)
    except Exception:
        return None


def _image_item_summary(img: dict[str, Any], now: datetime, reason: str) -> dict[str, Any]:
    tags = img.get("repo_tags") or []
    ref = next((t for t in tags if t and t != "<none>:<none>"), img.get("id", ""))
    if "@sha256:" in ref:
        base = ref.split("@")[0] or str(img.get("id", ""))
        ref = f"{base}@sha256:{str(img.get('id', '')).replace('sha256:', '')[:12]}"
    prov = img.get("provenance") or {}
    return {
        "ref": ref,
        "id": img.get("id"),
        "size": img.get("size") or 0,
        "age_days": _age_days(img.get("created"), now),
        "used_count": img.get("used_count", 0),
        "kind": prov.get("kind"),
        "fleet_repo": prov.get("fleet_repo"),
        "reason": reason,
    }


# --- Upstream brief: what is this image? --------------------------------------

#: GitHub org/repo overrides where the container namespace does not match GitHub.
GITHUB_OVERRIDES = {
    "postgres": "docker-library/postgres",
    "redis": "docker-library/redis",
    "nginx": "docker-library/nginx",
    "prom/prometheus": "prometheus/prometheus",
    "prom/node-exporter": "prometheus/node_exporter",
    "prom/blackbox-exporter": "prometheus/blackbox_exporter",
    "otel/opentelemetry-collector-contrib": "open-telemetry/opentelemetry-collector-contrib",
    "cadvisor/cadvisor": "google/cadvisor",
    "traefik": "traefik/traefik",
}

_BRIEF_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_BRIEF_TTL_SECONDS = 600.0


def _http_get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 8) -> Any | None:
    import json as _json
    import urllib.request

    if not url.startswith(("https://", "http://")):
        return None
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "docker-mcp/1.0"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return _json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _http_get_text(url: str, headers: dict[str, str] | None = None, timeout: int = 10) -> str | None:
    import urllib.request

    if not url.startswith(("https://", "http://")):
        return None
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "docker-mcp/1.0"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _github_candidates(prov: dict[str, Any]) -> list[str]:
    kind = prov.get("kind")
    namespace = (prov.get("namespace") or "").strip()
    repo = (prov.get("repo") or "").strip()
    if not repo:
        return []
    key = f"{namespace}/{repo}" if namespace else repo
    if key in GITHUB_OVERRIDES:
        return [GITHUB_OVERRIDES[key]]
    if kind == "ghcr" and namespace:
        return [f"{namespace}/{repo}"]
    if kind == "lscr":
        return [f"linuxserver/docker-{repo}", f"linuxserver/{repo}"]
    if kind == "dockerhub-user" and namespace:
        return [f"{namespace}/{repo}"]
    if kind == "dockerhub-official":
        return [GITHUB_OVERRIDES.get(repo, f"docker-library/{repo}")]
    return []


def _readme_excerpt(markdown: str, limit: int = 1100) -> str:
    """First substantive README lines: skip badges, comments, TOC, empty markup."""
    import re

    lines: list[str] = []
    for raw in (markdown or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<!--"):
            continue
        if re.match(r"^!\[.*?\]\(.*?\)\s*$", line):
            continue  # badge image alone on a line
        if re.match(r"^(\[.+?\]\(.+?\)\s*)+$", line) and len(line) < 200:
            continue  # badge/link soup line
        if re.match(r"^#{1,6}\s*(table of contents|toc|contents)\s*$", line, re.IGNORECASE):
            continue
        # strip inline badge images, keep the rest of the line
        line = re.sub(r"!\[.*?\]\(.*?\)", "", line).strip()
        line = re.sub(r"^#{1,6}\s*", "", line).strip()
        if len(line) < 12:
            continue
        lines.append(line)
        if sum(len(part) for part in lines) >= limit:
            break
    text = "\n".join(lines[:14])
    return text[:limit].rstrip() + ("…" if len(text) > limit else "")


def image_brief_sync(ref: str) -> dict[str, Any]:
    """Plain-language brief for an image: upstream description + README excerpt.

    Docker Hub API for hub images, GitHub API (repo meta + README) otherwise.
    Results are cached in-memory for 10 minutes (unauthenticated GitHub
    rate limit is 60 req/hour).
    """
    import time as _time

    ref = (ref or "").strip()
    if not ref:
        raise ValueError("ref is required")
    now = _time.time()
    cached = _BRIEF_CACHE.get(ref)
    if cached and now - cached[0] < _BRIEF_TTL_SECONDS:
        payload = dict(cached[1])
        payload["cached"] = True
        return payload

    prov = image_provenance(ref)
    kind = prov.get("kind")
    namespace = prov.get("namespace")
    repo = prov.get("repo")
    brief: dict[str, Any] = {
        "status": "success",
        "ref": ref,
        "kind": kind,
        "fleet_repo": prov.get("fleet_repo"),
        "hub_url": prov.get("hub_url"),
        "github_url": prov.get("github_url"),
        "github_repo": None,
        "stars": None,
        "license": None,
        "topics": [],
        "about": None,
        "readme_excerpt": None,
        "cached": False,
        "error": None,
    }

    if kind == "local":
        local_repo = prov.get("fleet_repo")
        suffix = " from fleet repo " + local_repo if local_repo else ""
        brief["about"] = (
            "Locally built image" + suffix + " - "
            "no upstream registry entry. Inspect config, env and layer history below for what it does."
        )
        _BRIEF_CACHE[ref] = (now, dict(brief))
        return brief

    # Docker Hub description for hub images.
    if kind in ("dockerhub-official", "dockerhub-user") and repo:
        hub_path = f"_/{repo}" if kind == "dockerhub-official" else f"{namespace}/{repo}"
        hub = _http_get_json(f"https://hub.docker.com/v2/repositories/{hub_path}/")
        if isinstance(hub, dict):
            brief["about"] = (hub.get("description") or "").strip() or None
            brief["hub_url"] = brief["hub_url"] or f"https://hub.docker.com/r/{hub_path}"

    # GitHub repo meta + README.
    for candidate in _github_candidates(prov):
        meta = _http_get_json(f"https://api.github.com/repos/{candidate}")
        if not isinstance(meta, dict) or meta.get("message") == "Not Found":
            continue
        brief["github_repo"] = candidate
        brief["github_url"] = f"https://github.com/{candidate}"
        brief["stars"] = meta.get("stargazers_count")
        license_info = meta.get("license") or {}
        brief["license"] = license_info.get("spdx_id") or license_info.get("name")
        brief["topics"] = list(meta.get("topics") or [])
        if not brief["about"]:
            brief["about"] = (meta.get("description") or "").strip() or None
        readme = _http_get_text(
            f"https://api.github.com/repos/{candidate}/readme",
            headers={
                "User-Agent": "docker-mcp/1.0",
                "Accept": "application/vnd.github.raw",
            },
        )
        if readme:
            brief["readme_excerpt"] = _readme_excerpt(readme) or None
        break

    if not brief["about"] and not brief["readme_excerpt"]:
        brief["error"] = "upstream lookup failed (offline or rate-limited) — config below still applies"
    _BRIEF_CACHE[ref] = (now, dict(brief))
    return brief


def junk_summary_sync() -> dict[str, Any]:
    """Aggregate cleanup candidates: unused/dangling/large/old images, stopped
    containers, unused volumes, and unused custom networks."""
    """Aggregate cleanup candidates: unused/dangling/large/old images, stopped
    containers, unused volumes, and unused custom networks."""
    images_data = list_images_sync()
    containers_data = list_containers_sync(all_states=True)
    volumes_data = list_volumes_sync()
    networks_data = list_networks_sync()
    now = datetime.now(tz=UTC)

    images = images_data.get("images") or []
    dangling = [_image_item_summary(i, now, "dangling (untagged layers)") for i in images if i.get("dangling")]
    unused = [
        _image_item_summary(i, now, "not used by any container")
        for i in images
        if not i.get("dangling") and not (i.get("used_by") or [])
    ]
    large = [
        _image_item_summary(i, now, f"{round((i.get('size') or 0) / 1e9, 1)} GB on disk")
        for i in images
        if (i.get("size") or 0) >= LARGE_IMAGE_BYTES
    ]
    old: list[dict[str, Any]] = []
    for img in images:
        age = _age_days(img.get("created"), now)
        if age is not None and age >= OLD_IMAGE_DAYS:
            item = _image_item_summary(img, now, f"image is {age} days old (update candidate)")
            item["age_days"] = age
            old.append(item)

    containers = containers_data.get("containers") or []
    stopped = [
        {
            "name": c.get("name"),
            "id": c.get("id"),
            "image": c.get("image"),
            "state": c.get("state"),
            "status": c.get("status"),
            "reason": "container is not running",
        }
        for c in containers
        if (c.get("state") or "") != "running"
    ]

    volumes = volumes_data.get("volumes") or []
    # NOTE: volume list UsageData is empty on this daemon; docker system df
    # carries the real RefCount/Size per volume, so use it as ground truth.
    df_vol_usage: dict[str, dict[str, Any]] = {}
    try:
        df_info = require_client().df()
        for item in df_info.get("Volumes") or []:
            if isinstance(item, dict) and item.get("Name"):
                df_vol_usage[str(item["Name"])] = item.get("UsageData") or {}
    except Exception:
        df_vol_usage = {}
    by_name = {str(v.get("name")): v for v in volumes if v.get("name")}
    unused_volumes = []
    unknown_volumes = []
    for name, vol in by_name.items():
        usage = df_vol_usage.get(name)
        if usage is None:
            unknown_volumes.append(
                {"name": name, "driver": vol.get("driver"), "reason": "daemon reported no usage data"}
            )
            continue
        ref_count = usage.get("RefCount")
        size = usage.get("Size")
        if ref_count is not None and ref_count == 0:
            unused_volumes.append(
                {
                    "name": name,
                    "driver": vol.get("driver"),
                    "size": size,
                    "created": vol.get("created"),
                    "age_days": _age_days(vol.get("created"), now),
                    "reason": "no container references this volume",
                }
            )
    unused_volumes.sort(key=lambda v: v.get("size") or 0, reverse=True)

    networks = networks_data.get("networks") or []
    unused_networks = [
        {
            "name": n.get("name"),
            "id": n.get("id"),
            "driver": n.get("driver"),
            "subnet": n.get("subnet"),
            "reason": "no containers attached",
        }
        for n in networks
        if (n.get("container_count") or 0) == 0 and (n.get("name") or "") not in DEFAULT_NETWORKS
    ]

    reclaimable = sum(i["size"] for i in dangling) + sum(i["size"] for i in unused)
    reclaimable += sum((v.get("size") or 0) for v in unused_volumes if isinstance(v.get("size"), (int, float)))

    # Daemon-estimated reclaimable (accounts for shared layers; the gross sum
    # above does not). Slow path, best effort.
    daemon_reclaimable = None
    try:
        disk = disk_usage_sync().get("disk_usage", {}).get("summary", {})
        daemon_reclaimable = {
            "images": disk.get("total_images_size", 0),
            "volumes": disk.get("total_volumes_size", 0),
            "containers": disk.get("total_containers_size", 0),
            "build_cache": disk.get("total_build_cache_size", 0),
            "total": disk.get("total_size", 0),
        }
    except Exception:
        daemon_reclaimable = None

    return {
        "status": "success",
        "summary": {
            "image_count": len(images),
            "container_count": len(containers),
            "volume_count": len(volumes),
            "network_count": len(networks),
            "dangling_images": len(dangling),
            "unused_images": len(unused),
            "large_images": len(large),
            "old_images": len(old),
            "stopped_containers": len(stopped),
            "unused_volumes": len(unused_volumes),
            "unknown_volumes": len(unknown_volumes),
            "unused_networks": len(unused_networks),
            "reclaimable_bytes": reclaimable,
            "daemon_disk": daemon_reclaimable,
        },
        "groups": {
            "dangling_images": sorted(dangling, key=lambda i: i["size"], reverse=True),
            "unused_images": sorted(unused, key=lambda i: i["size"], reverse=True),
            "large_images": sorted(large, key=lambda i: i["size"], reverse=True),
            "old_images": sorted(old, key=lambda i: i["age_days"] or 0, reverse=True),
            "stopped_containers": stopped,
            "unused_volumes": unused_volumes,
            "unknown_volumes": unknown_volumes,
            "unused_networks": unused_networks,
        },
    }
