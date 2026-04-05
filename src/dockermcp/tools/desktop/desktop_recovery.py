"""
Docker Daemon Recovery Tool - Emergency procedures for hung daemon.

Provides automated recovery from hanging daemon with process termination,
restart, and verification.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from dockermcp.mcp_instance import mcp


@mcp.tool()
async def docker_daemon_recover() -> dict[str, Any]:
    """
    Automatically recover from hanging Docker daemon.

    Recovery procedure:
    1. Kill hung Docker processes (Docker Desktop, backend, vpnkit)
    2. Wait for cleanup
    3. Restart Docker Desktop
    4. Verify daemon responsiveness (5 attempts)
    5. Report success/failure with next steps

    Returns:
        Dictionary with recovery status and recommendations
    """

    result = {
        "timestamp": datetime.now().isoformat(),
        "stages": {},
        "recovery_successful": False,
        "recommendations": [],
    }

    # Stage 1: Kill hung processes
    result["stages"]["kill_processes"] = await _kill_hung_processes()

    # Stage 2: Wait for cleanup
    await asyncio.sleep(3)

    # Stage 3: Restart Docker Desktop
    result["stages"]["restart"] = await _restart_docker_desktop()

    if result["stages"]["restart"].get("success"):
        # Wait for startup
        await asyncio.sleep(8)

        # Stage 4: Verify responsiveness
        result["stages"]["verify"] = await _verify_daemon_responsiveness()

        if result["stages"]["verify"].get("responsive"):
            result["recovery_successful"] = True
            result["recommendations"].append("Daemon recovered successfully!")
        else:
            result["recommendations"].append(
                "Daemon still not responsive after restart. "
                "Try: docker_desktop_update with full_wipe=True"
            )
    else:
        result["recommendations"].append(
            "Failed to restart Docker. Check if it's installed at: "
            "C:/Program Files/Docker/Docker/Docker.exe"
        )

    output = _format_recovery_report(result)

    return {
        "status": "success" if result["recovery_successful"] else "error",
        "message": output,
        "data": result,
    }


@mcp.tool()
async def docker_daemon_restart() -> dict[str, Any]:
    """
    Gracefully restart Docker Desktop daemon.

    Simple restart without killing hung processes.
    Use docker_daemon_recover if daemon is hanging.

    Returns:
        ToolResult with restart status
    """

    result = {
        "timestamp": datetime.now().isoformat(),
        "restart_status": "unknown",
        "responsive_after": False,
    }

    docker_path = Path("C:/Program Files/Docker/Docker/Docker.exe")
    if not docker_path.exists():
        return {
            "status": "error",
            "message": "Docker Desktop not found at expected location",
            "data": result,
        }

    try:
        # Start Docker Desktop
        await asyncio.create_subprocess_exec(
            str(docker_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        result["restart_status"] = "started"

        # Wait for startup
        await asyncio.sleep(8)

        # Verify
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
                        result["restart_status"] = "successful"
                        result["responsive_after"] = True
                        break
                except TimeoutError:
                    process.kill()

            except Exception:
                pass

            await asyncio.sleep(2)

        if not result["responsive_after"]:
            result["restart_status"] = "started_but_not_responsive"

    except Exception as e:
        result["restart_status"] = "failed"
        result["error"] = str(e)

    output = f"""
========== Docker Daemon Restart Report ==========

Timestamp: {result['timestamp']}
Restart Status: {result['restart_status']}
Responsive: {'✅ Yes' if result['responsive_after'] else '❌ No'}

{"" if result['responsive_after'] else 'Daemon may still be initializing. Wait 30 seconds and try again.'}

==================================================
""".strip()

    return {
        "status": "success" if result["responsive_after"] else "error",
        "message": output,
        "data": result,
    }


async def _kill_hung_processes() -> dict:
    """Kill hung Docker processes."""
    result = {
        "killed": [],
        "failed": [],
    }

    processes = [
        "Docker Desktop.exe",
        "com.docker.backend.exe",
        "vpnkit.exe",
    ]

    for proc_name in processes:
        try:
            await asyncio.create_subprocess_exec(
                "taskkill", "/IM", proc_name, "/F",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            result["killed"].append(proc_name)
        except Exception as e:
            result["failed"].append({proc_name: str(e)})

    return result


async def _restart_docker_desktop() -> dict:
    """Restart Docker Desktop."""
    docker_path = Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")

    if not docker_path.exists():
        return {
            "success": False,
            "error": f"Docker not found at {docker_path}",
        }

    try:
        await asyncio.create_subprocess_exec(
            str(docker_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _verify_daemon_responsiveness(max_attempts: int = 5) -> dict:
    """Verify daemon is responsive."""
    for attempt in range(max_attempts):
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
                    return {
                        "responsive": True,
                        "attempts": attempt + 1,
                    }
            except TimeoutError:
                process.kill()

        except Exception:
            pass

        if attempt < max_attempts - 1:
            await asyncio.sleep(2)

    return {
        "responsive": False,
        "attempts": max_attempts,
    }


def _format_recovery_report(result: dict) -> str:
    """Format recovery report."""
    lines = [
        "========== Docker Daemon Recovery Report ==========\n",
        f"Timestamp: {result['timestamp']}\n",
    ]

    # Kill results
    kill_result = result["stages"].get("kill_processes", {})
    if kill_result.get("killed"):
        lines.append("Processes Killed:")
        for proc in kill_result["killed"]:
            lines.append(f"  ✅ {proc}")

    lines.append("")

    # Restart
    restart_result = result["stages"].get("restart", {})
    if restart_result.get("success"):
        lines.append("✅ Docker Desktop restarted")
    else:
        lines.append(f"❌ Restart failed: {restart_result.get('error', 'Unknown')}")

    lines.append("")

    # Verify
    verify_result = result["stages"].get("verify", {})
    if verify_result.get("responsive"):
        lines.append(
            f"✅ Daemon responsive (verified in {verify_result['attempts']} attempt)"
        )
    else:
        lines.append(
            f"❌ Daemon not responsive after {verify_result.get('attempts', '?')} attempts"
        )

    lines.append("")

    # Overall result
    if result["recovery_successful"]:
        lines.append("✅ RECOVERY SUCCESSFUL")
    else:
        lines.append("❌ RECOVERY FAILED")

    lines.append("")

    # Recommendations
    if result["recommendations"]:
        lines.append("Next Steps:")
        for rec in result["recommendations"]:
            lines.append(f"  - {rec}")

    lines.append("\n" + "="*50)

    return "\n".join(lines)
