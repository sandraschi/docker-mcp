from typing import Literal

import httpx
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response
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

from .activity_log import (
    SortOrder,
    clear_logs,
    export_logs,
    log_activity,
    log_stats,
    query_logs,
)
from .ai import AIRouter
from .auth import authenticate
from .llm.manager import get_llm_manager

SortParam = Literal["asc", "desc"]


def setup_webapp(app: FastAPI, mcp_app: FastMCP):
    """Setup standard SOTA web endpoints for Docker-MCP."""

    ai_router = AIRouter(mcp_app)

    @app.get("/api/health")
    async def health():
        return {"status": "healthy", "service": "docker-mcp"}

    @app.get("/api/capabilities")
    async def capabilities():
        tools = await mcp_app.list_tools()
        return {
            "service": "docker-mcp",
            "pages": {
                "dashboard": True,
                "containers": True,
                "images": True,
                "tools": True,
                "logs": True,
                "settings": True,
                "chat": True,
            },
            "tool_count": len(tools),
            "llm_glom": True,
        }

    @app.get("/api/tools")
    async def list_tools():
        tools = await mcp_app.list_tools()
        return {"tools": [t.name for t in tools]}

    @app.get("/api/llm/providers")
    async def llm_providers(refresh: bool = Query(False)):
        manager = get_llm_manager()
        if refresh:
            await manager.glom_local_providers_if_up(force=True)
        return {"success": True, "providers": manager.list_providers()}

    @app.get("/api/logs")
    async def logs_query(
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        level: str | None = Query(None),
        kind: str | None = Query(None),
        search: str | None = Query(None),
        sort: str = Query("desc"),
        after_id: str | None = Query(None),
    ):
        order: SortOrder = "asc" if sort == "asc" else "desc"
        return query_logs(
            limit=limit,
            offset=offset,
            level=level,
            kind=kind,
            search=search,
            sort=order,
            after_id=after_id,
        )

    @app.get("/api/logs/stats")
    async def logs_stats():
        return log_stats()

    @app.get("/api/logs/export")
    async def logs_export(
        format: str = Query("json"),
        level: str | None = Query(None),
        kind: str | None = Query(None),
        search: str | None = Query(None),
        sort: str = Query("desc"),
    ):
        order: SortOrder = "asc" if sort == "asc" else "desc"
        if format not in ("json", "csv"):
            format = "json"
        body, media_type, filename = export_logs(
            format=format,
            level=level,
            kind=kind,
            search=search,
            sort=order,
        )
        log_activity("export", f"Logs exported as {format}", meta={"filename": filename})
        return Response(
            content=body,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.delete("/api/logs")
    async def logs_clear():
        clear_logs()
        log_activity("system", "Log buffer cleared", level="WARNING")
        return {"success": True}

    @app.get("/api/containers")
    async def api_containers():
        result = await list_containers(ListContainersParams(all_states=True))
        log_activity("tool_call", "list_containers (web API)")
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
        try:
            containers_result = await list_containers(
                ListContainersParams(all_states=True)
            )
            system_result = await get_system_info(
                SystemInfoRequest(include_disk_usage=True, include_swarm_info=False)
            )
            disk_result = await get_disk_usage(DiskUsageRequest(detailed=False))
            images_result = await list_images()

            containers_dict = (
                containers_result if isinstance(containers_result, dict) else {}
            )
            images_dict = images_result if isinstance(images_result, dict) else {}

            sys_info = (
                system_result.system_info
                if hasattr(system_result, "system_info")
                else system_result.get("system_info")
                if isinstance(system_result, dict)
                else None
            )
            disk_data = (
                disk_result.disk_usage
                if hasattr(disk_result, "disk_usage") and disk_result.disk_usage
                else None
            )
            disk_summary = (
                disk_data.get("summary", {}) if isinstance(disk_data, dict) else None
            )
            log_activity("tool_call", "dashboard aggregate")
            return {
                "containers": containers_dict.get("containers", []),
                "containers_status": containers_dict.get("status"),
                "containers_message": containers_dict.get("message"),
                "system_info": sys_info,
                "system_status": getattr(
                    system_result,
                    "status",
                    system_result.get("status")
                    if isinstance(system_result, dict)
                    else None,
                ),
                "disk_summary": disk_summary,
                "images": images_dict.get("images", []),
                "images_count": images_dict.get("count", 0),
                "images_status": images_dict.get("status"),
            }
        except Exception as exc:
            log_activity("server", f"dashboard error: {exc}", level="ERROR")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/chat")
    async def chat(payload: dict = Body(...), user: str = Depends(authenticate)):
        query = payload.get("query", "")
        provider = str(payload.get("provider") or "ollama")
        model = str(payload.get("model") or "llama3.2")
        endpoint = str(payload.get("endpoint") or "http://127.0.0.1:11434").rstrip("/")
        log_activity(
            "tool_call",
            f"chat via {provider}",
            meta={"model": model},
        )
        try:
            if provider == "ollama":
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{endpoint}/api/generate",
                        json={"model": model, "prompt": query, "stream": False},
                    )
                    response.raise_for_status()
                    text = response.json().get("response", "No response from Ollama")
            elif provider == "lmstudio":
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{endpoint}/v1/chat/completions",
                        json={
                            "messages": [{"role": "user", "content": query}],
                            "model": model,
                            "temperature": 0.7,
                        },
                    )
                    response.raise_for_status()
                    text = response.json()["choices"][0]["message"]["content"]
            else:
                return await ai_router.process_command(query)
            return {"response": text, "status": "success"}
        except Exception as exc:
            log_activity("server", f"chat error: {exc}", level="ERROR")
            return {"response": f"AI Bridge Error: {exc}", "status": "error"}
