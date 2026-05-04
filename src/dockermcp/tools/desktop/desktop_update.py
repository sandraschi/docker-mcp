"""
Docker Desktop Update Tool - Manages Docker Desktop updates and resets.

Handles update elevation errors, full system wipes, and configuration resets.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from dockermcp.mcp_instance import mcp


@mcp.tool()
async def docker_desktop_update(full_wipe: bool = False) -> dict[str, Any]:
    """
    Fix Docker Desktop update elevation errors and manage system resets.

    Procedure:
    1. Stop Docker Desktop gracefully
    2. Clear update temp folder (fixes elevation error)
    3. Optionally wipe Docker app data (full_wipe=True)
    4. Restart Docker Desktop
    5. Prompt user to check for updates in Settings

    Args:
        full_wipe: If True, also clear Docker app data for complete reset

    Returns:
        Dictionary with update procedure status
    """

    result = {
        "timestamp": datetime.now().isoformat(),
        "stages": {},
        "update_ready": False,
        "next_steps": [],
    }

    # Stage 1: Stop Docker Desktop
    result["stages"]["stop"] = await _stop_docker_desktop()
    await asyncio.sleep(2)

    # Stage 2: Clear update temp folder
    result["stages"]["clear_temp"] = await _clear_update_temp()

    # Stage 3: Clear app data (optional)
    if full_wipe:
        result["stages"]["full_wipe"] = await _wipe_docker_data()

    # Stage 4: Restart Docker Desktop
    result["stages"]["restart"] = await _restart_docker_desktop()

    if result["stages"]["restart"].get("success"):
        await asyncio.sleep(5)

        # Verify startup
        result["stages"]["verify"] = await _verify_daemon_startup()

        if result["stages"]["verify"].get("responsive"):
            result["update_ready"] = True
            result["next_steps"] = [
                "1. Wait 30 seconds for Docker Desktop to fully initialize",
                "2. Open Docker Desktop Settings (gear icon in system tray)",
                "3. Go to Settings > Check for Updates",
                "4. Install any available updates",
            ]
        else:
            result["next_steps"].append(
                "Daemon not responding - try manual restart"
            )

    output = _format_update_report(result, full_wipe)

    return {
        "status": "success" if result["update_ready"] else "error",
        "message": output,
        "data": result,
    }


async def _stop_docker_desktop() -> dict:
    """Stop Docker Desktop gracefully."""
    try:
        await asyncio.create_subprocess_exec(
            "taskkill", "/IM", "Docker Desktop.exe", "/T",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _clear_update_temp() -> dict:
    """Clear Docker update temp folder."""
    try:
        temp_path = Path.home() / "AppData" / "Local" / "Temp" / "DockerDesktopUpdates"

        if temp_path.exists():
            import shutil
            shutil.rmtree(temp_path)
            return {
                "success": True,
                "path": str(temp_path),
                "action": "removed",
            }
        else:
            return {
                "success": True,
                "path": str(temp_path),
                "action": "already_clean",
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _wipe_docker_data() -> dict:
    """Wipe Docker app data for full reset."""
    wiped = []
    failed = []

    paths = [
        Path.home() / "AppData" / "Roaming" / "Docker",
        Path.home() / "AppData" / "Local" / "Docker",
    ]

    for path in paths:
        try:
            if path.exists():
                import shutil
                shutil.rmtree(path)
                wiped.append(str(path))
        except Exception as e:
            failed.append({str(path): str(e)})

    return {
        "wiped": wiped,
        "failed": failed,
        "success": len(failed) == 0,
    }


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


async def _verify_daemon_startup() -> dict:
    """Verify daemon started after update cleanup."""
    for attempt in range(10):
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                _stdout, _stderr = await asyncio.wait_for(
                    process.communicate(), timeout=5.0
                )
                if process.returncode == 0:
                    return {
                        "responsive": True,
                        "attempts": attempt + 1,
                    }
            except TimeoutError:
                process.kill()

        except Exception:  # noqa: S110
            pass

        if attempt < 9:
            await asyncio.sleep(2)

    return {
        "responsive": False,
        "attempts": 10,
    }


def _format_update_report(result: dict, full_wipe: bool) -> str:
    """Format update report."""
    lines = [
        "========== Docker Desktop Update Preparation ==========\n",
        f"Timestamp: {result['timestamp']}\n",
    ]

    # Stop
    stop_result = result["stages"].get("stop", {})
    if stop_result.get("success"):
        lines.append("✅ Docker Desktop stopped")
    else:
        lines.append(f"❌ Failed to stop Docker: {stop_result.get('error')}")

    # Clear temp
    temp_result = result["stages"].get("clear_temp", {})
    if temp_result.get("success"):
        action = temp_result.get("action", "cleared")
        lines.append(f"✅ Update temp folder {action}: {temp_result['path']}")
    else:
        lines.append(f"❌ Failed to clear temp: {temp_result.get('error')}")

    # Full wipe
    if full_wipe:
        wipe_result = result["stages"].get("full_wipe", {})
        if wipe_result.get("success"):
            lines.append("✅ Docker data wiped for full reset")
            for path in wipe_result.get("wiped", []):
                lines.append(f"  - Removed: {path}")
        else:
            lines.append("⚠️  Full wipe partially failed")
            for failure in wipe_result.get("failed", []):
                lines.append(f"  - Error: {failure}")

    # Restart
    restart_result = result["stages"].get("restart", {})
    if restart_result.get("success"):
        lines.append("✅ Docker Desktop restarted")
    else:
        lines.append(f"❌ Restart failed: {restart_result.get('error')}")

    # Verify
    verify_result = result["stages"].get("verify", {})
    if verify_result.get("responsive"):
        lines.append(
            f"✅ Daemon responsive (verified in {verify_result['attempts']} attempt)"
        )
    else:
        lines.append(
            f"⚠️  Daemon not yet responsive ({verify_result.get('attempts')} attempts)"
        )

    lines.append("")

    # Overall status
    if result["update_ready"]:
        lines.append("✅ READY FOR UPDATE")
    else:
        lines.append("⚠️  UPDATE PREPARATION INCOMPLETE")

    lines.append("")

    # Next steps
    if result["next_steps"]:
        lines.append("Next Steps:")
        for step in result["next_steps"]:
            lines.append(f"  {step}")

    lines.append("\n" + "="*55)

    return "\n".join(lines)
