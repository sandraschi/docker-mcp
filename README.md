# docker-mcp

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.5-purple.svg)](https://github.com/jlowin/fastmcp)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/sandraschi/docker-mcp/pulls)

FastMCP 3.5 control plane for Docker — containers, images, volumes, networks, Compose, daemon recovery, **AI chat**, **backup/restore**, **image comparison**, **container analysis**, and a React web dashboard.

## Install

1. Download **`docker-mcp-<version>-setup.exe`** from the [latest release](https://github.com/sandraschi/docker-mcp/releases/latest).
2. Run it. Windows may show a SmartScreen warning because the installer is not code-signed:
   choose **More info > Run anyway**.
3. Open **Docker MCP** from the Start menu.

That installs the dashboard and the backend in one go. Nothing else to set up except
[Docker Desktop](https://www.docker.com/products/docker-desktop/), which this controls.

**Only want the Docker tools inside Claude?** The `.mcpb` bundle registers the MCP server in Claude Desktop
but does **not** install the dashboard. Paste this to Claude:

> Install the docker-mcp MCP extension: download `docker-mcp-<version>.mcpb` from
> https://github.com/sandraschi/docker-mcp/releases/latest and open it with Claude Desktop.

More options (other IDEs, manual config, troubleshooting): [INSTALL.md](INSTALL.md).

**Developers:** building from source, the justfile, tests and releasing are in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## What You Can Do

- "List all running containers and show resource usage."
- "Deploy my compose stack and verify every service is healthy."
- "Compare nginx:1.25 and nginx:1.26 — what changed?"
- Dashboard → **Run MCP tools** → pick a tool → fill the form → Run.
- "Analyze container my-app — why is it restarting?"
- "Back up my database volume before the upgrade."

## Feature Overview

| Area | Highlights |
|------|------------|
| **Containers** | CRUD, logs, stats, exec, inspect, health analysis, inline start/stop/restart |
| **Images** | List, pull (freshness check), build, tag, push, prune, search, compare, provenance, upstream brief |
| **Compose** | Projects, up/down, logs, config, YAML file analysis, repo-files preload |
| **Reports** | Global status + cleanup opportunities, Markdown/JSON export |
| **Backup/Restore** | `save/load image`, `backup/restore volume`, `export compose` |
| **Docker Desktop** | Status, hang detection, triple-kill recovery, restart |
| **AI Chat** | SSE streaming, tool execution cards, LLM provider discovery |
| **Agentic** | Deploy, cleanup, diagnose, rollback workflows |
| **Prefab Cards** | Containers, images, daemon status, system info |
| **Web dashboard** | Progressive overview (per-section loading, no global spinner), quick actions (Run MCP tools, Diagnose, Backup, Recover Docker), `/tools` runner, volumes, networks, compose, AI chat, reports with export |

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/TOOLS.md](docs/TOOLS.md) | Full MCP tool reference |
| [docs/COMPOSE.md](docs/COMPOSE.md) | Compose management & file analysis |
| [docs/BACKUP.md](docs/BACKUP.md) | Docker backup & restore guide |
| [docs/CHAT.md](docs/CHAT.md) | AI chat & agentic workflows |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Stack, transport, REST API |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Environment variables |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Build, just recipes, testing |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues |

## Troubleshooting

- **"Virtualization support not detected"**: a crash can reset the BIOS to
  defaults and switch off SVM/VT-x. Check
  `Get-CimInstance Win32_Processor | Select-Object VirtualizationFirmwareEnabled`,
  re-enable SVM Mode in firmware, then restart Docker Desktop.
  Full walkthrough: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Requirements

Windows 10/11 and Docker Desktop (Docker Engine 20.10+). Building from source has its own prerequisites, listed in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## License

MIT
