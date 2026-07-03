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

## Key modules

- `src/dockermcp/` — MCP tools, `mcp_instance.py`, `fleet_surface.py`
- `src/docker_mcp/` — web bridge, sampling, activity log, LLM glom
- `src/customization/server.py` — uvicorn ASGI `app`
- `native/` — Tauri 2 + PyInstaller sidecar
- `manifest.json` — MCPB v0.2 (repo root)
