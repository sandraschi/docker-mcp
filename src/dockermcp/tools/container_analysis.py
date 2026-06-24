"""Container resource analysis — trends, restart counts, log patterns, recommendations."""

from __future__ import annotations

from typing import Annotated, Any

from dockermcp.docker_context import docker_client
from dockermcp.mcp_instance import mcp


@mcp.tool()
async def container_analyze(
    container_id: Annotated[str, "Container ID or name to analyze."],
    log_tail: Annotated[int, "Lines of recent logs to scan for error patterns."] = 100,
) -> dict[str, Any]:
    """Analyze a container's health, resource trends, and recommend actions.

    Inspects restart count, exit codes, recent log patterns, resource limits,
    mount status, and network configuration. Returns actionable recommendations.

    ## Return Format
    {"success": bool, "container": str, "analysis": {...}, "recommendations": [str]}

    ## Examples
    container_analyze(container_id="my-app-1")
    container_analyze(container_id="abc123def", log_tail=200)
    """
    try:
        client = docker_client
        container = client.containers.get(container_id)
        attrs = container.attrs
        cfg = attrs.get("Config", {}) or attrs.get("config", {})
        state = attrs.get("State", {}) or attrs.get("state", {})

        restart_count = attrs.get("RestartCount", 0)
        exit_code = state.get("ExitCode")
        status = state.get("Status", "unknown")
        started_at = state.get("StartedAt", "")
        finished_at = state.get("FinishedAt", "")

        log_errors = []
        try:
            logs = container.logs(tail=log_tail, timestamps=True).decode("utf-8", errors="replace")
            error_lines = [l for l in logs.split("\n") if any(w in l.lower() for w in ["error", "fatal", "traceback", "exception", "panic", "killed", "oom"])]
            log_errors = error_lines[:10]
        except Exception:
            logs = ""
            log_errors = ["(unable to fetch logs)"]

        mounts = attrs.get("Mounts", [])
        ports = cfg.get("ExposedPorts", {}) or {}
        host_config = attrs.get("HostConfig", {}) or {}
        mem_limit = host_config.get("Memory", 0)
        cpu_shares = host_config.get("CpuShares", 0)
        restart_policy = host_config.get("RestartPolicy", {}).get("Name", "none")

        recommendations = []

        if restart_count > 3:
            recommendations.append(f"Container restarted {restart_count} times. Check for crash loops. ")
        if exit_code is not None and exit_code != 0 and status == "exited":
            recommendations.append(f"Container exited with code {exit_code}. Common causes: missing config, port conflict, dependency failure.")
        if mem_limit == 0:
            recommendations.append("No memory limit set. Set --memory to prevent OOM kills.")
        if restart_policy == "no":
            recommendations.append("Restart policy is 'no'. Use --restart unless-stopped for production.")
        if log_errors:
            recommendations.append(f"Found {len(log_errors)} ERROR/FATAL log lines. Review container logs.")
        if not ports:
            recommendations.append("No ports exposed. Verify network configuration.")
        if not mounts:
            recommendations.append("No volumes mounted. Data may be lost on container removal.")

        if not recommendations:
            recommendations.append("No critical issues detected.")

        return {
            "success": True,
            "container": container_id,
            "analysis": {
                "status": status,
                "restart_count": restart_count,
                "exit_code": exit_code,
                "started_at": started_at,
                "finished_at": finished_at,
                "memory_limit_bytes": mem_limit,
                "cpu_shares": cpu_shares,
                "restart_policy": restart_policy,
                "port_count": len(ports),
                "volume_count": len(mounts),
                "log_error_lines": log_errors[:5],
            },
            "recommendations": recommendations,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
