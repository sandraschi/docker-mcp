# DockerMCP

## FastMCP 2.11.3 server for comprehensive Docker operations with Austrian efficiency

[![FastMCP](https://img.shields.io/badge/FastMCP-2.11.3-blue)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-✓-blue)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Austrian Efficiency](https://img.shields.io/badge/Austrian-Efficiency-red)](https://en.wikipedia.org/wiki/Austrian_school)

*Vienna-style Docker management with FastMCP 2.11.3 - because your containers deserve Sachertorte-level precision.*

## 🚀 Features

### State Management (Powered by FastMCP 2.11.3)

DockerMCP leverages FastMCP 2.11.3's built-in state management system for all its stateful operations. This provides several key benefits:

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

### Austrian Efficiency Add-ons

- **Docker Watchdog**: Automatic monitoring and recovery of Docker daemon
- **Stack Health Checks**: One-command status of all your stacks
- **Problem Detection**: Find and diagnose issues before they become problems
- **Intelligent Recovery**: Automated fixes for common Docker issues
- **Maintenance Recommendations**: Proactive suggestions for keeping your Docker environment clean
- **Cross-Platform Support**: Works on both Windows and Linux systems

## 🚨 Docker Watchdog

### Features

- **Automatic Recovery**: Automatically restarts Docker daemon if it becomes unresponsive
- **Cross-Platform**: Works on both Windows and Linux systems
- **Configurable**: Adjust check intervals and retry attempts
- **Detailed Logging**: Comprehensive logs for troubleshooting
- **Service Integration**: Runs as a system service (systemd on Linux, Windows Service on Windows)

### Installation

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

## 🏗 Project Structure

```text
dockermcp/
├── src/
│   └── dockermcp/
│       ├── api/                 # API endpoints and routes
│       ├── core/                # Core Docker operations
│       │   ├── containers.py    # Container management
│       │   ├── images.py        # Image handling
│       │   ├── networks.py      # Network management
│       │   ├── system.py        # System operations
│       │   └── volumes.py       # Volume management
│       │
│       ├── models/              # Data models and schemas
│       ├── tools/               # FastMCP 2.11.3 compatible tools
│       │   ├── compose/         # Docker Compose tools
│       │   ├── containers/      # Container management tools
│       │   ├── images/          # Image management tools
│       │   ├── networks/        # Network management tools
│       │   ├── system/          # System management tools
│       │   ├── volumes/         # Volume management tools
│       │   └── workflow/        # Workflow automation tools
│       │
│       └── utils/               # Utility functions
│           ├── json_utils.py    # JSON handling utilities
│           └── process_utils.py # Process management utilities
│
├── tests/                      # Test suite
├── docs/                       # Documentation
└── examples/                   # Usage examples
```

## 📦 Installation

### Prerequisites

- Python 3.8+
- Docker Engine 20.10.0+
- FastMCP 2.11.3+ (handles all state management internally)

### From Source

```bash
git clone https://github.com/sandraschi/dockermcp.git
cd dockermcp
pip install -e .
```

## 🛠 Usage

### Starting the Server

```bash
python -m dockermcp
```

### Example: List Containers

```python
from fastmcp import MCPClient

client = MCPClient("http://localhost:8000")
containers = client.list_containers()
print(containers)
```

## 🧩 DXT Package

DockerMCP is available as a DXT package for easy integration with Claude Desktop:

1. Build the DXT package:

   ```bash
   python -m dxt build
   ```

2. Install the resulting `.dxt` file through Claude Desktop

## 📚 Documentation

Full documentation is available at [GitHub Wiki](https://github.com/sandraschi/dockermcp/wiki).

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*"In Vienna, even the containers run on time."* - Probably not Gustav Mahler
