# MCP tools (summary)

Full catalog is dynamic — use the `list_tools` MCP call or the web **MCP Tools** page.

## Docker Desktop

| Tool | Purpose |
|------|---------|
| `docker_desktop_status` | Health, hang detection, recent images/containers |
| `docker_daemon_recover` | Emergency recovery |
| `docker_daemon_restart` | Graceful restart |
| `docker_desktop_update` | Update / elevation fixes |

## Prefab (fleet UI cards)

| Tool | Purpose |
|------|---------|
| `docker_containers_card` | Container inventory card |
| `docker_desktop_status_card` | Daemon status card |
| `docker_system_info_card` | Engine stats card |

## Agentic

| Tool | Purpose |
|------|---------|
| `agentic_container_workflow` | Multi-step workflows via FastMCP 3.3 sampling |

Requires a sampling-capable client and `DOCKER_MCP_SAMPLING_*` or Ollama on localhost.

## Core areas

- **Containers**: `list_containers`, lifecycle, logs, exec, stats, …
- **Images**: `list_images`, pull, tag, prune, …
- **Networks / volumes / system / workflows**: see MCP `tools/list`

## Prompts

- `docker_deploy_stack`
- `docker_daemon_health_check`
