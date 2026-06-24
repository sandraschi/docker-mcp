
## [3.5.0] - 2026-06-24 (Session 2)

### Added
- **Provider auto-discovery in chat settings**: Settings panel calls `GET /api/llm/providers` on open, shows reachable status dot, model dropdown populated from selected provider's models. Fallback to text input when no providers found.
- **Agentic chat mode (`mode: "agentic"`)**: Backend streams SSE events (`text`, `tool_call`, `tool_result`, `done`). Frontend renders expandable tool call cards with tool name, params, timing, result preview, and success/failure status.
- **`agentic_workflow` MCP tool**: Four multi-step workflows — `deploy_compose` (up + health check + rollback suggestion), `cleanup` (prune images/volumes/networks in dependency order), `diagnose` (container states + logs + system resources + suggestions), `rollback` (down + remove volumes).
- **`image_compare` MCP tool**: Compare two Docker images — diffs layers (added/removed/shared), environment variables, entrypoint, CMD, exposed ports, labels, working directory, and user.
- **`container_analyze` MCP tool**: Analyze container health — restart count, exit code, recent log error patterns, memory limit, CPU shares, restart policy, port/volume counts, actionable recommendations.
- **`docker_images_card` Prefab tool**: Image inventory as a visual card with total/tagged badges, tag, size, and ID for each image.
- **`docker_backup` MCP tool**: Backup/restore Docker resources — `save_image`/`load_image` (export/import images as .tar), `backup_volume`/`restore_volume` (volume data as .tar.gz), `export_compose` (full project archive: config + container list + images).
- **Compose file analysis**: YAML parser (`compose_analysis.py`) extracts services, images, volumes, networks, ports, dependencies, build contexts, healthchecks. Accessible via `POST /api/compose/analyze` and the compose frontend.
- **Compose REST API**: Six new endpoints — `GET /api/compose/projects`, `GET /api/compose/ps`, `POST /api/compose/up`, `POST /api/compose/down`, `GET /api/compose/logs`, `GET /api/compose/config`.
- **Compose frontend page** (`/compose`): Project list with running/stopped indicators, container per-project view, up/down toggles, config viewer, logs viewer, file picker for external compose file analysis.
- **Tauri file dialog**: `tauri-plugin-dialog` in Cargo.toml and `dialog:allow-open` capability. Compose page uses `@tauri-apps/plugin-dialog`'s `open()` with `.yml`/`.yaml` filter; browser fallback via `<input type="file">` and manual path input.
- **SKILL.md file-based loading**: `fleet_surface.py` now reads `skills/docker-mcp/SKILL.md` at runtime instead of a hardcoded string.
- **Tauri dialog plugin**: `tauri-plugin-dialog` registered in Rust main.rs.

### Fixed
- **Duplicate `/api/llm/providers` route**: Two `@app.get("/api/llm/providers")` definitions in `web.py` — the second (manual probe) shadowed the first (manager-based). Removed the duplicate; kept the manager-based version.
- **Missing `import json` and `AsyncGenerator`**: Added to `web.py` for structured SSE event streaming.

### Changed
- **Version**: 3.3.1-beta → 3.5.0 (`__init__.py`, `manifest.json`, `justfile`)
- **`justfile` `mcpb-pack` recipe**: Uses `{{ver}}` variable instead of hardcoded `v3.3.0`.
- **Image `__init__.py`**: Exports `ImageCompareResult` for schema tooling.

## [3.3.1-beta] - 2026-06-24

