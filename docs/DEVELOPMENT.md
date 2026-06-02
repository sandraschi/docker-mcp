# Development

## Setup

```powershell
uv sync
cd web_sota
npm install
```

## Run

| Command | Purpose |
|---------|---------|
| `.\start.ps1` | Web UI (10806) + API (10807) |
| `just run` | MCP stdio server |
| `just webapp-dev` | Vite only |
| `just check` | Ruff + Biome |

## MCPB bundle

```powershell
npx @anthropic-ai/mcpb pack . dist/docker-mcp-v3.3.0.mcpb
```

Uses root `manifest.json` and `.mcpbignore` per [mcp-central-docs MCPB standards](https://github.com/sandraschi/mcp-central-docs).

## Tauri native (Windows)

```powershell
just build-native
```

Pipeline: `web_sota` build → PyInstaller sidecar → `npx tauri build`.

Outputs under `native/target/release/bundle/`:

- `nsis/Docker MCP_3.3.0_x64-setup.exe`
- `msi/Docker MCP_3.3.0_x64_en-US.msi`

Prerequisites: Rust (rustup), Node 20+, uv, PyInstaller (installed via uv).

## Fleet surface

Registered in `dockermcp/fleet_surface.py`:

- MCP prompts: `docker_deploy_stack`, `docker_daemon_health_check`
- Resources: `resource://docker-mcp/skills`, `resource://docker-mcp/capabilities`
- Prefab tools: `docker_containers_card`, `docker_desktop_status_card`, `docker_system_info_card`
