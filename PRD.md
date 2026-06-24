# DockerMCP - Product Requirements Document (PRD)

**Version**: 3.5.0
**Status**: Active

## 1. Overview

DockerMCP is a FastMCP 3.4+ server that provides a comprehensive interface for managing Docker containers, images, networks, volumes, and Compose. It features a React web dashboard, agentic AI chat with tool execution, Prefab UI cards, container health analysis, image comparison, backup/restore tools, and a Tauri NSIS desktop installer.

## 2. Objectives

- Provide a unified MCP tool surface for all Docker operations
- Deliver a SOTA React web dashboard (Vite + Tailwind + Zustand)
- Offer AI-assisted chat with natural-language Docker management
- Support local LLMs (Ollama, LM Studio) for offline operation
- Ship as a single NSIS installer with embedded Python backend
- Provide Docker backup/restore for noob-friendly data safety

## 3. Features

### 3.1 Core MCP Tools

- **Container Management**: Create, start, stop, restart, remove, exec, logs, inspect
- **Image Management**: List, pull, build, tag, push, prune, search, compare
- **Network Management**: List, create, connect, disconnect, prune
- **Volume Management**: List, create, inspect, prune, backup/restore
- **Compose Management**: List projects, ps, up/down, logs, build, config, debug, analyze YAML

### 3.2 Web Dashboard

- **Dashboard**: Container/image counts, daemon health, system info, restart Docker button
- **Containers**: Live listing with all states
- **Images**: Listing with tags and sizes
- **Compose**: Project list, container per-project view, up/down toggles, config, logs, file analysis
- **AI Chat**: Personality selection (Expert/SRE/Beginner), streaming, tool mode with expandable tool call cards, provider discovery, per-chat model override
- **MCP Tools**: Dynamic tool list discovery
- **Event Logs**: Ring-buffer query, filter, export
- **Settings**: LLM provider glom-on (Ollama/LM Studio), model picker, save
- **Help**: About, Architecture, Usage, Docker info tabs

### 3.3 AI / Agentic Features

- **Provider auto-discovery**: Probes Ollama (:11434) and LM Studio (:1234) for available models
- **Agentic chat mode**: SSE streaming with interleaved tool execution — `tool_call` + `tool_result` events rendered as expandable cards
- **`agentic_workflow`**: Multi-step workflows — deploy_compose (up + health + rollback suggestion), cleanup (prune images/volumes/networks), diagnose (states + logs + system + suggestions), rollback

### 3.4 Prefab UI Cards

- `docker_containers_card` — Container inventory
- `docker_images_card` — Image inventory
- `docker_desktop_status_card` — Daemon health
- `docker_system_info_card` — Engine info

### 3.5 Docker Backup & Restore

- **`save_image`/`load_image`**: Export/import images as .tar
- **`backup_volume`/`restore_volume`**: Volume data as .tar.gz
- **`export_compose`**: Full project archive (YAML + container list + images)

### 3.6 Analysis Tools

- **`image_compare`**: Diff two images (layers, env, entrypoint, cmd, ports, labels, workdir, user)
- **`container_analyze`**: Restart counts, exit codes, log error patterns, resource limits, recommendations
- **Compose file analysis**: Parse YAML → services, images, volumes, networks, ports, dependencies

### 3.7 Compose File Analysis

- Parse `docker-compose.yml` YAML → extract services, images, volumes, networks, ports, dependencies, build contexts, healthchecks
- Accessible via `POST /api/compose/analyze` and compose frontend
- Tauri file dialog for file picking (browser fallback via `<input type="file">`)

### 3.8 Docker Desktop Management

- `docker_desktop_status` — Health check with hang detection, inventory, disk usage
- `docker_daemon_recover` — Triple-kill Docker Desktop + backend + vpnkit
- `docker_daemon_restart` — Graceful daemon restart
- `docker_desktop_update` — Fix update elevation errors
- Restart Docker button on dashboard

### 3.9 Monitoring Stack

- Prometheus (metrics), Grafana (dashboards), Loki (logs), Promtail, cAdvisor, Node Exporter
- Per-container resource usage analytics

## 4. Technical Architecture

### 4.1 Stack

| Layer | Technology |
|-------|-----------|
| MCP Framework | FastMCP 3.4+ |
| Python Backend | FastAPI + uvicorn |
| Frontend | React 19, Vite, Tailwind, Zustand, Lucide |
| Desktop | Tauri 2.0 + PyInstaller (NSIS installer) |
| Local LLM | Ollama (:11434), LM Studio (:1234) |
| Backup | docker save/load, volume tar, compose export |

### 4.2 Ports

| Service | Port |
|---------|------|
| Frontend (Vite dev) | 10806 |
| Backend (FastAPI + MCP HTTP) | 10807 |
| Tauri WebView | Embedded (tauri://localhost) |

### 4.3 Transport

- **MCP stdio**: Default for Claude Desktop
- **MCP HTTP**: `/mcp` endpoint on :10807 for streamable HTTP
- **REST**: `/api/*` endpoints for the web dashboard

## 5. Future Roadmap

### 5.1 Short-term
- Per-conversation model override in chat compose box
- Auto-refresh compose page via SSE
- Enhanced container stats with trend charts

### 5.2 Medium-term
- Swarm mode support
- Kubernetes integration
- Multi-host monitoring

### 5.3 Long-term
- Self-healing infrastructure with predictive failure analysis
- ML-based resource optimization
- Automated remediation workflows
