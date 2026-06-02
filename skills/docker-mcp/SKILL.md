---
name: docker-mcp
description: Docker Desktop and engine MCP — containers, images, networks, daemon recovery, agentic workflows.
---

# Docker-MCP

Use when the user needs Docker container operations, Docker Desktop health, or multi-step deploy workflows.

## Tools (priority order)

1. `docker_desktop_status` / `docker_desktop_status_card` — daemon health first
2. `list_containers` / `docker_containers_card` — inventory
3. `docker_daemon_recover` / `docker_daemon_restart` — only when daemon is hung
4. `agentic_container_workflow` — natural-language multi-step ops (requires sampling client)

## Webapp

- Event logs: `/api/logs` (fleet ring buffer)
- Settings: LLM glom-on via `/api/llm/providers` (Ollama 11434, LM Studio 1234)

## Ports

- MCP HTTP: 10807 (env `MCP_PORT`)
- Web UI: 10806 (Vite dev) or served from 10807 in Tauri release builds
