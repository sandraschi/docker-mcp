# MCP Server

## Quick Config

### Claude Desktop

```json
{
  "mcpServers": {
    "docker-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:/Dev/repos/docker-mcp", "python", "-m", "dockermcp"],
      "env": { "PYTHONPATH": "src" }
    }
  }
}
```

Or install the `.mcpb` bundle: `just mcpb-pack` → drag onto Claude Desktop.

### Cursor

Settings → MCP → Add server:
```
Name: docker-mcp
Type: stdio
Command: uv run --directory D:/Dev/repos/docker-mcp python -m dockermcp
```

### HTTP (streamable)

```
URL: http://127.0.0.1:10807/mcp
Transport: streamable HTTP (SSE)
```

## Tool Catalog

### Compose

| Tool | Purpose |
|------|---------|
| `compose_operations` | CRUD: list, ps, up, down, logs, build, config, debug |
| `agentic_workflow("deploy_compose")` | Up + health check + rollback suggestion |
| `agentic_workflow("cleanup")` | Prune images/volumes/networks in order |
| `agentic_workflow("diagnose")` | States + logs + system resources + suggestions |
| `agentic_workflow("rollback")` | Down + remove volumes |

### Images

| Tool | Purpose |
|------|---------|
| `list_images` | All images with tags, sizes, OS, arch |
| `pull_image` | Pull from registry |
| `build_image` | Build from Dockerfile |
| `tag_image` | Tag an image |
| `push_image` | Push to registry |
| `prune_images` | Remove dangling (dry-run supported) |
| `search_images` | Docker Hub search |
| `get_image_history` | Layer history |
| `image_compare(a, b)` | Diff layers, env, entrypoint, cmd, ports, labels, workdir, user |

### Containers

| Tool | Purpose |
|------|---------|
| `list_containers` | All containers with states |
| `manage_container` | Create, start, stop, restart, remove |
| `get_container_logs` | Logs with tail/filters |
| `execute_in_container` | Run commands |
| `get_container_stats` | CPU, memory, network, block IO |
| `inspect_container` | Full container config |
| `container_analyze(id)` | Restart count, exit codes, log errors, recommendations |

### Networks, Volumes, System

| Tool | Purpose |
|------|---------|
| `list_networks` / `create_network` / `remove_network` | Network CRUD |
| `list_volumes` / `create_volume` / `remove_volume` / `prune_volumes` | Volume CRUD |
| `get_system_info` | Docker engine info |
| `get_disk_usage` | Docker disk usage |
| `get_container_resources` | Resource limits |

### Backup & Restore

| Tool | Purpose |
|------|---------|
| `docker_backup("save_image")` | Export image(s) to .tar |
| `docker_backup("load_image")` | Import images from .tar |
| `docker_backup("backup_volume")` | Volume data to .tar.gz |
| `docker_backup("restore_volume")` | Restore volume from .tar.gz |
| `docker_backup("export_compose")` | Full project: config + containers + images |

### Docker Desktop

| Tool | Purpose |
|------|---------|
| `docker_desktop_status` | Health check + hang detection + auto-recovery |
| `docker_daemon_recover` | Triple-kill Docker Desktop + backend + vpnkit |
| `docker_daemon_restart` | Graceful daemon restart |
| `docker_desktop_update` | Fix update elevation errors |

### Agentic / Sampling

| Tool | Purpose | Requires |
|------|---------|----------|
| `agentic_container_workflow` | Autonomous multi-step orchestration via `ctx.sample()` | Sampling-capable client + Ollama/LM Studio |
| `agentic_workflow` | Deterministic multi-step: deploy, cleanup, diagnose, rollback | Nothing (uses Docker SDK directly) |

### Prefab Cards (in-chat rich UI)

| Tool | Content |
|------|---------|
| `docker_containers_card` | Container inventory with total/running badges |
| `docker_images_card` | Image inventory with tagged/total badges |
| `docker_desktop_status_card` | Daemon health with autofix option |
| `docker_system_info_card` | Engine version, CPU cores, memory |

### Web API (REST)

The server also exposes a REST API at `http://127.0.0.1:10807/api` for the web dashboard.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the full endpoint list.

## Prompts

| Prompt | Purpose |
|--------|---------|
| `docker_deploy_stack` | Deploy a multi-container stack with dependency ordering |
| `docker_daemon_health_check` | Daemon diagnostics and recovery workflow |

## Resources

| URI | Content |
|-----|---------|
| `resource://docker-mcp/skills` | When to use docker-mcp, workflow order, ports |
| `resource://docker-mcp/capabilities` | Server capabilities summary |

## Transports

| Mode | Config | When |
|------|--------|------|
| stdio | `command` + `args` in MCP config | Claude Desktop, Cursor |
| HTTP SSE | `url: http://127.0.0.1:10807/mcp` | Remote, browser-based clients |