### Fixed
- **CSP blocking all WebView fetches**: `"csp": null` in tauri.conf.json → explicit CSP allowing `connect-src http://127.0.0.1:10807`. Tauri 2.0 default CSP blocks all backend connections — this was the root cause of "Failed to fetch" in the installed app. (Documented as fleet pitfall #13 — 45 repos affected.)
- **API_BASE empty in production**: Frontend used relative URLs that resolved to `tauri://localhost/...` instead of `http://127.0.0.1:10807/...`. Now uses absolute URL in production mode.
- **Stale cached backend binary**: `materialize_backend` compared app version stamp to decide whether to re-copy from resources. On rebuild with same version, the old binary persisted. Removed version-caching; always uses fresh resource. (Fleet-wide fix — 11 repos affected.)
- **Missing `app` import**: `customization/server.py` was only 11 lines of path setup — never imported the FastAPI `web_app`. Added `from server import web_app as app`.
- **Relative fetch in tools.tsx**: `fetch('/api/tools')` without API_BASE prefix. Changed to `${API_BASE}/api/tools`.
- **Dashboard error detection**: Only checked HTTP-level fetch errors. Backend returns 200 with `containers_status: "error"` when Docker is down — the error state never triggered. Now checks response body status fields.

### Added
- **Docker triple kill recovery**: `POST /api/docker/recover` endpoint that kills Docker Desktop, com.docker.backend, and vpnkit processes, then restarts Docker Desktop and polls for daemon readiness. (Pattern from DOCKER_WINDOWS_RESILIENCE.md Level 3.)
- **Restart Docker button**: Appears on dashboard when `containers_status === "error"`. Calls the triple kill endpoint.
- **Diagnostics endpoint**: `GET /api/v1/diagnostics` returning backend status, system CPU/memory/disk, tool count.
- **Frontend connection health pattern**: Zustand store with exponential backoff health poll (1s→2s→4s→8s→16s→30s) + Tauri `backend-status` event listener + dynamic topbar indicator + `data-testid` attributes for CUA.
- **Ctrl+Scroll zoom hook**: `useZoom.ts` with {0.8, 1.0, 1.25, 1.5, 2.0, 3.0} levels persisted to localStorage.
- **CUA smoke test**: 9-phase test with pywinauto window find/maximize, OCR WebView bridge verification, nav click-through (4 routes), diagnostics check, and uninstall. Template updated to v3.
- **Help page**: Replaced grid of cards with 4 horizontal tabs: About, Architecture (with ASCII diagram), Usage (quick start, AI command examples, tool categories, troubleshooting), Docker (requirements, daemon hang detection, triple kill, AI optimization, port table).
- **Dashboard hero section**: 3-line "AI-powered Docker management via natural language" description with port info.

### Changed
- `.env` → `.env.example` bundling: `build.ps1` now copies `.env.example` (NOT `.env`) to resources — prevents leaking personal API keys into NSIS installer. First-run copies to `%LOCALAPPDATA%\{identifier}\.env`.
- `cua-smoke.py` v3: Window maximized for consistent nav coordinates, shared window object (avoids PID mismatches).
- Build pipeline: `uv run pyinstaller` → venv pyinstaller (`$Root\.venv\Scripts\pyinstaller.exe`). Global uv tool env lacks project dependencies.

### Removed
- `createDesktopShortcut`/`createStartMenuShortcut` from tauri.conf.json (Tauri 2.0 schema rejects them — they're always shown as NSIS finish page checkboxes).
- Version-based `materialize_backend` caching in backend.rs.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.3.0] - 2026-06-02

### Added

- **FastMCP 3.3** (`fastmcp>=3.3,<4`) with `DockerSamplingHandler` (Ollama / LM Studio), `on_duplicate=replace`.
- **Fleet surface** (`dockermcp/fleet_surface.py`): MCP prompts, `resource://docker-mcp/skills`, prefab tools (`docker_containers_card`, `docker_desktop_status_card`, `docker_system_info_card`).
- **Web dashboard**: `/logs` page and API (`/api/logs`, stats, export); settings with LLM provider glom and model dropdown.
- **MCPB**: Root `manifest.json` v0.2, `assets/prompts/`, `.mcpbignore`; `just mcpb-pack` → `dist/docker-mcp-v3.3.0.mcpb`.
- **Tauri native**: `native/` scaffold, PyInstaller sidecar, `just build-native` (NSIS + MSI installers).
- **Docs**: Fleet-shaped `README.md`, `docs/CONFIGURATION.md`, `docs/DEVELOPMENT.md`, `docs/TOOLS.md`, `docs/TROUBLESHOOTING.md`.
- **Tests**: `tests/test_web_bridge.py` (health + logs smoke).

### Changed

- **Import architecture**: `docker_context.py`, `tool_registration.py`; slim `tools/__init__.py` (fixes circular imports).
- **`start.ps1` / `web_sota/start.ps1`**: Exit unless `/api/health` returns 200 (no false “Backend ready”).
- **`customization/server.py`**: Restored `from server import web_app as app` for uvicorn.
- **Web build**: `vite-env.d.ts`, `@radix-ui/react-switch`, `VITE_API_BASE` for Tauri production.
- **Removed** legacy `mcpb/` subdirectory (canonical packaging at repo root only).

### Fixed

- Dashboard HTTP 500 when backend failed to bind or wrong process held port 10807.
- FastMCP 3.3 constructor: `on_duplicate_tools` → `on_duplicate`.

## [3.2.0] - 2026-03 (prior)

### Added - Docker Desktop Management Tools

**4 native MCP tools for Docker Desktop daemon management:**

- **`docker_desktop_status(autofix: bool)`** — Health check with hang detection, inventory, disk usage, optional auto-recovery.
- **`docker_daemon_recover()`** — Emergency daemon recovery.
- **`docker_daemon_restart()`** — Graceful daemon restart.
- **`docker_desktop_update(full_wipe: bool)`** — Fix update elevation errors.

Implementation: `src/dockermcp/tools/desktop/` (status, recovery, update modules).

### Changed

- FastMCP requirement raised toward 3.x; Python 3.12+.
- README and project structure updates for desktop tools.

### Previous Changes

- GitHub Actions CI/CD, Dockerfile, docker-compose monitoring stack.
- Structured JSON logging, test layout (unit / integration / e2e).

## [0.1.0] - 2025-09-11

### Added

- Initial Docker MCP server and container management tools.


