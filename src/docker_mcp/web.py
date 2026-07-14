import json
from collections.abc import AsyncGenerator
from typing import Literal

import httpx
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
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
    import time

    _start_time = time.time()

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
        sys_resp = await get_system_info(SystemInfoRequest(include_disk_usage=True, include_swarm_info=False))
        disk_resp = await get_disk_usage(DiskUsageRequest(detailed=True))
        return {
            "system": sys_resp.model_dump() if hasattr(sys_resp, "model_dump") else sys_resp,
            "disk": disk_resp.model_dump() if hasattr(disk_resp, "model_dump") else disk_resp,
        }

    @app.get("/api/images")
    async def api_images():
        return await list_images()

    @app.get("/api/compose/projects")
    async def api_compose_projects(all_: bool = Query(False, alias="all")):
        from dockermcp.tools.compose.compose_management import _compose_list

        return await _compose_list(all=all_)

    @app.get("/api/compose/ps")
    async def api_compose_ps(project: str = Query(...)):
        from dockermcp.tools.compose.compose_management import _compose_ps

        return await _compose_ps(project=project)

    @app.post("/api/compose/up")
    async def api_compose_up(payload: dict = Body(...)):
        from dockermcp.tools.compose.compose_management import _compose_up

        return await _compose_up(
            project=payload["project"], build=payload.get("build", False), detach=payload.get("detach", True)
        )

    @app.post("/api/compose/down")
    async def api_compose_down(payload: dict = Body(...)):
        from dockermcp.tools.compose.compose_management import _compose_down

        return await _compose_down(project=payload["project"], volumes=payload.get("volumes", False))

    @app.get("/api/compose/logs")
    async def api_compose_logs(project: str = Query(...), tail: int = Query(50)):
        from dockermcp.tools.compose.compose_management import _compose_logs

        return await _compose_logs(project=project, tail=tail)

    @app.get("/api/compose/config")
    async def api_compose_config(project: str = Query(...)):
        from dockermcp.tools.compose.compose_management import _compose_config

        return await _compose_config(project=project)

    @app.post("/api/compose/analyze")
    async def api_compose_analyze(payload: dict = Body(...)):
        from dockermcp.tools.compose.compose_analysis import analyze_compose_file

        file_path = payload.get("file_path", "")
        if not file_path:
            return {"success": False, "error": "file_path required"}
        result = analyze_compose_file(file_path)
        log_activity(
            "tool_call",
            f"compose analyze: {file_path}",
            meta={"service_count": result.get("service_count", 0) if result.get("success") else 0},
        )
        return result

    @app.get("/api/dashboard")
    async def api_dashboard():
        try:
            containers_result = await list_containers(ListContainersParams(all_states=True))
            system_result = await get_system_info(SystemInfoRequest(include_disk_usage=True, include_swarm_info=False))
            disk_result = await get_disk_usage(DiskUsageRequest(detailed=False))
            images_result = await list_images()

            containers_dict = containers_result if isinstance(containers_result, dict) else {}
            images_dict = images_result if isinstance(images_result, dict) else {}

            sys_info = (
                system_result.system_info
                if hasattr(system_result, "system_info")
                else system_result.get("system_info")
                if isinstance(system_result, dict)
                else None
            )
            disk_data = (
                disk_result.disk_usage if hasattr(disk_result, "disk_usage") and disk_result.disk_usage else None
            )
            disk_summary = disk_data.get("summary", {}) if isinstance(disk_data, dict) else None
            log_activity("tool_call", "dashboard aggregate")
            return {
                "containers": containers_dict.get("containers", []),
                "containers_status": containers_dict.get("status"),
                "containers_message": containers_dict.get("message"),
                "system_info": sys_info,
                "system_status": getattr(
                    system_result,
                    "status",
                    system_result.get("status") if isinstance(system_result, dict) else None,
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
        system_prompt = payload.get("system_prompt", "")
        stream = payload.get("stream", False)
        mode = payload.get("mode", "llm")
        history = payload.get("history", [])
        agentic_tools = payload.get("agentic_tools", False)

        log_activity("tool_call", f"chat via {provider}", meta={"model": model, "stream": stream, "mode": mode})

        if mode == "agentic" and stream:
            return StreamingResponse(
                _agentic_chat_stream(query, provider, model, endpoint, system_prompt, history),
                media_type="text/event-stream",
            )

        try:
            if provider == "ollama":
                async with httpx.AsyncClient(timeout=120.0) as client:
                    ollama_messages = []
                    if system_prompt:
                        ollama_messages.append({"role": "system", "content": system_prompt})
                    for h in history:
                        ollama_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                    ollama_messages.append({"role": "user", "content": query})
                    if stream:
                        return StreamingResponse(
                            _stream_ollama(client, endpoint, model, ollama_messages),
                            media_type="text/event-stream",
                        )
                    response = await client.post(
                        f"{endpoint}/api/chat",
                        json={"model": model, "messages": ollama_messages, "stream": False},
                    )
                    response.raise_for_status()
                    text = response.json().get("message", {}).get("content", "No response")
            elif provider == "lmstudio":
                async with httpx.AsyncClient(timeout=120.0) as client:
                    lm_messages = []
                    if system_prompt:
                        lm_messages.append({"role": "system", "content": system_prompt})
                    for h in history:
                        lm_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                    lm_messages.append({"role": "user", "content": query})
                    if stream:
                        return StreamingResponse(
                            _stream_lmstudio(client, endpoint, model, lm_messages),
                            media_type="text/event-stream",
                        )
                    response = await client.post(
                        f"{endpoint}/v1/chat/completions",
                        json={"messages": lm_messages, "model": model, "temperature": 0.7},
                    )
                    response.raise_for_status()
                    text = response.json()["choices"][0]["message"]["content"]
            else:
                return await ai_router.process_command(query)

            if agentic_tools:
                from .tool_orchestrator import _match_query, execute_tool

                tool_name = _match_query(query)
                if tool_name:
                    tool_result = await execute_tool(tool_name, query)
                    return {"response": text, "status": "success", "tool_calls": [tool_result]}
            return {"response": text, "status": "success"}
        except Exception as exc:
            log_activity("server", f"chat error: {exc}", level="ERROR")
            return {"response": f"AI Bridge Error: {exc}", "status": "error"}


class _AgenticEvent:
    """SSE event types for agentic chat."""

    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DONE = "done"


async def _agentic_chat_stream(
    query: str, provider: str, model: str, endpoint: str, system_prompt: str, history: list
) -> AsyncGenerator[str, None]:
    """Stream agentic chat with interleaved tool execution."""
    from .tool_orchestrator import _match_query, execute_tool, tool_to_nl_name

    tool_name = _match_query(query)
    tool_result = None

    if tool_name:
        yield f"data: {json.dumps({'type': _AgenticEvent.TEXT, 'content': f'Running {tool_to_nl_name(tool_name)}...'})}\n\n"
        yield f"data: {json.dumps({'type': _AgenticEvent.TOOL_CALL, 'tool': tool_name, 'nl_name': tool_to_nl_name(tool_name)})}\n\n"
        tool_result = await execute_tool(tool_name, query)
        yield f"data: {json.dumps({'type': _AgenticEvent.TOOL_RESULT, 'tool': tool_name, 'result': tool_result})}\n\n"

    async with httpx.AsyncClient(timeout=120.0) as client:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        tool_summary = ""
        if tool_result and tool_result.get("success"):
            if isinstance(tool_result.get("result"), str):
                tool_summary = f"\n\nTool result: {tool_result['result'][:1000]}"
            else:
                tool_summary = "\n\nTool executed successfully."
        elif tool_result:
            tool_summary = f"\n\nTool returned: {tool_result.get('error', 'unknown error')}"

        user_content = f"{query}{tool_summary}" if tool_summary else query
        for h in history:
            msgs.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        msgs.append({"role": "user", "content": user_content})

        if provider == "ollama":
            async for chunk in _stream_ollama_raw(client, endpoint, model, msgs):
                yield f"data: {json.dumps({'type': _AgenticEvent.TEXT, 'content': chunk})}\n\n"
        elif provider == "lmstudio":
            async for chunk in _stream_lmstudio_raw(client, endpoint, model, msgs):
                yield f"data: {json.dumps({'type': _AgenticEvent.TEXT, 'content': chunk})}\n\n"

    yield f"data: {json.dumps({'type': _AgenticEvent.DONE})}\n\n"


async def _stream_ollama_raw(client, endpoint, model, messages) -> AsyncGenerator[str, None]:
    async with client.stream(
        "POST", f"{endpoint}/api/chat", json={"model": model, "messages": messages, "stream": True}, timeout=120
    ) as r:
        async for line in r.aiter_lines():
            if line:
                try:
                    data = json.loads(line)
                    yield data.get("message", {}).get("content", "")
                except json.JSONDecodeError:
                    pass


async def _stream_lmstudio_raw(client, endpoint, model, messages) -> AsyncGenerator[str, None]:
    async with client.stream(
        "POST",
        f"{endpoint}/v1/chat/completions",
        json={"messages": messages, "model": model, "temperature": 0.7, "stream": True},
        timeout=120,
    ) as r:
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                chunk = line[6:]
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                    yield data["choices"][0].get("delta", {}).get("content", "")
                except json.JSONDecodeError:
                    pass


async def _stream_ollama(client, endpoint, model, messages):
    async with client.stream(
        "POST", f"{endpoint}/api/chat", json={"model": model, "messages": messages, "stream": True}, timeout=120
    ) as r:
        async for line in r.aiter_lines():
            if line:
                import json as _json

                try:
                    data = _json.loads(line)
                    yield data.get("message", {}).get("content", "")
                except:
                    pass


async def _stream_lmstudio(client, endpoint, model, messages):
    async with client.stream(
        "POST",
        f"{endpoint}/v1/chat/completions",
        json={"messages": messages, "model": model, "temperature": 0.7, "stream": True},
        timeout=120,
    ) as r:
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                chunk = line[6:]
                if chunk == "[DONE]":
                    break
                import json as _json

                try:
                    data = _json.loads(chunk)
                    yield data["choices"][0].get("delta", {}).get("content", "")
                except:
                    pass

    @app.get("/api/v1/diagnostics")
    async def diagnostics():
        import time

        try:
            import psutil

            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            try:
                disk = psutil.disk_usage("/").percent
            except:
                disk = 0
        except ImportError:
            cpu = mem = disk = 0
        return {
            "success": True,
            "backend": {"port": 10807, "status": "running", "uptime": time.time() - _start_time},
            "system": {"cpu_percent": cpu, "memory_percent": mem, "disk_percent": disk},
            "tools": {"total": 0},
            "cua_status": {"tesseract_available": False, "window_found": False},
        }

    @app.post("/api/docker/recover")
    async def recover_docker():
        from dockermcp.docker_context import triple_kill_docker

        return triple_kill_docker()
