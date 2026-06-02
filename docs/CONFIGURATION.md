# Configuration

## MCP transport

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | `stdio`, `http`, or `sse` |
| `MCP_HOST` | `127.0.0.1` | HTTP bind address |
| `MCP_PORT` | `10807` | HTTP / web bridge port |
| `MCP_PATH` | `/mcp` | HTTP MCP path |

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
