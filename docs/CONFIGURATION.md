# Configuration

## Fleet repos ("our" vs external images, compose file scan)

| Setting | Default | Description |
|---------|---------|-------------|
| Fleet root | `D:/Dev/repos` | Where your own repos live. Anyone cloning from GitHub points it at their checkout (Settings page → Fleet repositories). |
| `DOCKER_MCP_FLEET_ROOT` | *(empty)* | Env override, wins over the saved setting. |
| Settings file | `~/.docker-mcp/settings.json` | Persists `fleet_root` (`GET/PUT /api/settings/fleet`). |

Used for image provenance matching (`myai-*` → `myai`, …) and the compose-files preload (`GET /api/compose/files`).

## MCP transport

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | `stdio`, `http`, or `sse` |
| `MCP_HOST` | `127.0.0.1` | HTTP bind address |
| `MCP_PORT` | `10807` | HTTP / web bridge port |
| `MCP_PATH` | `/mcp` | HTTP MCP path |

### Installed sidecar (`docker-mcp-backend.exe`) and IDE registration

The installed desktop app runs the sidecar over HTTP (the app spawns it with no flags). An IDE or
Claude Desktop MCP entry runs the **same exe with `--stdio`**:

```json
{ "mcpServers": { "docker-mcp": { "command": "C:\\...\\resources\\docker-mcp-backend.exe", "args": ["--stdio"] } } }
```

`MCP_TRANSPORT=stdio` is equivalent to `--stdio`. In stdio mode logs go to stderr; stdout carries only
MCP JSON-RPC.

### Stdio proxy to a running backend

Before any Docker or tool initialization, a stdio instance probes for an already-running backend and,
if one is healthy, becomes a thin proxy to it (one instance, one activity log, the dashboard sees
every call). A backend is used only if `GET /api/health` returns 200 within 2 s with
`service == "docker-mcp"` and `status == "healthy"`, **and** `POST /mcp` `initialize` returns 200
within 3 s. Anything else (nothing listening, a hung process, another app on the port, a backend
whose `/mcp` is dead) means the stdio instance starts normally on its own.

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_MCP_API_URL` | *(unset)* | Probe only this base URL (e.g. `http://127.0.0.1:11240`) |
| `DOCKER_MCP_NO_PROXY` | *(unset)* | `1` = never proxy, always run standalone |

Without `DOCKER_MCP_API_URL` the probe tries the installed app's backend `127.0.0.1:11240`, then the
dev stack `127.0.0.1:10807`. The probe runs once at startup: if the backend dies mid-session, proxied
calls fail until it returns or the client restarts the stdio process.

## Sampling (FastMCP 3.3)

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_MCP_SAMPLING_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible API (Ollama) |
| `DOCKER_MCP_SAMPLING_MODEL` | `llama3.2` | Model id for sampling |
| `DOCKER_MCP_SAMPLING_API_KEY` | *(empty)* | Optional API key |

## Local LLM glom-on (webapp)

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_MCP_LLM_GLOM` | `1` | Probe Ollama / LM Studio on startup |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama tags endpoint base |
| `LMSTUDIO_BASE_URL` | `http://127.0.0.1:1234` | LM Studio models endpoint base |

## Logs ring buffer

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_MCP_LOG_MAX_ENTRIES` | `2000` | In-memory log capacity |

## Prefab UI

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_MCP_PREFAB_APPS` | `1` | Set `0` to skip registering prefab card tools |

## Webapp (Tauri release build)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | *(empty)* | Set to `http://127.0.0.1:10807` when building `web_sota` for Tauri |
