"""Docker backup and restore: images (save/load), volumes, compose projects."""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Annotated, Any

from dockermcp.docker_context import docker_available, docker_error, docker_client
from dockermcp.mcp_instance import mcp


async def _run_cmd(cmd: list[str], timeout: int = 300) -> dict[str, Any]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            return {"success": False, "error": err or f"exit code {proc.returncode}"}
        return {"success": True, "output": out}
    except asyncio.TimeoutError:
        return {"success": False, "error": f"Command timed out ({timeout}s)"}
    except FileNotFoundError:
        return {"success": False, "error": "docker not found on PATH"}


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
async def docker_backup(
    operation: Annotated[str, "Operation: save_image, load_image, backup_volume, restore_volume, export_compose."],
    image: Annotated[str | None, "Image name:tag for save_image/load_image."] = None,
    volume: Annotated[str | None, "Volume name for backup_volume/restore_volume."] = None,
    project: Annotated[str | None, "Compose project name for export_compose."] = None,
    output_path: Annotated[str | None, "Output file path (save_image, backup_volume, export_compose)."] = None,
    input_path: Annotated[str | None, "Input file path (load_image, restore_volume)."] = None,
) -> dict[str, Any]:
    """Backup and restore Docker resources.

    ## How Docker data works
    Docker data is NOT one big blob — it's split into:
    - **Images** (read-only templates) — export/import with `docker save` / `docker load`
    - **Volumes** (persistent data like DBs, configs) — backup via tar archive
    - **Compose projects** (YAML + volumes + metadata) — export all of the above

    ## Operations
    - **save_image**: Export one or more images to a .tar file via `docker save`.
    - **load_image**: Import images from a .tar file via `docker load`.
    - **backup_volume**: Backup a Docker volume's data to a .tar.gz file.
    - **restore_volume**: Restore a Docker volume from a .tar.gz backup file.
    - **export_compose**: Archive a compose project directory + volume data.

    ## Return Format
    {"success": bool, "operation": str, "message": str, "data": {...}}

    ## Examples
    docker_backup(operation="save_image", image="nginx:latest", output_path="C:/backups/nginx.tar")
    docker_backup(operation="load_image", input_path="C:/backups/nginx.tar")
    docker_backup(operation="backup_volume", volume="myapp_data", output_path="C:/backups/myapp_data.tar.gz")
    docker_backup(operation="restore_volume", volume="myapp_data", input_path="C:/backups/myapp_data.tar.gz")
    docker_backup(operation="export_compose", project="myapp", output_path="C:/backups/myapp-compose-backup")
    """
    if not docker_available:
        return {"success": False, "error": f"Docker not available: {docker_error}"}

    if operation == "save_image":
        if not image or not output_path:
            return {"success": False, "error": "image and output_path required"}
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result = await _run_cmd(["docker", "save", "-o", output_path, image])
        size = os.path.getsize(output_path) if result["success"] else 0
        return {
            "success": result["success"],
            "operation": operation,
            "message": f"Saved {image} to {output_path} ({size / 1024 / 1024:.1f} MB)" if result["success"] else result["error"],
            "data": {"image": image, "output_path": output_path, "size_bytes": size} if result["success"] else {},
        }

    elif operation == "load_image":
        if not input_path:
            return {"success": False, "error": "input_path required"}
        if not os.path.isfile(input_path):
            return {"success": False, "error": f"File not found: {input_path}"}
        result = await _run_cmd(["docker", "load", "-i", input_path])
        return {
            "success": result["success"],
            "operation": operation,
            "message": result.get("output", "Images loaded") if result["success"] else result["error"],
            "data": {"input_path": input_path, "output": result.get("output", "")} if result["success"] else {},
        }

    elif operation == "backup_volume":
        if not volume or not output_path:
            return {"success": False, "error": "volume and output_path required"}
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result = await _run_cmd([
            "docker", "run", "--rm",
            "-v", f"{volume}:/volume:ro",
            "-v", f"{os.path.dirname(os.path.abspath(output_path))}:/backup",
            "alpine", "tar", "czf", f"/backup/{os.path.basename(output_path)}", "-C", "/volume", ".",
        ])
        size = os.path.getsize(output_path) if result["success"] else 0
        return {
            "success": result["success"],
            "operation": operation,
            "message": f"Backed up volume {volume} to {output_path} ({size / 1024 / 1024:.1f} MB)" if result["success"] else result["error"],
            "data": {"volume": volume, "output_path": output_path, "size_bytes": size} if result["success"] else {},
        }

    elif operation == "restore_volume":
        if not volume or not input_path:
            return {"success": False, "error": "volume and input_path required"}
        if not os.path.isfile(input_path):
            return {"success": False, "error": f"File not found: {input_path}"}
        result = await _run_cmd([
            "docker", "run", "--rm",
            "-v", f"{volume}:/volume",
            "-v", f"{os.path.dirname(os.path.abspath(input_path))}:/backup:ro",
            "alpine", "tar", "xzf", f"/backup/{os.path.basename(input_path)}", "-C", "/volume",
        ])
        return {
            "success": result["success"],
            "operation": operation,
            "message": f"Restored volume {volume} from {input_path}" if result["success"] else result["error"],
            "data": {"volume": volume, "input_path": input_path} if result["success"] else {},
        }

    elif operation == "export_compose":
        if not project or not output_path:
            return {"success": False, "error": "project and output_path required"}
        os.makedirs(output_path, exist_ok=True)
        steps = []
        config_result = await _run_cmd(["docker", "compose", "-p", project, "config"])
        if config_result["success"]:
            config_path = os.path.join(output_path, "docker-compose.yml")
            with open(config_path, "w") as f:
                f.write(config_result["output"])
            steps.append(f"Config saved to {config_path}")
        ps_result = await _run_cmd(["docker", "compose", "-p", project, "ps", "--format", "json"])
        if ps_result["success"]:
            with open(os.path.join(output_path, "containers.json"), "w") as f:
                f.write(ps_result["output"])
            steps.append("Container list saved")
        images_path = os.path.join(output_path, "images")
        os.makedirs(images_path, exist_ok=True)
        img_result = await _run_cmd(["docker", "compose", "-p", project, "images", "--format", "json"])
        if img_result["success"] and img_result["output"]:
            import json
            try:
                images = [json.loads(l) for l in img_result["output"].split("\n") if l.strip()]
                for img in images:
                    tag = img.get("Image", img.get("image", "unknown")).replace("/", "_").replace(":", "_")
                    save_result = await _run_cmd(["docker", "save", "-o", os.path.join(images_path, f"{tag}.tar"), img.get("ID", "")])
                    if save_result["success"]:
                        steps.append(f"Saved image {tag}")
            except json.JSONDecodeError:
                steps.append("Could not parse image list")
        return {
            "success": True,
            "operation": operation,
            "message": f"Compose project {project} exported to {output_path}",
            "data": {"project": project, "output_path": output_path, "steps": steps},
        }

    return {"success": False, "operation": operation, "error": f"Unknown operation: {operation}"}
