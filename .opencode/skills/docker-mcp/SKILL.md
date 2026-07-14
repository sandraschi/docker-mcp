# docker-mcp

FastMCP 3.5 Docker control plane. Provides tools for containers, images, volumes, networks, Compose, and daemon recovery.

## Key tools

- `container_ops`: CRUD, logs, stats, exec, inspect, health analysis
- `image_ops`: list, pull, build, tag, push, prune, search, compare
- `compose_ops`: compose_up, compose_down, compose_ps, compose_logs, compose_config
- `volume_ops`: create, list, remove, prune
- `network_ops`: create, inspect, list, remove, connect, disconnect
- `docker_desktop`: status, daemon_recover, daemon_restart, update
- `agentic_workflow`: deploy, cleanup, diagnose, rollback
- `docker_backup`: save/load image, backup/restore volume, export compose

## Ports

- Web UI: 10806 (Vite dev), 10807 (API/MCP HTTP)
- Backend: FastAPI bridge on 10807
