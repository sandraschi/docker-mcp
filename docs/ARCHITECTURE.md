# Architecture

```
                  docker-mcp
     ┌─────────────────────────────────────────┐
     │  FastMCP        FastAPI       React 19   │
     │  MCP Tools      REST API      Vite       │
     │  stdio/HTTP     :10807        Tailwind   │
     └─────────────────────────────────────────┘
            │                     │
    ┌───────┴────────┐    ┌───────┴────────┐
    │ Docker Engine  │    │ Ollama/LM      │
    │ (Desktop/CE)   │    │ Studio (LLM)   │
    └────────────────┘    └────────────────┘
```

## Transports

| Mode | Protocol | Port | Usage |
|------|----------|------|-------|
| MCP stdio | stdin/stdout | — | Claude Desktop |
| MCP HTTP | `GET /mcp` SSE | 10807 | Streamable HTTP |
| REST API | `/api/*` | 10807 | Web dashboard |

## Modules

| Module | Role |
|--------|------|
| `src/dockermcp/` | MCP tools, MCP instance, fleet surface |
| `src/docker_mcp/` | FastAPI web app, chat, activity log, LLM glom |
| `src/customization/` | uvicorn ASGI entry point |
| `web_sota/` | React SPA (Vite + Tailwind + Zustand) |
| `native/` | Tauri 2.0 + PyInstaller wrapper |
| `scripts/` | CUA smoke test, build helpers |

## REST API

Base: `http://127.0.0.1:10807/api`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server health (access-log silenced) |
| `/docker/status` | GET | Daemon version (access-log silenced) |
| `/tools` | GET | MCP tool catalog + JSON Schema |
| `/tools/{name}` | GET | One tool schema |
| `/tools/{name}` | POST | Invoke tool (`arguments`, `confirm`) |
| `/dashboard` | GET | Aggregate: containers + images + system |
| `/containers` | GET | All container states |
| `/containers/{id}` | GET | Inspect |
| `/containers/{id}/start` | POST | Start |
| `/containers/{id}/stop` | POST | Stop |
| `/containers/{id}/restart` | POST | Restart |
| `/images` | GET | All images |
| `/images/inspect` | GET | Image inspect (`?ref=`) |
| `/volumes` | GET | Named volumes |
| `/volumes/{name}` | GET | Volume inspect |
| `/networks` | GET | Networks |
| `/networks/{id}` | GET | Network inspect |
| `/system` | GET | Engine info (no `df()`) |
| `/disk` | GET | `docker system df` (slow; dashboard loads in background) |
| `/compose/projects` | GET | Compose projects |
| `/compose/ps` | GET | Compose container states |
| `/compose/up` | POST | Start services |
| `/compose/down` | POST | Stop services |
| `/compose/logs` | GET | Compose logs |
| `/compose/config` | GET | Render compose config |
| `/compose/analyze` | POST | Parse docker-compose.yml |
| `/chat` | POST | LLM proxy |
| `/llm/providers` | GET | Discover LLMs |
| `/logs` | GET/DELETE | Event log |
| `/v1/diagnostics` | GET | CUA diagnostics |
| `/docker/recover` | POST | Triple-kill daemon |
