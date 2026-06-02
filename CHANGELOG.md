# Changelog

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
