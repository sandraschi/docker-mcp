"""Compose file analysis — parse, validate, and summarize docker-compose YAML."""

from __future__ import annotations

import os
from typing import Any


def analyze_compose_file(file_path: str) -> dict[str, Any]:
    """Parse a docker-compose YAML and return structured analysis."""
    if not os.path.isfile(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        import yaml
    except ImportError:
        return {"success": False, "error": "PyYAML not installed. Run: uv add pyyaml"}

    try:
        with open(file_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return {"success": False, "error": f"YAML parse error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Read error: {e}"}

    if not isinstance(config, dict):
        return {"success": False, "error": "Compose file is empty or not a mapping"}

    version = str(config.get("version", ""))
    services_raw = config.get("services", {}) or {}
    volumes_raw = config.get("volumes", {}) or {}
    networks_raw = config.get("networks", {}) or {}

    services = []
    for name, svc in services_raw.items():
        if not isinstance(svc, dict):
            continue
        image = svc.get("image", "")
        build = svc.get("build", "")
        ports_raw = svc.get("ports", []) or []
        ports = []
        for p in ports_raw:
            if isinstance(p, str):
                parts = p.split(":")
                if len(parts) == 2:
                    ports.append({"host": parts[0], "container": parts[1]})
                elif len(parts) == 1:
                    ports.append({"container": parts[0]})
            elif isinstance(p, dict):
                ports.append({"host": str(p.get("published", "")), "container": str(p.get("target", ""))})
        volumes = []
        for v in svc.get("volumes") or []:
            if isinstance(v, str):
                volumes.append(v.split(":")[0])
            elif isinstance(v, dict):
                volumes.append(v.get("source", ""))
        depends_on = svc.get("depends_on", [])
        if isinstance(depends_on, dict):
            depends_on = list(depends_on.keys())
        env_vars = svc.get("environment", {}) or {}
        if isinstance(env_vars, list):
            env_vars = {e.split("=", 1)[0]: e.split("=", 1)[1] if "=" in e else "" for e in env_vars}

        services.append(
            {
                "name": name,
                "image": image,
                "build": build
                if isinstance(build, str)
                else (build.get("context", "") if isinstance(build, dict) else ""),
                "ports": ports,
                "volumes": volumes,
                "depends_on": depends_on,
                "environment_keys": list(env_vars.keys()),
                "restart": svc.get("restart", ""),
                "healthcheck": svc.get("healthcheck") is not None,
                "container_name": svc.get("container_name", ""),
            }
        )

    volumes_config = [
        {"name": k, "driver": (v.get("driver", "local") if isinstance(v, dict) else "local")}
        for k, v in volumes_raw.items()
    ]
    networks_config = [
        {"name": k, "driver": (v.get("driver", "bridge") if isinstance(v, dict) else "bridge")}
        for k, v in networks_raw.items()
    ]

    all_ports = []
    for svc in services:
        for p in svc["ports"]:
            all_ports.append(f"{svc['name']}: {p.get('host', '?')}->{p.get('container', '?')}")
    all_images = [s["image"] for s in services if s["image"]]
    used_volumes = set()
    for s in services:
        for v in s["volumes"]:
            used_volumes.add(v)

    return {
        "success": True,
        "file_path": file_path,
        "file_size": os.path.getsize(file_path),
        "compose_version": version,
        "service_count": len(services),
        "volume_count": len(volumes_config),
        "network_count": len(networks_config),
        "services": services,
        "volumes": volumes_config,
        "networks": networks_config,
        "all_images": all_images,
        "all_ports": all_ports,
        "has_build_contexts": any(s["build"] for s in services),
        "has_healthchecks": any(s["healthcheck"] for s in services),
        "has_depends_on": any(s["depends_on"] for s in services),
        "unreferenced_volumes": [v["name"] for v in volumes_config if v["name"] not in used_volumes],
    }
