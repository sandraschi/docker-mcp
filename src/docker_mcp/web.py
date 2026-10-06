import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Literal
from urllib.parse import unquote

import httpx
from docker.errors import APIError, DockerException, ImageNotFound, NotFound
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from fastmcp import FastMCP

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
from .examples_api import register_examples_routes
from .llm.manager import get_llm_manager
from .web_queries import (
    DockerUnavailable,
    container_action_sync,
    container_logs_sync,
    dashboard_sync,
    disk_usage_sync,
    get_fleet_settings,
    image_brief_sync,
    image_history_sync,
    inspect_container_sync,
    inspect_image_sync,
    inspect_network_sync,
    inspect_volume_sync,
    junk_summary_sync,
    list_containers_sync,
    list_images_sync,
    list_networks_sync,
    list_volumes_sync,
    pull_image_sync,
    scan_compose_files_cached,
    set_fleet_root,
    system_info_sync,
)

SortParam = Literal["asc", "desc"]

_DESTRUCTIVE_NAME_MARKERS = ("remove_", "prune_", "delete_", "recover", "update")


def _tool_annotations(tool) -> dict | None:
    ann = getattr(tool, "annotations", None)
    if ann is None:
        return None
    if hasattr(ann, "model_dump"):
        return ann.model_dump()
    if isinstance(ann, dict):
        return ann
    return None


def _tool_needs_confirm(name: str, annotations: dict | None) -> bool:
    if annotations and annotations.get("destructiveHint") is True:
        return True
    lowered = name.lower()
    return any(marker in lowered for marker in _DESTRUCTIVE_NAME_MARKERS)


def _tool_row(tool) -> dict:
    params = (
        tool.parameters if isinstance(getattr(tool, "parameters", None), dict) else {"type": "object", "properties": {}}
    )
    annotations = _tool_annotations(tool)
    tags = getattr(tool, "tags", None) or []
    return {
        "name": tool.name,
        "title": getattr(tool, "title", None),
        "description": (getattr(tool, "description", None) or "").strip(),
        "parameters": params,
        "annotations": annotations,
        "tags": sorted(tags) if tags else [],
        "needs_confirm": _tool_needs_confirm(tool.name, annotations),
    }


def _serialize_tool_result(result):
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    blocks = getattr(result, "content", None) or []
    texts = []
    for block in blocks:
        text = getattr(block, "text", None)
        texts.append(text if text is not None else str(block))
    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except (TypeError, json.JSONDecodeError):
            return {"text": texts[0]}
    return {"text": "\n".join(str(item) for item in texts)}


