# docker-mcp

FastMCP 3.5 Docker control plane — containers, images, volumes, networks, Compose, daemon recovery, AI chat, backup/restore, image comparison, container analysis, React web dashboard.

## Quick start

```powershell
uv sync
.\start.ps1       # Opens http://127.0.0.1:10806
just check         # ruff + biome
just mcpb-pack     # Build MCPB bundle
just build-native  # Tauri NSIS installer
```

## Ports

- Frontend (Vite): 10806
- Backend (API / MCP HTTP): 10807

## Key modules

- `src/dockermcp/` — MCP tools, mcp_instance.py, fleet_surface.py
- `src/docker_mcp/` — web bridge, sampling, activity log, LLM glom
- `src/customization/server.py` — uvicorn ASGI app
- `native/` — Tauri 2 + PyInstaller sidecar
- `manifest.json` — MCPB v0.2 (repo root)

## CORS

Both src/server.py and src/dockermcp/api/app.py use the fleet standard CORS regex
covering Tailscale *.ts.net, LAN IPs, localhost, and tauri://localhost.
