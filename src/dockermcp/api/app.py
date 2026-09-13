"""
FastAPI routes for Docker MCP webapp
"""

import logging
import os
import sys

import docker
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI app with Docker endpoints"""

    app = FastAPI(title="Docker MCP API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:10807",
            "http://localhost:10807",
            "http://goliath:10807",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    client: docker.DockerClient | None = None

    # Dynamic Docker client resolver
    def get_client() -> docker.DockerClient | None:
        nonlocal client
        if client:
            try:
                client.ping()
                return client
            except Exception:
                client = None
        candidate_urls = [None]
        if sys.platform == "win32":
            candidate_urls.extend(["npipe:////./pipe/dockerDesktopLinuxEngine", "npipe:////./pipe/docker_engine"])
        for base_url in candidate_urls:
            try:
                c = docker.DockerClient(base_url=base_url) if base_url else docker.from_env()
                c.ping()
                client = c
                return client
            except Exception as e:
                logger.debug(f"Docker client ping/connect failed for {base_url}: {e}")
        client = None
        return None

    # Health check
    @app.get("/health")
    @app.get("/api/health")
    async def health():
        return {"status": "healthy", "service": "docker-mcp"}

    # Docker daemon status endpoint
    @app.get("/api/docker/status")
    async def docker_status():
        from dockermcp.docker_context import get_docker_status

        return get_docker_status()

    # Dashboard endpoint
    @app.get("/api/dashboard")
    async def get_dashboard():
        """Get dashboard overview with system info and container status"""
        active_client = get_client()
        if not active_client:
            raise HTTPException(status_code=503, detail="Docker not available")

        try:
            # Get system info
            info = active_client.info()
            version = active_client.version()

            # Get containers
            containers = active_client.containers.list(all=True)
            running = len([c for c in containers if c.status == "running"])

            # Get images
            images = active_client.images.list()

            return {
                "system_info": {
                    "docker_version": version.get("Version"),
                    "containers": {
                        "total": len(containers),
                        "running": running,
                        "paused": len([c for c in containers if c.status == "paused"]),
                        "stopped": len(containers) - running,
                    },
                    "images": {
                        "total": len(images),
                    },
                    "memory": {
                        "total": info.get("MemTotal", 0),
                        "total_formatted": f"{info.get('MemTotal', 0) / (1024**3):.1f}GB",
                    },
                    "cpu": {
                        "cores": info.get("NCPU", 0),
                    },
                },
                "containers": [
                    {
                        "id": c.id[:12],
                        "name": c.name,
                        "status": c.status,
                        "image": (c.attrs or {}).get("Image") or "",
                        "state": "running" if c.status == "running" else "stopped",
                    }
                    for c in containers[:10]
                ],
                "containers_status": "success",
                "containers_message": f"Total: {len(containers)} containers",
                "disk_summary": None,
                "images": [
                    {
                        "id": img.id[:12] if img.id else "",
                        "repo_tags": img.tags or ["<none>"],
                        "size": (img.attrs or {}).get("Size", 0),
                        "created": (img.attrs or {}).get("Created"),
                    }
                    for img in images[:10]
                ],
                "images_count": len(images),
                "images_status": "success",
                "system_status": "success",
            }
        except Exception as e:
            logger.error(f"Error getting dashboard: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    # Containers endpoint
    @app.get("/api/containers")
    async def get_containers():
        """Get list of all containers"""
        active_client = get_client()
        if not active_client:
            raise HTTPException(status_code=503, detail="Docker not available")

        try:
            containers = active_client.containers.list(all=True)
            return {
                "containers": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "status": c.status,
                        "image": (c.attrs or {}).get("Image") or "",
                        "state": "running" if c.status == "running" else "stopped",
                        "created": c.attrs.get("Created"),
                    }
                    for c in containers
                ],
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Error getting containers: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/images")
    async def get_images():
        """Get list of images without per-image inspect or system df."""
        active_client = get_client()
        if not active_client:
            raise HTTPException(status_code=503, detail="Docker not available")
        try:
            images = active_client.images.list()
            return {
                "status": "success",
                "count": len(images),
                "images": [
                    {
                        "id": img.id,
                        "repo_tags": img.tags or [],
                        "size": (img.attrs or {}).get("Size", 0),
                        "created": (img.attrs or {}).get("Created"),
                        "dangling": not bool(img.tags),
                    }
                    for img in images
                ],
            }
        except Exception as e:
            logger.error(f"Error getting images: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    # Tools endpoint
    @app.get("/api/tools")
    async def get_tools():
        """Get list of available MCP tools"""
        docker_desktop_tools = [
            "docker_desktop_status",
            "docker_daemon_recover",
            "docker_daemon_restart",
            "docker_desktop_update",
        ]

        container_tools = [
            "list_containers",
            "start_container",
            "stop_container",
            "restart_container",
            "remove_container",
            "get_container_logs",
        ]

        return {
            "tools": docker_desktop_tools + container_tools,
            "docker_desktop_tools": docker_desktop_tools,
            "container_tools": container_tools,
        }

    @app.get("/api/v1/diagnostics")
    async def diagnostics():
        try:
            import psutil

            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
        except ImportError:
            cpu = mem = disk = None
        return {
            "success": True,
            "backend": {"port": 10807, "status": "running"},
            "system": {"cpu_percent": cpu, "memory_percent": mem, "disk_percent": disk},
            "tools": {"total": 0},
            "cua_status": {"tesseract_available": False, "window_found": False},
        }

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=10807)
