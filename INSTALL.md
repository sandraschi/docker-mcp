# Installation

## Prerequisites

- Windows 10/11
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed (`winget install Docker.DockerDesktop`)

Both installers below are prebuilt and attached to every
[release](https://github.com/sandraschi/docker-mcp/releases/latest). You do not need Python,
Node.js, Rust or `just` to use them.

## Option A — MCPB (Claude Desktop)

1. Download `docker-mcp-<version>.mcpb` from the [latest release](https://github.com/sandraschi/docker-mcp/releases/latest)
2. Drag it onto the Claude Desktop window
3. Ask Claude: "List my running containers"

The bundle runs the MCP server over stdio. It is unsigned, so Claude Desktop may ask you to confirm.

## Option B — Desktop app (Windows installer)

1. Download `docker-mcp-<version>-setup.exe` from the [latest release](https://github.com/sandraschi/docker-mcp/releases/latest)
2. Run it. It installs per user (no admin prompt) and is unsigned, so Windows SmartScreen may warn: choose **More info → Run anyway**
3. Launch **Docker MCP** from the Start menu

The app starts its own backend on `127.0.0.1:11240`; it does not collide with a dev stack on 10806/10807.

## Option C — Run from source (developers)

```powershell
git clone https://github.com/sandraschi/docker-mcp
cd docker-mcp
uv sync
.\start.ps1
```

Opens http://127.0.0.1:10806 (frontend) and http://127.0.0.1:10807 (API). Building the `.mcpb` and
the installer yourself (`just mcpb-pack`, `just build-native`) is covered in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Traditional Setup

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
