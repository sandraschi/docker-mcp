from fastapi import Body, Depends, FastAPI
from fastmcp import FastMCP

from dockermcp.tools.containers.list_containers import (
    ListContainersParams,
    list_containers,
)
from dockermcp.tools.images.image_management import list_images
from dockermcp.tools.system.system_management import (
    DiskUsageRequest,
    SystemInfoRequest,
    get_disk_usage,
    get_system_info,
)

from .ai import AIRouter
from .auth import authenticate


def setup_webapp(app: FastAPI, mcp_app: FastMCP):
    """Setup standard SOTA web endpoints for Docker-MCP."""

    ai_router = AIRouter(mcp_app)

    @app.get("/api/health")
    async def health():
        return {"status": "healthy", "service": "docker-mcp"}

    @app.get("/api/tools")
    async def list_tools():
        tools = await mcp_app.list_tools()
        return {"tools": [t.name for t in tools]}

    @app.get("/api/containers")
    async def api_containers():
        result = await list_containers(ListContainersParams(all_states=True))
        return result

    @app.get("/api/system")
    async def api_system():
        sys_resp = await get_system_info(
            SystemInfoRequest(include_disk_usage=True, include_swarm_info=False)
        )
        disk_resp = await get_disk_usage(DiskUsageRequest(detailed=True))
        return {
            "system": sys_resp.model_dump() if hasattr(sys_resp, "model_dump") else sys_resp,
            "disk": disk_resp.model_dump() if hasattr(disk_resp, "model_dump") else disk_resp,
        }

    @app.get("/api/images")
    async def api_images():
        return await list_images()

    @app.get("/api/dashboard")
    async def api_dashboard():
        containers_result = await list_containers(
            ListContainersParams(all_states=True)
        )
        system_result = await get_system_info(
            SystemInfoRequest(include_disk_usage=True, include_swarm_info=False)
        )
        disk_result = await get_disk_usage(DiskUsageRequest(detailed=False))
        images_result = await list_images()

        # Ensure results are dictionaries for .get() access
        containers_dict = containers_result if isinstance(containers_result, dict) else {}
        images_dict = images_result if isinstance(images_result, dict) else {}

        sys_info = (
            system_result.system_info
            if hasattr(system_result, "system_info")
            else system_result.get("system_info") if isinstance(system_result, dict) else None
        )
        disk_data = (
            disk_result.disk_usage
            if hasattr(disk_result, "disk_usage") and disk_result.disk_usage
            else None
        )
        disk_summary = (
            disk_data.get("summary", {}) if isinstance(disk_data, dict) else None
        )
        return {
            "containers": containers_dict.get("containers", []),
            "containers_status": containers_dict.get("status"),
            "containers_message": containers_dict.get("message"),
            "system_info": sys_info,
            "system_status": getattr(system_result, "status", system_result.get("status") if isinstance(system_result, dict) else None),
            "disk_summary": disk_summary,
            "images": images_dict.get("images", []),
            "images_count": images_dict.get("count", 0),
            "images_status": images_dict.get("status"),
        }

    @app.post("/api/chat")
    async def chat(payload: dict = Body(...), user: str = Depends(authenticate)):
        query = payload.get("query", "")
        return await ai_router.process_command(query)
