"""
Docker Desktop Status Tool - Comprehensive health check with hang detection.

Provides daemon responsiveness check, image/container listings, resource monitoring,
and automatic recovery from hanging daemon.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from dockermcp.mcp_instance import mcp


@mcp.tool()
async def docker_desktop_status(autofix: bool = False) -> dict[str, Any]:
    """
    Check Docker Desktop daemon health with hang detection and auto-recovery.

    Comprehensive status check including:
    - Daemon responsiveness (with timeout detection for hangs)
    - Last 10 built images (name, size, creation date)
    - Last 10 containers (name, status, ports, creation date)
    - Running vs stopped container count
    - Disk usage breakdown (images, containers, volumes)
    - System resource configuration (memory, CPU allocation)
    - Warnings for undersized allocations (AI workloads)

    Args:
        autofix: If True, automatically attempt recovery if daemon is hanging

    Returns:
        Dictionary with status report and detected issues
    """

    result = {
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "issues": [],
        "recommendations": [],
        "daemon_healthy": False,
        "daemon_hanging": False,
    }

    # 1. Check if Docker is installed
    docker_path = Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")
    if not docker_path.exists():
        return {
            "status": "error",
            "message": "Docker Desktop not installed",
            "install_url": "https://hub.docker.com/"
        }

    result["checks"]["docker_installed"] = True

    # 2. Check daemon responsiveness with timeout (hang detection)
    result["checks"]["daemon_responsiveness"] = await _check_daemon_health(
        autofix=autofix, result=result
    )

    if result["daemon_healthy"]:
        # 3. Get Docker version
        result["checks"]["docker_version"] = await _get_docker_version()

        # 4. Get last 10 images
        result["checks"]["recent_images"] = await _get_recent_images(limit=10)

        # 5. Get last 10 containers
        result["checks"]["recent_containers"] = await _get_recent_containers(limit=10)

        # 6. Get container summary
        result["checks"]["container_summary"] = await _get_container_summary()

        # 7. Get disk usage
        result["checks"]["disk_usage"] = await _get_disk_usage()

        # 8. Get resource stats (if containers running)
        result["checks"]["resource_stats"] = await _get_resource_stats()
    else:
        result["issues"].append("Docker daemon not healthy - skipping detailed checks")

    # 9. Get Docker Desktop configuration
    result["checks"]["docker_config"] = await _get_docker_config()

    # Add recommendations based on findings
    _add_recommendations(result)

    # Format output
    output = _format_status_report(result)

    return {
        "status": "success" if result["daemon_healthy"] else "error",
        "message": output,
        "data": result
    }


async def _check_daemon_health(autofix: bool, result: dict) -> dict:
    """Check daemon responsiveness with timeout detection for hangs."""
    check_result = {"status": "unknown", "recovered": False}

    try:
        # Test with 5-second timeout
        process = await asyncio.create_subprocess_exec(
            "docker", "version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=5.0
            )

            if process.returncode == 0:
                result["daemon_healthy"] = True
                check_result["status"] = "responsive"
            else:
                result["daemon_hanging"] = True
                check_result["status"] = "hanging"
                result["issues"].append("Daemon hanging - not responding to commands")

                if autofix:
                    check_result["recovery_attempted"] = True
                    recovered = await _attempt_daemon_recovery()
                    if recovered:
                        result["daemon_healthy"] = True
                        result["daemon_hanging"] = False
                        check_result["recovered"] = True
                        check_result["status"] = "recovered"
                        result["issues"].remove("Daemon hanging - not responding to commands")
                    else:
                        result["issues"].append(
                            "Daemon recovery failed - manual intervention needed"
                        )
                        result["recommendations"].append(
                            "Run: .\\update-docker-desktop.ps1 -FullWipe"
                        )

        except TimeoutError:
            # Command timed out = daemon is hanging
            result["daemon_hanging"] = True
            check_result["status"] = "hanging_timeout"
            result["issues"].append("Daemon hanging (timeout after 5s)")

            if autofix:
                check_result["recovery_attempted"] = True
                recovered = await _attempt_daemon_recovery()
                if recovered:
                    result["daemon_healthy"] = True
                    result["daemon_hanging"] = False
                    check_result["recovered"] = True
                    check_result["status"] = "recovered"
                else:
                    result["issues"].append("Daemon recovery failed after restart")
                    result["recommendations"].append(
                        "Use: docker_desktop_update with full_wipe=True"
                    )
            else:
                result["recommendations"].append(
                    "Use: docker_daemon_recover to auto-fix hanging daemon"
                )

            process.kill()

    except Exception as e:
        result["issues"].append(f"Error checking daemon: {str(e)}")
        check_result["status"] = "error"
        check_result["error"] = str(e)

    return check_result


async def _attempt_daemon_recovery() -> bool:
    """Kill hung processes and restart Docker Desktop."""
    try:
        # Kill hung processes
        for proc_name in [
            "Docker Desktop.exe",
            "com.docker.backend.exe",
            "vpnkit.exe",
        ]:
            try:
                await asyncio.create_subprocess_exec(
                    "taskkill", "/IM", proc_name, "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except Exception:
                pass  # Process might not be running

        await asyncio.sleep(3)

        # Restart Docker Desktop
        docker_path = Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")
        if docker_path.exists():
            await asyncio.create_subprocess_exec(
                str(docker_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            # Wait for daemon to be responsive
            await asyncio.sleep(8)

            # Verify responsiveness
            for _attempt in range(5):
                try:
                    process = await asyncio.create_subprocess_exec(
                        "docker", "version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(), timeout=5.0
                        )
                        if process.returncode == 0:
                            return True
                    except TimeoutError:
                        process.kill()

                except Exception:
                    pass

                await asyncio.sleep(2)

            return False

    except Exception:
        pass

    return False


async def _get_docker_version() -> dict:
    """Get Docker version."""
    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "version", "--format={{.Server.Version}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
        return {"version": stdout.decode().strip()}
    except Exception as e:
        return {"error": str(e)}


async def _get_recent_images(limit: int = 10) -> dict:
    """Get last N built images."""
    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "images",
            "--format={{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10.0)

        lines = stdout.decode().strip().split("\n")
        images = []
        for line in lines[:limit]:
            if line:
                parts = line.split("\t")
                if len(parts) >= 3:
                    images.append({
                        "name": parts[0],
                        "size": parts[1],
                        "created": parts[2],
                    })

        return {
            "count": len(images),
            "images": images,
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_recent_containers(limit: int = 10) -> dict:
    """Get last N containers (all states)."""
    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a",
            "--format={{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.CreatedAt}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10.0)

        lines = stdout.decode().strip().split("\n")
        containers = []
        for line in lines[:limit]:
            if line:
                parts = line.split("\t", 3)
                if len(parts) >= 4:
                    containers.append({
                        "name": parts[0],
                        "status": parts[1],
                        "ports": parts[2],
                        "created": parts[3],
                    })

        return {
            "count": len(containers),
            "containers": containers,
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_container_summary() -> dict:
    """Get running vs stopped container count."""
    try:
        # Running containers
        process = await asyncio.create_subprocess_exec(
            "docker", "ps", "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10.0)
        running = len([x for x in stdout.decode().strip().split("\n") if x])

        # All containers
        process = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a", "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10.0)
        total = len([x for x in stdout.decode().strip().split("\n") if x])

        stopped = total - running

        return {
            "running": running,
            "stopped": stopped,
            "total": total,
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_disk_usage() -> dict:
    """Get Docker disk usage breakdown."""
    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "system", "df",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10.0)

        lines = stdout.decode().strip().split("\n")[1:]  # Skip header
        usage = []
        for line in lines:
            if line:
                usage.append(line)

        return {"usage": usage}
    except Exception as e:
        return {"error": str(e)}


async def _get_resource_stats() -> dict:
    """Get resource stats for running containers."""
    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "stats", "--no-stream",
            "--format={{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10.0)

        lines = stdout.decode().strip().split("\n")
        stats = []
        for line in lines:
            if line:
                parts = line.split("\t")
                if len(parts) >= 3:
                    stats.append({
                        "container": parts[0][:12],
                        "memory": parts[1],
                        "cpu": parts[2],
                    })

        return {"stats": stats}
    except Exception as e:
        return {"error": str(e), "note": "No running containers or stats unavailable"}


async def _get_docker_config() -> dict:
    """Get Docker Desktop configuration (memory, CPU, swap)."""
    try:
        settings_path = Path.home() / "AppData" / "Roaming" / "Docker" / "settings.json"
        if settings_path.exists():
            with open(settings_path) as f:
                settings = json.load(f)

            memory_mb = settings.get("memoryMiB", "unknown")
            cpus = settings.get("cpus", "unknown")
            swap_mb = settings.get("memorySwapMiB", "unknown")

            return {
                "memory_mb": memory_mb,
                "cpus": cpus,
                "swap_mb": swap_mb,
            }
        else:
            return {"error": "Settings file not found"}
    except Exception as e:
        return {"error": str(e)}


def _add_recommendations(result: dict) -> None:
    """Add recommendations based on check results."""
    config = result["checks"].get("docker_config", {})

    # Check memory allocation
    memory = config.get("memory_mb", 0)
    if isinstance(memory, int) and memory < 8192:
        result["recommendations"].append(
            f"Memory allocation is low ({memory}MB). Recommend 12GB+ for AI workloads. "
            "Go to Docker Desktop Settings > Resources > Memory"
        )

    # Check CPU allocation
    cpus = config.get("cpus", 0)
    if isinstance(cpus, int) and cpus < 4:
        result["recommendations"].append(
            f"CPU allocation is low ({cpus} cores). Recommend 4+ cores. "
            "Go to Docker Desktop Settings > Resources > CPUs"
        )

    # Check disk usage
    disk = result["checks"].get("disk_usage", {})
    if "usage" in disk and disk["usage"]:
        # Note: could parse to check for specific thresholds
        result["recommendations"].append(
            "Run periodic cleanup: docker system prune -a"
        )


def _format_status_report(result: dict) -> str:
    """Format status report as human-readable text."""
    lines = [
        "========== Docker Desktop Status Report ==========\n",
        f"Timestamp: {result['timestamp']}\n",
    ]

    # Daemon health
    if result["daemon_healthy"]:
        lines.append("✅ Docker daemon: HEALTHY")
    elif result["daemon_hanging"]:
        lines.append("⚠️  Docker daemon: HANGING")
    else:
        lines.append("❌ Docker daemon: UNHEALTHY")

    lines.append("")

    # Check results
    if result["daemon_healthy"]:
        checks = result["checks"]

        # Version
        version_info = checks.get("docker_version", {})
        if "version" in version_info:
            lines.append(f"Docker Version: {version_info['version']}")

        # Images
        images_info = checks.get("recent_images", {})
        if "count" in images_info:
            lines.append(f"\nLast 10 Images ({images_info['count']} total):")
            for img in images_info.get("images", []):
                lines.append(
                    f"  {img['name']:<40} {img['size']:<15} {img['created']}"
                )

        # Containers
        containers_info = checks.get("recent_containers", {})
        if "count" in containers_info:
            lines.append(f"\nLast 10 Containers ({containers_info['count']} total):")
            for cont in containers_info.get("containers", []):
                lines.append(
                    f"  {cont['name']:<20} {cont['status']:<25} {cont['ports']:<30}"
                )

        # Summary
        summary = checks.get("container_summary", {})
        if summary:
            lines.append(
                f"\nContainer Summary: {summary.get('running', 0)} running, "
                f"{summary.get('stopped', 0)} stopped (total: {summary.get('total', 0)})"
            )

        # Disk usage
        disk = checks.get("disk_usage", {})
        if "usage" in disk:
            lines.append("\nDisk Usage:")
            for usage_line in disk["usage"][:5]:  # Show first 5 lines
                lines.append(f"  {usage_line}")

        # Config
        config = checks.get("docker_config", {})
        if config and "error" not in config:
            lines.append(
                f"\nDocker Config: Memory={config.get('memory_mb', '?')}MB, "
                f"CPUs={config.get('cpus', '?')}, Swap={config.get('swap_mb', '?')}MB"
            )

    # Issues
    if result["issues"]:
        lines.append("\n⚠️  Issues Detected:")
        for issue in result["issues"]:
            lines.append(f"  - {issue}")

    # Recommendations
    if result["recommendations"]:
        lines.append("\n💡 Recommendations:")
        for rec in result["recommendations"]:
            lines.append(f"  - {rec}")

    lines.append("\n" + "="*50)

    return "\n".join(lines)
