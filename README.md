# DockerMCP 🐳

**FastMCP 2.10 server for comprehensive Docker operations with Austrian efficiency**

[![FastMCP](https://img.shields.io/badge/FastMCP-2.10-blue)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-✓-blue)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Austrian Efficiency](https://img.shields.io/badge/Austrian-Efficiency-red)](https://en.wikipedia.org/wiki/Austrian_school)

*Vienna-style Docker management with FastMCP 2.10 - because your containers deserve Sachertorte-level precision.*

## 🚀 Features

### Core Docker Operations

- **Container Management**: Create, start, stop, restart, and remove containers
- **Image Handling**: Pull, list, tag, and remove Docker images
- **Network Operations**: Manage Docker networks and connections
- **Volume Management**: Handle Docker volumes and storage
- **System Monitoring**: Get Docker system info, version, and disk usage

### Austrian Efficiency Add-ons

- **Stack Health Checks**: One-command status of all your stacks
- **Problem Detection**: Find and diagnose issues before they become problems
- **Intelligent Recovery**: Automated fixes for common Docker issues
- **Maintenance Recommendations**: Proactive suggestions for keeping your Docker environment clean

## 📦 Installation

### Prerequisites

- Python 3.8+
- Docker Engine 20.10.0+
- FastMCP 2.10+

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