async def _in_thread(fn, *args, **kwargs):
    """Run blocking docker-py work off the event loop."""
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except DockerUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (NotFound, ImageNotFound) as exc:
        detail = getattr(exc, "explanation", None) or str(exc)
        raise HTTPException(status_code=404, detail=detail) from exc
    except APIError as exc:
        detail = getattr(exc, "explanation", None) or str(exc)
        raise HTTPException(status_code=409, detail=detail) from exc
    except (DockerException, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Docker daemon unavailable: {exc}") from exc


def setup_webapp(app: FastAPI, mcp_app: FastMCP, mcp_http_app=None):
    """Setup standard SOTA web endpoints for Docker-MCP.

    mcp_http_app is the FastMCP Streamable HTTP sub-app (built in server.py so
    its lifespan can be combined there); it is mounted at /mcp here, before the
    "/" StaticFiles UI mount, or POST /mcp falls through to StaticFiles (405).
    """
    import time

    _start_time = time.time()

    ai_router = AIRouter(mcp_app)

    @app.get("/api/health")
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "docker-mcp"}

    @app.get("/api/docker/status")
    async def api_docker_status():
        from dockermcp.docker_context import get_docker_status

        return get_docker_status()

    @app.get("/api/capabilities")
    async def capabilities():
        tools = await mcp_app.list_tools()
        return {
            "service": "docker-mcp",
            "pages": {
                "dashboard": True,
                "containers": True,
                "images": True,
                "volumes": True,
                "networks": True,
                "compose": True,
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
        rows = [_tool_row(tool) for tool in tools]
        rows.sort(key=lambda item: item["name"])
        return {"tools": rows, "count": len(rows)}

    @app.get("/api/tools/{tool_name}")
    async def get_tool(tool_name: str):
        wanted = unquote(tool_name)
        tools = await mcp_app.list_tools()
        tool = next((item for item in tools if item.name == wanted), None)
        if tool is None:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {wanted}")
        return {"tool": _tool_row(tool)}

    @app.post("/api/tools/{tool_name}")
    async def invoke_tool(tool_name: str, payload: dict = Body(default_factory=dict)):
        wanted = unquote(tool_name)
        tools = await mcp_app.list_tools()
        tool = next((item for item in tools if item.name == wanted), None)
        if tool is None:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {wanted}")
        row = _tool_row(tool)
        arguments = payload.get("arguments")
        if arguments is None:
            arguments = {k: v for k, v in payload.items() if k not in ("confirm", "arguments")}
        if not isinstance(arguments, dict):
            raise HTTPException(status_code=400, detail="arguments must be an object")
        if row["needs_confirm"] and not payload.get("confirm"):
            raise HTTPException(status_code=400, detail="Set confirm=true to run this tool")
        try:
            result = await tool.run(arguments)
            log_activity("tool_call", f"web invoke {wanted}", meta={"args": list(arguments.keys())})
            return {"success": True, "tool": wanted, "result": _serialize_tool_result(result)}
        except HTTPException:
            raise
        except Exception as exc:
            log_activity("tool_call", f"web invoke {wanted} failed: {exc}", level="ERROR")
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    async def api_containers(all_states: bool = Query(True, alias="all")):
        result = await _in_thread(list_containers_sync, all_states)
        log_activity("tool_call", "list_containers (web API)")
        return result

    @app.get("/api/containers/{container_id}")
    async def api_container_inspect(container_id: str):
        result = await _in_thread(inspect_container_sync, unquote(container_id))
        log_activity("tool_call", f"inspect_container {container_id[:12]}")
        return result

    @app.get("/api/containers/{container_id}/logs")
    async def api_container_logs(container_id: str, tail: int = Query(200, ge=1, le=2000)):
        result = await _in_thread(container_logs_sync, unquote(container_id), tail)
        return result

    @app.post("/api/containers/{container_id}/start")
    async def api_container_start(container_id: str):
        result = await _in_thread(container_action_sync, unquote(container_id), "start")
        log_activity("tool_call", f"start_container {container_id[:12]}")
        return result

    @app.post("/api/containers/{container_id}/stop")
    async def api_container_stop(container_id: str):
        result = await _in_thread(container_action_sync, unquote(container_id), "stop")
        log_activity("tool_call", f"stop_container {container_id[:12]}")
        return result

    @app.post("/api/containers/{container_id}/restart")
    async def api_container_restart(container_id: str):
        result = await _in_thread(container_action_sync, unquote(container_id), "restart")
        log_activity("tool_call", f"restart_container {container_id[:12]}")
        return result

    register_examples_routes(app, _in_thread)

    @app.get("/api/system")
    async def api_system():
        return await _in_thread(system_info_sync)

    @app.get("/api/disk")
    async def api_disk():
        """Slow docker system df. Dashboard must not wait on this."""
        return await _in_thread(disk_usage_sync)

    @app.get("/api/images")
    async def api_images():
        return await _in_thread(list_images_sync)

    @app.get("/api/images/inspect")
    async def api_image_inspect(ref: str = Query(..., min_length=1)):
        result = await _in_thread(inspect_image_sync, unquote(ref))
        log_activity("tool_call", f"inspect_image {ref[:48]}")
        return result

    @app.get("/api/images/history")
    async def api_image_history(ref: str = Query(..., min_length=1)):
        return await _in_thread(image_history_sync, unquote(ref))

    @app.get("/api/images/brief")
    async def api_image_brief(ref: str = Query(..., min_length=1)):
        result = await _in_thread(image_brief_sync, unquote(ref))
        return result

    @app.post("/api/images/pull")
    async def api_image_pull(payload: dict = Body(...)):
        repository = str(payload.get("repository") or "").strip()
        tag = str(payload.get("tag") or "latest").strip() or "latest"
        if not repository:
            raise HTTPException(status_code=400, detail="repository is required")
        result = await _in_thread(pull_image_sync, repository, tag)
        log_activity("tool_call", f"pull_image {repository}:{tag} -> {result.get('message')}")
        return result

    @app.get("/api/junk")
    async def api_junk():
        result = await _in_thread(junk_summary_sync)
        log_activity("tool_call", "junk summary (web API)")
        return result

    @app.get("/api/settings/fleet")
    async def api_fleet_settings_get():
        return await _in_thread(get_fleet_settings)

    @app.put("/api/settings/fleet")
    async def api_fleet_settings_put(payload: dict = Body(...)):
        result = await _in_thread(set_fleet_root, str(payload.get("fleet_root") or ""))
        log_activity("tool_call", f"fleet_root -> {result.get('fleet_root')}")
        return result

    @app.get("/api/volumes")
    async def api_volumes():
        result = await _in_thread(list_volumes_sync)
        log_activity("tool_call", "list_volumes (web API)")
        return result

    @app.get("/api/volumes/{volume_name}")
    async def api_volume_inspect(volume_name: str):
        result = await _in_thread(inspect_volume_sync, unquote(volume_name))
        log_activity("tool_call", f"inspect_volume {volume_name[:48]}")
        return result

    @app.get("/api/networks")
    async def api_networks():
        result = await _in_thread(list_networks_sync)
        log_activity("tool_call", "list_networks (web API)")
        return result

    @app.get("/api/networks/{network_id}")
    async def api_network_inspect(network_id: str):
        result = await _in_thread(inspect_network_sync, unquote(network_id))
        log_activity("tool_call", f"inspect_network {network_id[:12]}")
        return result

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
            project=payload["project"],
            build=payload.get("build", False),
            detach=payload.get("detach", True),
            project_dir=payload.get("project_dir"),
        )

    @app.post("/api/compose/down")
    async def api_compose_down(payload: dict = Body(...)):
        from dockermcp.tools.compose.compose_management import _compose_down

        return await _compose_down(
            project=payload["project"],
            volumes=payload.get("volumes", False),
            project_dir=payload.get("project_dir"),
        )

    @app.get("/api/compose/files")
    async def api_compose_files(refresh: bool = Query(False)):
        result = await _in_thread(scan_compose_files_cached, refresh)
        log_activity("tool_call", f"compose files scan: {result.get('count', 0)} files")
        return result

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
        from dockermcp.tools.compose.compose_analysis import analyze_compose_file, analyze_compose_text

        file_path = payload.get("file_path", "")
        content = payload.get("content")
        if content:
            result = analyze_compose_text(str(content), file_path=str(file_path or "upload"))
        elif file_path:
            result = analyze_compose_file(file_path)
        else:
            return {"success": False, "error": "file_path or content required"}
        log_activity(
            "tool_call",
            f"compose analyze: {file_path}",
            meta={"service_count": result.get("service_count", 0) if result.get("success") else 0},
        )
        return result

    @app.get("/api/dashboard")
    async def api_dashboard():
        try:
            payload = await _in_thread(dashboard_sync)
            log_activity("tool_call", "dashboard aggregate")
            return payload
        except HTTPException:
            raise
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

    _setup_diagnostics_routes(app, _start_time, mcp_app)

    # MCP Streamable HTTP at exact /mcp (advertised on the dashboard hero).
    # Routes are included directly (not mounted): Starlette Mount("/mcp")
    # only matches "/mcp/..." with trailing slash, so a mount would 405/404
    # clients POSTing the advertised exact path. The sub-app instance comes
    # from server.py (same one whose lifespan is combined into the parent);
    # never build a second one here.
    try:
        if mcp_http_app is None:
            raise RuntimeError("no MCP HTTP sub-app provided by server.py")
        sub_routes = list(getattr(mcp_http_app, "routes", []))
        if not sub_routes:
            raise RuntimeError("MCP HTTP sub-app has no routes")
        for route in sub_routes:
            app.router.routes.append(route)
        log_activity("server", f"MCP Streamable HTTP routes added at /mcp ({len(sub_routes)} routes)")
    except Exception as exc:
        log_activity("server", f"MCP HTTP routes failed: {exc}", level="ERROR")


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
                except Exception:
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
                except Exception:
                    pass


def _setup_diagnostics_routes(app: FastAPI, start_time: float, mcp_app: FastMCP):
    @app.get("/api/v1/diagnostics")
    async def diagnostics():
        import time

        try:
            import psutil

            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            try:
                disk = psutil.disk_usage("/").percent
            except Exception:
                disk = 0
        except ImportError:
            cpu = mem = disk = 0
        from dockermcp.docker_context import get_docker_status

        tools = await mcp_app.list_tools()
        return {
            "success": True,
            "backend": {"port": 10807, "status": "running", "uptime": time.time() - start_time},
            "system": {"cpu_percent": cpu, "memory_percent": mem, "disk_percent": disk},
            "tools": {"total": len(tools)},
            "docker": get_docker_status(),
            "cua_status": {"tesseract_available": False, "window_found": False},
        }

    @app.post("/api/docker/recover")
    async def recover_docker():
        from dockermcp.docker_context import triple_kill_docker

        return triple_kill_docker()
