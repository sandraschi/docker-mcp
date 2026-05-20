# docker-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

## Quick Start

```powershell
git clone https://github.com/sandraschi/docker-mcp
cd docker-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:

## FastMCP 3.2.0 server for comprehensive Docker operations

[![FastMCP](https://img.shields.io/badge/FastMCP-3.2.0-blue)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/Python-3.12+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker--blue)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://github.com/sandraschi/dockermcp/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/sandraschi/dockermcp/actions)
[![Docker Image](https://img.shields.io/docker/pulls/sandraschi/dockermcp)](https://hub.docker.com/r/sandraschi/dockermcp)
[![codecov](https://codecov.io/gh/sandraschi/dockermcp/branch/main/graph/badge.svg?token=YOUR-TOKEN)](https://codecov.io/gh/sandraschi/dockermcp)


##  Features

###  Docker Desktop Management (NEW)

Comprehensive Docker Desktop daemon management with native MCP tools:

- **`docker_desktop_status(autofix: bool)`**  Check daemon health with hang detection, list last 10 images/containers, monitor resource allocation, auto-recover from hanging daemon
- **`docker_daemon_recover()`**  Emergency recovery from hung daemon (kill processes, restart, verify responsiveness)
- **`docker_daemon_restart()`**  Graceful daemon restart with verification
- **`docker_desktop_update(full_wipe: bool)`**  Fix elevation errors, clear update temp folders, optional full wipe for reset

**Features:**
- Timeout-based hang detection (5-second timeout)
- Last 10 built images with size and creation date
- Last 10 containers with status, ports, and creation date
- Resource configuration monitoring (memory, CPU, swap)
- Disk usage breakdown
- Issue detection and recommendations
- Full async/await implementation
- Structured error handling with `ToolResult`
- JSON logging context

**Location:** `src/dockermcp/tools/desktop/`

###  Monitoring Stack

DockerMCP includes a comprehensive monitoring stack with the following components:

- **Prometheus**: Metrics collection and alerting (Port: 9091)
- **Grafana**: Visualization and dashboards (Port: 3001)
- **Loki**: Log aggregation (Port: 3101)
- **Promtail**: Log collection
- **cAdvisor**: Container metrics (Port: 8082)
- **Node Exporter**: Host metrics (Port: 9100)
- **Redis**: Caching and metrics storage (Port: 6379)

To start the monitoring stack:

```bash
cd monitoring
docker-compose -f docker-compose-monitoring.yml up -d
```

Access the monitoring interfaces:

- **Grafana**: [http://localhost:3001](http://localhost:3001) (admin/admin)
- **Prometheus**: [http://localhost:9091](http://localhost:9091)
- **Loki**: [http://localhost:3101](http://localhost:3101)
- **cAdvisor**: [http://localhost:8082](http://localhost:8082)

###  Testing

DockerMCP uses a comprehensive testing strategy with the following structure:

```text
tests/
 unit/           # Unit tests for individual components
 integration/    # Integration tests for component interactions
 e2e/            # End-to-end tests for complete workflows
```

To run the tests:

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run with coverage report
pytest --cov=src tests/
```

###  Logging

DockerMCP uses structured JSON logging for better observability:

- All logs are emitted as JSON for easy parsing and analysis
- Includes context information (correlation IDs, request IDs)
- Configurable log levels and output formats
- Automatic log rotation for file output

### State Management (Powered by FastMCP 3.2.0+)

DockerMCP leverages FastMCP 3.2.0+'s built-in state management system \
for all its stateful operations. This provides several key benefits:

- **No External Dependencies**: No Redis or other external services required
- **Consistent State**: All state is managed within the FastMCP runtime
- **TTL Support**: Automatic expiration of temporary state
- **Request Isolation**: Clean separation between different client sessions
- **Efficient Storage**: Optimized for minimal memory footprint

#### Key State Management Features

- Session persistence across requests
- Automatic cleanup of stale data
- Thread-safe operations
- Built-in caching for improved performance

### Core Docker Operations

- **Container Management**: Create, start, stop, restart, and remove containers
- **Image Handling**: Pull, list, tag, and remove Docker images
- **Network Operations**: Manage Docker networks and connections
- **Volume Management**: Handle Docker volumes and storage
- **System Monitoring**: Get Docker system info, version, and disk usage

### Management & Recovery Features

- **Docker Desktop Management**: Native tools for daemon health, recovery, and updates
- **Hang Detection**: Automatic timeout-based detection of unresponsive daemon
- **Auto-Recovery**: Graceful process termination and restart
- **Stack Health Checks**: One-command status of all your stacks
- **Problem Detection**: Diagnose issues before they cause downtime
- **Intelligent Recovery**: Automated fixes for common Docker issues
- **Cross-Platform Support**: Works on both Windows and Linux systems

##  Docker Watchdog

### Features

- **Automatic Recovery**: Automatically restarts Docker daemon if it becomes unresponsive
- **Cross-Platform**: Works on both Windows and Linux systems
- **Configurable**: Adjust check intervals and retry attempts
- **Detailed Logging**: Comprehensive logs for troubleshooting
- **Service Integration**: Runs as a system service (systemd/Linux, Windows Service/Windows)

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+
- FastMCP 3.2.0+

