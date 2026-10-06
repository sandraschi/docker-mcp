# docker-mcp Agent Context

FastMCP 3.4 fleet server. Normative standards: `D:\Dev\repos\mcp-central-docs`.

## Quick ref

```powershell
uv sync
just check
.\start.ps1
just mcpb-pack
just build-native
```

## Ports

- Web UI (Vite): **10806**
- API / MCP HTTP bridge: **10807**
- Installed desktop app (operator) backend: **11240** (`docker-mcp-native`; never the dev ports)

## HTTP daemon + stdio proxy (SOTA_REQUIREMENTS 2.3)

- Stdio entry points (`run_server.py --stdio`, `mcpb/run_server.py`) call
  `docker_mcp.daemon_probe.proxy_if_daemon()` **before** importing `dockermcp.server` (that import
  initializes Docker and registers tools). Healthy daemon found: proxy to it, never a second stack.
- Daemon candidates: `DOCKER_MCP_API_URL`, else `127.0.0.1:11240`, then `127.0.0.1:10807`.
  Opt out: `DOCKER_MCP_NO_PROXY=1`. Health = `/api/health` `{"service":"docker-mcp","status":"healthy"}`
  within 2 s plus a `/mcp` `initialize` within 3 s; a hung or foreign listener is rejected.
- Stdio mode never starts the web bridge (`main(web_bridge=False)`) so it cannot hold 10807.
- stdout is JSON-RPC only; all logging goes to stderr. `scripts/smoke_stdio.py` enforces this.
- Tests: `tests/test_daemon_probe.py`.

## Key modules

- `src/dockermcp/` — MCP tools, `mcp_instance.py`, `fleet_surface.py`
- `src/docker_mcp/` — web bridge, sampling, activity log, LLM glom
- `src/customization/server.py` — uvicorn ASGI `app`
- `native/` — Tauri 2 + PyInstaller sidecar
- `manifest.json` — MCPB v0.2 (repo root)
