# docker-mcp

FastMCP **3.3** server for Docker Desktop and engine operations — containers, images, networks, volumes, daemon recovery, **sampling**, **prefab UI**, **agentic workflows**, and a fleet **web_sota** dashboard.

## Preview

| Dashboard | Event logs |
|-----------|------------|
| Web UI at http://127.0.0.1:10806 (dev) | `/logs` — tail, filter, export |

Native **Tauri** installer bundles the UI + API bridge (port **10807**). After `just build-native`:

- `native\target\release\bundle\nsis\Docker MCP_3.3.0_x64-setup.exe`
- `native\target\release\bundle\msi\Docker MCP_3.3.0_x64_en-US.msi`

## Features

- Docker Desktop health, hang detection, recovery, and restart tools
- Full container / image / network / volume / compose tool surface
- **Prefab cards** for container lists, daemon status, and system info
- **MCP prompts** and `resource://docker-mcp/skills`
- **Agentic workflows** via FastMCP 3.3 sampling (Ollama / LM Studio)
- Web dashboard: dashboard, containers, images, MCP tools, chat, settings (LLM glom-on), event logs

## Quick install

1. Download `docker-mcp-v3.3.0.mcpb` from [Releases](https://github.com/sandraschi/docker-mcp/releases/latest)
2. Drag the file onto Claude Desktop (or Settings → MCP → Install from file)

## Quick start (developers)

```powershell
git clone https://github.com/sandraschi/docker-mcp
cd docker-mcp
uv sync
.\start.ps1
```

Opens the web UI at http://127.0.0.1:10806 (API bridge on **10807**).

## What you can do

- “Check if Docker Desktop is hung and recover the daemon.”
- “List all running containers and show resource usage.”
- “Deploy my compose stack and verify every service is healthy.”

## Documentation

| Doc | Contents |
|-----|----------|
| [INSTALL.md](INSTALL.md) | All install paths, prerequisites, Tauri installer |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Environment variables |
| [docs/TOOLS.md](docs/TOOLS.md) | MCP tool reference |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local dev, just recipes, MCPB, native build |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues |

## Requirements

- Docker Desktop or Docker Engine
- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) (dev / manual install)
- **Node.js 20+** (webapp / MCPB CLI)
- **Rust + Cargo** (Tauri native build only)

## License

MIT — see [LICENSE](LICENSE).