###  Quick Start

Run immediately via `uvx` (no installation needed):
```bash
uvx docker-mcp
```

Or install and run locally via `uv`:
```bash
git clone https://github.com/sandraschi/docker-mcp.git
cd docker-mcp
uv sync
uv run docker-mcp
```

###  Installation Methods

#### Option 1: One-liner via `uvx` (No installation)
```bash
uvx docker-mcp
```
Runs immediately with automatic dependency management.

#### Option 2: Local install via `uv`
```bash
git clone https://github.com/sandraschi/docker-mcp.git
cd docker-mcp
uv sync          # Install dependencies
uv run docker-mcp  # Start server
```

#### Option 3: Claude Desktop Integration
Add to `claude_desktop_config.json`:
```json
"mcpServers": {
  "docker-mcp": {
    "command": "uvx",
    "args": ["docker-mcp"]
  }
}
```

#### Windows

```powershell
# Run as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install\docker-watchdog.ps1
```

#### Linux

```bash
# Install as systemd service
sudo cp install/docker-watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now docker-watchdog
```

### Logs

- **Windows**: `docker_watchdog.log` in the installation directory
- **Linux**: `journalctl -u docker-watchdog -f`

##  CI/CD Pipeline

DockerMCP uses GitHub Actions for CI/CD with the following workflows:

1. **Test**: Runs on every push and pull request
   - Unit tests
   - Integration tests
   - Code coverage reporting

2. **Build and Push**: Runs on push to main and tags
   - Builds Docker image
   - Pushes to Docker Hub
   - Tags with version, branch, and commit SHA

3. **Release**: Creates GitHub releases for tags
   - Generates release notes from CHANGELOG.md
   - Creates GitHub release with artifacts

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DOCKERHUB_USERNAME` | Docker Hub username | Yes | - |
| `DOCKERHUB_TOKEN` | Docker Hub access token | Yes | - |
| `CODECOV_TOKEN` | Codecov upload token | No | - |

##  Project Structure

```text
docker-mcp/
 src/
    dockermcp/
        api/                 # API endpoints and routes
        core/                # Core Docker operations
           containers.py    # Container management
           images.py        # Image handling
           networks.py      # Network management
           system.py        # System operations
           volumes.py       # Volume management
       
        models/              # Data models and schemas
        tools/               # FastMCP 3.2.0+ compatible tools
           containers/      # Container management tools
           desktop/         # Docker Desktop management tools (NEW)
              desktop_status.py      # Status check with hang detection
              desktop_recovery.py    # Daemon recovery & restart
              desktop_update.py      # Update & elevation fixes
           images/          # Image management tools
           networks/        # Network management tools
           system/          # System management tools
           volumes/         # Volume management tools
           workflows/       # Workflow automation tools
       
        utils/               # Utility functions
            json_utils.py    # JSON handling utilities
            process_utils.py # Process management utilities

 tests/                      # Test suite
 docs/                       # Documentation
 examples/                   # Usage examples
```

##  Quick Start

### Using Docker (Recommended)

```bash
docker run -d \
  --name docker-mcp \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  sandraschi/docker-mcp:latest
```

### Using Docker Compose

```bash
git clone https://github.com/sandraschi/docker-mcp.git
cd docker-mcp
docker-compose up -d
```

### From Source (Local Development)

```bash
git clone https://github.com/sandraschi/docker-mcp.git
cd docker-mcp
uv sync
uv run docker-mcp
```

##  Usage

### Starting the Server

**Via `uvx` (one-liner):**
```bash
uvx docker-mcp
```

**Via `uv` (local):**
```bash
cd docker-mcp
uv run docker-mcp
```

**Via Docker:**
```bash
docker run -d \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  sandraschi/docker-mcp
```

### MCP Tools

**Docker Desktop Management:**
```python
# Check daemon status with hang detection
result = await docker_desktop_status(autofix=False)

# Auto-recover from hanging daemon
result = await docker_daemon_recover()

# Graceful daemon restart
result = await docker_daemon_restart()

# Fix update elevation errors
result = await docker_desktop_update(full_wipe=False)
```

### API Endpoints

- `GET /health` - Health check endpoint to verify service status
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation with [ReDoc](https://github.com/Redocly/redoc)

### Example: Check Docker Status

```python
from fastmcp import MCPClient

client = MCPClient("http://localhost:8000")
status = client.call_tool("docker_desktop_status", {"autofix": False})
print(status)
```

##  Documentation

Full documentation is available at [GitHub Wiki](https://github.com/sandraschi/docker-mcp/wiki).

##  Contributing

Contributions are welcome! Please read our \
[Contributing Guidelines](CONTRIBUTING.md) for details.


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.

##  License

This project is licensed under the MIT License - \
see the [LICENSE](LICENSE) file for details.

---

*Docker MCP Server - Comprehensive Docker operations with FastMCP 3.2.0+*
