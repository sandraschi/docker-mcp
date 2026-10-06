# Installation

## Prerequisites

- Windows 10/11
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed (`winget install Docker.DockerDesktop`)

Both installers below are prebuilt and attached to every
[release](https://github.com/sandraschi/docker-mcp/releases/latest). You do not need Python,
Node.js, Rust or `just` to use them.

## Option A — Windows installer (recommended)

1. Download `docker-mcp-<version>-setup.exe` from the [latest release](https://github.com/sandraschi/docker-mcp/releases/latest)
2. Run it. It installs per user (no admin prompt) and is unsigned, so Windows SmartScreen may warn: choose **More info → Run anyway**
3. Launch **Docker MCP** from the Start menu

This installs the dashboard and the backend. The app starts its own backend on `127.0.0.1:11240`; it does not
collide with a dev stack on 10806/10807.

## Option B — Claude Desktop bundle (.mcpb)

The `.mcpb` registers the MCP server in Claude Desktop. It does **not** install the dashboard.

Paste this to Claude:

> Install the docker-mcp MCP extension: download `docker-mcp-<version>.mcpb` from
> https://github.com/sandraschi/docker-mcp/releases/latest and open it with Claude Desktop.

Or do it by hand: download the file from the release and drag it onto the Claude Desktop window.
It is unsigned, so Claude Desktop may ask you to confirm. Then ask Claude: "List my running containers".

## Option C — Other MCP clients (Cursor, Claude Code, ...)

Point the client at the installed sidecar over stdio (installed by Option A):

```json
{ "mcpServers": { "docker-mcp": {
  "command": "C:\\Users\\<you>\\AppData\\Local\\Docker MCP\\resources\\docker-mcp-backend.exe",
  "args": ["--stdio"] } } }
```

If the desktop app is running, this process automatically proxies to it instead of starting a second
instance ([configuration](docs/CONFIGURATION.md)). The path above is where a per-user install puts it;
check it on your machine.

## Developers

Run from source, the justfile, tests, building the installer and `.mcpb`, and releasing:
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Traditional Setup (from source)

If you prefer not to use `just`:

1. Install [Python 3.13+](https://python.org) and [uv](https://docs.astral.sh/uv/)
2. Clone and enter the repo:
   ```powershell
   git clone https://github.com/sandraschi/docker-mcp
   cd docker-mcp
   ```
3. Install dependencies:
   ```powershell
   uv sync --all-extras
   ```
4. Start the server:
   ```powershell
   # stdio mode (for MCP clients like Claude Desktop)
   uv run python -m docker_mcp.server

   # HTTP web bridge (API + optional built UI)
   uv run uvicorn customization.server:app --host 127.0.0.1 --port 10807
   ```
5. Open http://127.0.0.1:10806 (run `cd web_sota; npm run dev` for Vite) or http://127.0.0.1:10807/api/health.

---

## ❓ Troubleshooting

| Issue | Fix |
|---|---|
| `just` not found | Install via `winget install Casey.Just`, `scoop install just`, or `brew install just` |
| Port conflict | Run `just kill-all` to clear fleet ports (10700–11000) |
| Dependencies out of sync | `uv sync --all-extras` |
| Something else | [Open a GitHub issue](https://github.com/sandraschi/docker-mcp/issues) |

---

*See the main [README](README.md) for feature overview and documentation.*
