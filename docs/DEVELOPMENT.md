# Development

Everything here is for contributors. End users download the installer from
[Releases](https://github.com/sandraschi/docker-mcp/releases/latest) and never need `just`, Python or Node
(see the [README](../README.md)).

## Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Git | clone | `winget install Git.Git` |
| uv | Python env + runner | `winget install astral-sh.uv` |
| Node.js 20+ | webapp, `mcpb` CLI | `winget install OpenJS.NodeJS` |
| Bun | Biome / tsc runner used by hooks | `winget install Oven-sh.Bun` |
| just | recipe runner | `winget install Casey.Just` |
| Rust (rustup) + MSVC build tools | Tauri installer build only | `winget install Rustlang.Rustup` |
| Docker Desktop | the thing being controlled | `winget install Docker.DockerDesktop` |

## Setup and run from source

```powershell
git clone https://github.com/sandraschi/docker-mcp
cd docker-mcp
uv sync
cd web_sota; npm install; cd ..
just bootstrap      # deps + pre-commit hooks (ruff AND biome run on every commit)
.\start.ps1         # web UI :10806 + API/MCP bridge :10807
```

| Command | Purpose |
|---------|---------|
| `.\start.ps1` | Dev stack: web UI 10806, API / MCP HTTP 10807 |
| `just run` | MCP server over stdio |
| `just webapp-dev` | Vite only |
| `just check` / `just fix` | ruff + biome / autofix |
| `just test` | pytest (includes `tests/test_daemon_probe.py`) |
| `just e2e` | Playwright smoke (start the backend first) |

## Ports

| Port | What |
|------|------|
| 10806 / 10807 | Dev web UI / dev backend (`start.ps1`) |
| 11239 (reserved) / **11240** | Installed desktop app (`docker-mcp-native`): **operator backend** on 11240. Never the dev ports, so the app and a dev stack run side by side. |

Claim new ports with `mcp-central-docs/fleet-gate/claim_ports.py`; never hardcode one.

## Transport contract

The sidecar (`run_server.py`) follows the arxiv-mcp contract:

- **No flags:** HTTP (web bridge + REST + `/mcp`). This is how the desktop app spawns it.
- **`--stdio`** or `MCP_TRANSPORT=stdio`: MCP over stdio, no web bridge. This is what IDE entries run.
- **stdout carries JSON-RPC only; all logging goes to stderr.** `scripts/smoke_stdio.py` enforces it.
- Before any Docker/tool init a stdio instance proxies to a healthy running backend
  (`docker_mcp/daemon_probe.py`; see [CONFIGURATION.md](CONFIGURATION.md)). Opt out: `DOCKER_MCP_NO_PROXY=1`.

```powershell
uv run python scripts/smoke_stdio.py uv run python run_server.py --stdio   # expects: initialize ok, 43 tools
```

## Building the release artifacts

Releases ship **both** artifacts ([release standard](https://github.com/sandraschi/mcp-central-docs/blob/main/standards/RELEASE_TIERS.md)).

```powershell
just build-native     # Tauri NSIS installer, full pipeline
just mcpb-pack        # .mcpb for Claude Desktop
just cua-nsis-test    # REQUIRED before a release: installs the real installer, drives the UI, uninstalls
```

**`just build-native`** (`native/build.ps1`): `tsc` + Vite build with `VITE_API_BASE` baked to the operator port,
PyInstaller from the project venv (`.venv\Scripts\pyinstaller.exe`, never `uv run pyinstaller`), frozen-backend
smoke tests (HTTP `/api/health` + `/api/v1/diagnostics`, **and** a stdio MCP handshake), then Tauri/NSIS.
Only `.env.example` is bundled, never `.env`. Output: `dist/Docker MCP_<ver>_x64-setup.exe`.

**`just mcpb-pack`** (`mcpb/pack.ps1`): stages `src/dockermcp` + `src/docker_mcp` into `mcpb/src`, runs import isolation,
AST, pollution and launch checks, then packs. Output: `dist/schip-mcp-docker-v<ver>.mcpb` (the manifest name).

**`just cua-nsis-test`** installs the built installer on **this machine**, launches it, walks the UI with pywinauto and
checks the backend received the requests, then uninstalls. It takes over the desktop, so run it when you are not
using the machine. It writes `cua-reports/cua-result.json`, which the release gate binds to the installer's SHA-256.

### Publishing a release

```powershell
$v = "3.5.0"   # == mcpb/manifest.json == native/tauri.conf.json == tag without the "v"
Copy-Item "dist\Docker MCP_${v}_x64-setup.exe" "dist\docker-mcp-$v-setup.exe"
Copy-Item "dist\schip-mcp-docker-v$v.mcpb"     "dist\docker-mcp-$v.mcpb"
pwsh ..\mcp-central-docs\scripts\check-release-gate.ps1 -Repo . -Local -Version $v   # must pass first
gh release create "v$v" "dist\docker-mcp-$v.mcpb" "dist\docker-mcp-$v-setup.exe" --title "Docker MCP $v" --notes "..."
pwsh ..\mcp-central-docs\scripts\check-release-gate.ps1 -Repo . -Version $v          # verify what is published
```

Installers are unsigned (SmartScreen: More info > Run anyway). Tag at the commit you built from, on a clean tree.

## The justfile

Only these recipes matter for this repo: `bootstrap`, `check`, `fix`, `run`, `test`, `webapp-dev`, `e2e`,
`mcpb-pack`, `build-native`, `cua-nsis-test`, `clean`. The rest (`gpu-*`, `invokeai-up`, `zombie*`, `fleet-*`,
`tauri-audit`, `tauri-fix`, `emojibuster`, `docker-build`, `up`/`down`) are fleet-wide helper recipes copied into every
repo from a template; they do not build or test docker-mcp. `just` with no arguments opens a recipe browser.

## Fleet surface

Registered in `dockermcp/fleet_surface.py`:

- MCP prompts: `docker_deploy_stack`, `docker_daemon_health_check`
- Resources: `resource://docker-mcp/skills`, `resource://docker-mcp/capabilities`
- Prefab tools: `docker_containers_card`, `docker_desktop_status_card`, `docker_system_info_card`
