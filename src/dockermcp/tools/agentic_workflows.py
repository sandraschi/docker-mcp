"""Agentic Docker workflows — compose deploy, cleanup, diagnose, and rollback."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from dockermcp.docker_context import docker_client
from dockermcp.mcp_instance import mcp
from dockermcp.tools.compose.compose_management import _compose_down, _compose_logs, _compose_ps, _compose_up


def _health_check(containers: list[dict[str, Any]]) -> dict[str, Any]:
    healthy = []
    unhealthy = []
    for c in containers:
        status = (c.get("Status") or "").lower()
        state = (c.get("State") or "").lower()
        name = c.get("Name") or c.get("name") or "?"
        if state == "running" and "unhealthy" not in status:
            healthy.append(name)
        else:
            unhealthy.append({"name": name, "reason": f"state={state}" if state != "running" else "health check failing"})
    return {"healthy": healthy, "unhealthy": unhealthy, "total": len(containers), "healthy_count": len(healthy)}


@mcp.tool()
async def agentic_workflow(
    operation: Annotated[str, "Workflow: deploy_compose, cleanup, diagnose, rollback."],
    project: Annotated[str | None, "Compose project name (required for deploy/rollback/diagnose)."] = None,
    build: Annotated[bool, "Rebuild images before deploy."] = False,
    resource_type: Annotated[str, "Resource type for cleanup: images, volumes, networks, all."] = "all",
) -> dict[str, Any]:
    """Multi-step Docker agentic workflows.

    ## Operations
    - **deploy_compose**: Start a compose project, wait, health-check, suggest rollback on failure.
    - **cleanup**: Prune unused Docker resources in dependency order (images, volumes, networks).
    - **diagnose**: Collect container states, logs, and system resources for a compose project.
    - **rollback**: Stop a compose project and remove its volumes.

    ## Return Format
    {"success": bool, "operation": str, "summary": str, "steps": [...], "data": {...}}

    ## Examples
    agentic_workflow(operation="deploy_compose", project="myapp", build=True)
    agentic_workflow(operation="cleanup", resource_type="all")
    agentic_workflow(operation="diagnose", project="myapp")
    agentic_workflow(operation="rollback", project="myapp")
    """
    steps = []

    if operation == "deploy_compose":
        if not project:
            return {"success": False, "operation": operation, "summary": "Missing project name", "steps": [], "data": {}}
        steps.append({"name": "deploy", "status": "running", "detail": ""})
        deploy_result = await _compose_up(project=project, build=build)
        steps[-1] = {"name": "deploy", "status": "ok" if deploy_result.get("success") else "fail", "detail": deploy_result.get("message", deploy_result.get("error", ""))}
        if not deploy_result.get("success"):
            return {"success": False, "operation": operation, "summary": f"Deploy failed: {deploy_result.get('error')}", "steps": steps, "data": {}}
        steps.append({"name": "health_check", "status": "pending", "detail": ""})
        await asyncio.sleep(3)
        containers = await _compose_ps(project)
        health = _health_check(containers)
        steps[-1] = {"name": "health_check", "status": "ok" if health["healthy_count"] == health["total"] else "degraded", "detail": f"{health['healthy_count']}/{health['total']} healthy"}
        suggestion = ""
        if health["unhealthy"]:
            suggestion = f"Rollback recommended: {len(health['unhealthy'])} unhealthy services"
        return {
            "success": health["healthy_count"] > 0,
            "operation": operation,
            "summary": f"Deployed {project}: {health['healthy_count']}/{health['total']} services healthy",
            "steps": steps,
            "data": {"project": project, "health": health, "suggestion": suggestion},
        }

    elif operation == "cleanup":
        results = {}
        if resource_type in ("images", "all"):
            steps.append({"name": "prune_images", "status": "running", "detail": ""})
            try:
                client = docker_client
                img_result = client.images.prune(filters={"dangling": True})
                reclaimed = img_result.get("SpaceReclaimed", 0)
                count = len(img_result.get("ImagesDeleted", []))
                steps[-1] = {"name": "prune_images", "status": "ok", "detail": f"Removed {count} images ({reclaimed / 1024 / 1024:.1f} MB)"}
                results["images"] = {"count": count, "reclaimed_bytes": reclaimed}
            except Exception as e:
                steps[-1] = {"name": "prune_images", "status": "fail", "detail": str(e)}
        if resource_type in ("volumes", "all"):
            steps.append({"name": "prune_volumes", "status": "running", "detail": ""})
            try:
                client = docker_client
                vol_result = client.volumes.prune()
                count = len(vol_result.get("VolumesDeleted", []))
                steps[-1] = {"name": "prune_volumes", "status": "ok", "detail": f"Removed {count} volumes"}
                results["volumes"] = {"count": count}
            except Exception as e:
                steps[-1] = {"name": "prune_volumes", "status": "fail", "detail": str(e)}
        if resource_type in ("networks", "all"):
            steps.append({"name": "prune_networks", "status": "running", "detail": ""})
            try:
                client = docker_client
                net_result = client.networks.prune()
                count = len(net_result.get("NetworksDeleted", []))
                steps[-1] = {"name": "prune_networks", "status": "ok", "detail": f"Removed {count} networks"}
                results["networks"] = {"count": count}
            except Exception as e:
                steps[-1] = {"name": "prune_networks", "status": "fail", "detail": str(e)}
        return {"success": True, "operation": operation, "summary": "Cleanup completed", "steps": steps, "data": results}

    elif operation == "diagnose":
        if not project:
            return {"success": False, "operation": operation, "summary": "Missing project name", "steps": [], "data": {}}
        steps.append({"name": "list_containers", "status": "running", "detail": ""})
        containers = await _compose_ps(project)
        steps[-1] = {"name": "list_containers", "status": "ok", "detail": f"Found {len(containers)} containers"}
        steps.append({"name": "health_check", "status": "running", "detail": ""})
        health = _health_check(containers)
        steps[-1] = {"name": "health_check", "status": "ok", "detail": f"{health['healthy_count']}/{health['total']} healthy"}
        steps.append({"name": "logs", "status": "running", "detail": ""})
        logs = await _compose_logs(project, tail=30)
        steps[-1] = {"name": "logs", "status": "ok", "detail": f"Collected {len(logs)} chars of logs"}
        steps.append({"name": "system_resources", "status": "running", "detail": ""})
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            steps[-1] = {"name": "system_resources", "status": "ok", "detail": f"CPU {cpu}%, Mem {mem}%, Disk {disk}%"}
        except ImportError:
            steps[-1] = {"name": "system_resources", "status": "skip", "detail": "psutil not installed"}
        issues = [f"{u['name']}: {u.get('reason', 'unknown')}" for u in health.get("unhealthy", [])]
        if not issues:
            issues.append("No health issues found")
        suggestions = []
        if health["healthy_count"] < health["total"]:
            suggestions.append("Restart unhealthy services with `docker compose restart`")
            suggestions.append("Check container logs for ERROR/FATAL patterns")
        return {
            "success": True,
            "operation": operation,
            "summary": f"Diagnosis for {project}: {len(issues)} issue(s)",
            "steps": steps,
            "data": {"project": project, "health": health, "issues": issues, "logs_preview": logs[:2000], "suggestions": suggestions},
        }

    elif operation == "rollback":
        if not project:
            return {"success": False, "operation": operation, "summary": "Missing project name", "steps": [], "data": {}}
        steps.append({"name": "down", "status": "running", "detail": ""})
        result = await _compose_down(project=project, volumes=True)
        steps[-1] = {"name": "down", "status": "ok" if result.get("success") else "fail", "detail": result.get("message", result.get("error", ""))}
        return {
            "success": result.get("success", False),
            "operation": operation,
            "summary": f"Rolled back {project} (stopped + removed volumes)",
            "steps": steps,
            "data": {"project": project},
        }

    return {"success": False, "operation": operation, "summary": f"Unknown operation: {operation}", "steps": steps, "data": {}}
