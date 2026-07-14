"""Docker Compose CRUD operations via `docker compose` CLI — portmanteau tool."""

from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Annotated, Any, Literal

from dockermcp.docker_context import docker_available, docker_error
from dockermcp.mcp_instance import get_mcp


async def _run_compose(
    args: list[str],
    cwd: str | None = None,
) -> dict[str, Any]:
    """Run `docker compose` with args, return parsed output."""
    if not docker_available:
        return {"success": False, "error": f"Docker not available: {docker_error}"}
    cmd = ["docker", "compose"] + args
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            return {"success": False, "error": err or f"exit code {proc.returncode}"}
        return {"success": True, "output": out}
    except TimeoutError:
        return {"success": False, "error": "Command timed out after 60s"}
    except FileNotFoundError:
        return {"success": False, "error": "docker not found on PATH"}


def _parse_projects(stdout: str) -> list[dict[str, Any]]:
    """Parse `docker compose ls --format json` output."""
    projects = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            projects.append(data)
        except json.JSONDecodeError:
            pass
    return projects


async def _compose_list(all: bool = False) -> dict[str, Any]:
    """List all Docker Compose projects (running or all).

    Args:
        all: Include stopped projects (default false).

    Returns:
        {"success": bool, "projects": [{name, status, config_files}], "total": int}
    """
    args = ["ls", "--format", "json"]
    if all:
        args.append("--all")
    result = await _run_compose(args)
    if not result["success"]:
        return result
    projects = _parse_projects(result["output"])
    return {"success": True, "projects": projects, "total": len(projects)}


async def _compose_ps(project: str | None = None) -> dict[str, Any]:
    """List containers for a Compose project.

    Args:
        project: Compose project name. Omit to list all.

    Returns:
        {"success": bool, "containers": [{name, status, service, project}]}
    """
    args = ["ps", "--format", "json"]
    if project:
        args.extend(["-p", project])
    result = await _run_compose(args)
    if not result["success"]:
        return result
    containers = []
    for line in result["output"].strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            containers.append(data)
        except json.JSONDecodeError:
            pass
    return {"success": True, "containers": containers, "total": len(containers)}


