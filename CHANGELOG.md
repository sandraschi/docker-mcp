# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Docker Desktop Management Tools (NEW)

**4 New Native MCP Tools for Docker Desktop Daemon Management:**

- **`docker_desktop_status(autofix: bool)`** — Comprehensive health check with hang detection
  - Daemon responsiveness check with 5-second timeout
  - Last 10 built images (name, size, creation date)
  - Last 10 containers (name, status, ports, creation date)
  - Running vs stopped container summary
  - Disk usage breakdown (images, containers, volumes)
  - Docker Desktop resource configuration (memory, CPU, swap)
  - Issue detection and recommendations
  - Optional auto-recovery from hanging daemon (with `autofix=True`)
  - Full async/await with `asyncio.wait_for()` timeout

- **`docker_daemon_recover()`** — Emergency daemon recovery
  - Kill hung Docker processes (Docker Desktop, com.docker.backend, vpnkit)
  - Graceful shutdown (3-second grace period)
  - Restart Docker Desktop
  - Verify responsiveness (5 attempts with 2-second delays)
  - Structured error reporting
  - Recommendations for persistent issues

- **`docker_daemon_restart()`** — Graceful daemon restart
  - Start Docker Desktop without killing hung processes
  - Wait for startup (8 seconds)
  - Verify responsiveness (5 attempts)
  - Return restart status and responsiveness

- **`docker_desktop_update(full_wipe: bool)`** — Fix update elevation errors
  - Stop Docker Desktop gracefully
  - Clear update temp folder (`%LOCALAPPDATA%\Temp\DockerDesktopUpdates`)
  - Optional full data wipe (clears `%APPDATA%\Docker` and `%LOCALAPPDATA%\Docker`)
  - Restart Docker Desktop
  - Verify startup (10 attempts)
  - Prompt for Settings > Check for Updates

**Implementation Details:**
- Location: `src/dockermcp/tools/desktop/` (3 modules)
  - `desktop_status.py` (18.9KB) — Status checking with hang detection
  - `desktop_recovery.py` (8.9KB) — Recovery and restart procedures
  - `desktop_update.py` (8.1KB) — Update elevation error fixes
- Full async/await with `asyncio.create_subprocess_exec()` and `asyncio.wait_for()`
- Structured error handling returning `ToolResult` objects
- Timeout-based hang detection (5-second command timeout)
- JSON logging context for MCP framework
- Conditional imports (graceful failure on non-Windows systems)
- Registered in `src/dockermcp/tools/__init__.py` with other tool modules

### Added - Infrastructure Updates

- Updated FastMCP version requirement to 3.1+ (was 2.13+)
- Updated Python requirement to 3.12+ (was 3.8+)
- New `tools/desktop/` subdirectory for Desktop management tools
- Enhanced error handling throughout desktop tools
- Timeout detection for daemon hang diagnosis

### Changed

- README.md refreshed with Docker Desktop management section
- Project structure updated to include `tools/desktop/` module
- FastMCP version bumped to 3.1+ in badges and documentation
- Python version requirement updated to 3.12+

### Previous Changes

GitHub Actions CI/CD workflow for automated testing and deployment
Dockerfile for containerizing the application
docker-compose.yml for local development with monitoring stack
Comprehensive documentation for CI/CD and deployment
Automated release process with semantic versioning
Code coverage reporting with Codecov
Health check endpoint at `/health`
Interactive API documentation at `/docs` and `/redoc`
Structured JSON logging for all application logs
Test infrastructure with unit, integration, and e2e test directories

## [0.1.0] - 2025-09-11 - Initial Release

### Features

- Initial project setup
- Basic Docker MCP server implementation
- Container management tools