async def _compose_up(
    project: str,
    services: list[str] | None = None,
    detach: bool = True,
    build: bool = False,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """Start Compose services.

    Args:
        project: Compose project name.
        services: Specific services to start (optional).
        detach: Run in background (default true).
        build: Rebuild images before starting (default false).
        project_dir: Working directory with compose file (optional).

    Returns:
        {"success": bool, "output": str}
    """
    args = ["-p", project, "up"]
    if detach:
        args.append("-d")
    if build:
        args.append("--build")
    if services:
        args.extend(services)
    # Suppress noisy docker compose up output — only return on error
    result = await _run_compose(args, cwd=project_dir)
    if not result["success"]:
        return result
    return {"success": True, "message": f"Compose project '{project}' started", "project": project}


async def _compose_down(
    project: str,
    volumes: bool = False,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """Stop and remove Compose services.

    Args:
        project: Compose project name.
        volumes: Remove named volumes (default false).
        project_dir: Working directory (optional).

    Returns:
        {"success": bool, "output": str}
    """
    args = ["-p", project, "down"]
    if volumes:
        args.append("-v")
    result = await _run_compose(args, cwd=project_dir)
    if not result["success"]:
        return result
    return {"success": True, "message": f"Compose project '{project}' stopped", "project": project}


async def _compose_logs(
    project: str,
    service: str | None = None,
    tail: int = 100,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """Fetch logs for a Compose project or service.

    Args:
        project: Compose project name.
        service: Specific service name (optional).
        tail: Number of lines per service (default 100).
        project_dir: Working directory (optional).

    Returns:
        {"success": bool, "logs": str}
    """
    args = ["-p", project, "logs", "--no-color", f"--tail={tail}"]
    if service:
        args.append(service)
    result = await _run_compose(args, cwd=project_dir)
    return result


async def _compose_build(
    project: str,
    service: str | None = None,
    no_cache: bool = False,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """Rebuild Compose service images.

    Args:
        project: Compose project name.
        service: Specific service to rebuild (optional, rebuilds all if omitted).
        no_cache: Disable build cache (default false).
        project_dir: Working directory (optional).

    Returns:
        {"success": bool, "output": str}
    """
    args = ["-p", project, "build"]
    if no_cache:
        args.append("--no-cache")
    if service:
        args.append(service)
    result = await _run_compose(args, cwd=project_dir)
    if not result["success"]:
        return result
    return {"success": True, "message": f"Compose build complete for '{project}'", "project": project}


async def _compose_config(
    project: str,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """Validate and render Compose configuration.

    Args:
        project: Compose project name.
        project_dir: Working directory (optional).

    Returns:
        {"success": bool, "config": str} — rendered YAML
    """
    args = ["-p", project, "config"]
    result = await _run_compose(args, cwd=project_dir)
    if not result["success"]:
        return result
    return {"success": True, "config": result["output"], "project": project}


async def _compose_debug(
    project: str,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """Debug a Compose project: show container states, exit codes, port conflicts.

    Args:
        project: Compose project name.

    Returns:
        {"success": bool, "project": str, "services": [...], "issues": [...]}
    """
    # Get ps output in verbose format
    ps_result = await compose_ps(project)
    if not ps_result["success"]:
        return ps_result

    containers = ps_result.get("containers", [])
    issues = []
    services = []

    for c in containers:
        svc = {
            "name": c.get("Name", ""),
            "service": c.get("Service", ""),
            "status": c.get("Status", ""),
            "state": c.get("State", ""),
            "ports": c.get("Ports", ""),
            "exit_code": None,
        }
        # Detect common issues
        status = (c.get("Status") or "").lower()
        state = (c.get("State") or "").lower()
        if state == "exited":
            issues.append(f"Container '{c.get('Name')}' is exited (may need restart)")
        if "unhealthy" in status:
            issues.append(f"Container '{c.get('Name')}' health check failed")
        if "(0)" in (c.get("Ports") or ""):
            issues.append(f"Port conflict on '{c.get('Name')}'")
        services.append(svc)

    # Check project logs for ERROR
    log_result = await compose_logs(project, tail=20)
    if log_result.get("output"):
        for line in log_result["output"].split("\n"):
            if "error" in line.lower() or "fatal" in line.lower() or "traceback" in line.lower():
                issues.append(f"Log error: {line.strip()[:200]}")
                break

    return {
        "success": True,
        "project": project,
        "services": services,
        "issues": issues,
        "issue_count": len(issues),
    }


def register_tools(mcp=None) -> None:
    """Register compose portmanteau tool."""
    if mcp is None:
        mcp = get_mcp()

    @mcp.tool()
    async def compose_operations(
        operation: Annotated[
            Literal["list", "ps", "up", "down", "logs", "build", "config", "debug"], "Operation to perform."
        ],
        project: Annotated[str | None, "Compose project name (required for up/down/logs/build/config/debug)."] = None,
        services: Annotated[str | None, "Comma-separated service names for up/build/logs."] = None,
        detach: Annotated[bool, "Run in background (up only)."] = True,
        build: Annotated[bool, "Rebuild images before starting (up only)."] = False,
        no_cache: Annotated[bool, "Disable build cache (build only)."] = False,
        volumes: Annotated[bool, "Remove named volumes (down only)."] = False,
        tail: Annotated[int, "Log lines per service (logs only)."] = 100,
        all_projects: Annotated[bool, "Include stopped projects (list only)."] = False,
        project_dir: Annotated[str | None, "Working directory with compose file."] = None,
    ) -> dict[str, Any]:
        """Docker Compose CRUD and debug operations.

        ## Return Format
        {"success": bool, ...} — varies by operation

        ## Examples
        compose_operations(operation="list", all_projects=True)
        compose_operations(operation="up", project="myapp", build=True)
        compose_operations(operation="logs", project="myapp", service="web", tail=50)
        compose_operations(operation="debug", project="myapp")
        """
        svc_list = services.split(",") if services else None
        if operation == "list":
            return await _compose_list(all=all_projects)
        elif operation == "ps":
            return await _compose_ps(project=project)
        elif operation == "up":
            return await _compose_up(
                project=project, services=svc_list, detach=detach, build=build, project_dir=project_dir
            )
        elif operation == "down":
            return await _compose_down(project=project, volumes=volumes, project_dir=project_dir)
        elif operation == "logs":
            return await _compose_logs(project=project, tail=tail, project_dir=project_dir)
        elif operation == "build":
            return await _compose_build(project=project, no_cache=no_cache, project_dir=project_dir)
        elif operation == "config":
            return await _compose_config(project=project, project_dir=project_dir)
        elif operation == "debug":
            return await _compose_debug(project=project, project_dir=project_dir)
        return {"success": False, "error": f"Unknown operation: {operation}"}
