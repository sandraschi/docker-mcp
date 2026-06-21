# schip-mcp-docker — MCP Server Capabilities

## Server Overview

Docker MCP provides comprehensive Docker container orchestration, system management, and GPU monitoring through a FastMCP 3.3 server with dual transport (stdio for Claude Desktop + FastAPI HTTP for web dashboard). It exposes container lifecycle management, image operations, volume and network administration, Docker Desktop integration, GPU monitoring (NVIDIA and AMD), system diagnostics, agentic workflows, and an LLM-powered chat interface. The server runs a FastAPI backend on port 10807 for the web dashboard and communicates via MCP protocol for tool execution.

The server is organized into domain-specific tool groups: containers (list, create, start, stop, restart, exec, logs, stats, inspect, file operations), images (list, pull, build, history, prune), volumes (list, create, remove, prune), networks (full CRUD), GPU monitoring (list GPUs, usage, info), Docker Desktop management (status, update, daemon restart/recover), and system operations (info, health, capabilities). It also includes Prefab UI cards for rich in-chat visualizations, an agentic container workflow using FastMCP sampling, and a logging system with JSON format and Loki integration.

Configuration is minimal with sensible defaults. The server auto-detects Docker Desktop availability, GPU hardware, and LLM providers. It includes a web dashboard with container management UI, system metrics, and activity logs.

## Tools

### Container Operations

**list_containers** — Lists Docker containers with optional filtering.
- Parameters: all (bool, default false), filters (dict, optional)
- Returns: Array of container objects with id, name, image, status, ports, created

**container_management** (portmanteau in containers/container_management.py):
- Actions: list, get, create, start, stop, restart, remove, logs, stats, exec, top
- Container lifecycle with parameters for image, ports, volumes, environment, command

**container_exec** — Execute commands inside running containers.
- Parameters: container (str, required), command (str, required), workdir (str, optional), user (str, optional)
- Returns: {stdout, stderr, exit_code}

**container_logs** — Fetch logs from a container.
- Parameters: container (str), tail (int, default 100), since (str, optional), timestamps (bool)

**container_stats** — Live resource stats for a container (CPU, memory, network, block IO).

**container_inspect** — Detailed container configuration and state in JSON.

**container_files** — Copy files to/from containers and list file contents.

### Image Operations

**list_images** — List Docker images with repository, tag, id, size, created.
- Parameters: all (bool), filters (dict)

**get_image_history** — Show history/layers of an image.
- Parameters: image (str, required)

**build_image / pull_image / remove_image / prune_images** — Full image lifecycle.

### Volume Operations

**volume_management** (portmanteau):
- Actions: list, create, remove, prune
- Parameters: name, driver, driver_opts, labels for create

**list_volumes / create_volume / remove_volume / prune_volumes** — Individual tools.

### Network Operations

**network_management** (portmanteau):
- Actions: list, create, remove, connect, disconnect, prune
- Parameters: name, driver, subnet, gateway, ip_range, internal for create

### GPU Monitoring

**list_gpus** — List available GPU devices with properties.
- Returns: Array with id, name, memory, driver, compute capability

**get_gpu_info** — Detailed GPU information and capabilities.

**monitor_gpu_usage** — Real-time GPU utilization metrics.
- Parameters: interval_seconds (int, default 1), count (int, default 5)
- Returns: Usage %, memory %, temperature, power draw

### Docker Desktop Management

**docker_desktop_status** — Check Docker Desktop daemon status and health.
- Returns: {running, version, uptime, containers, images, health}

**docker_desktop_update** — Check for and optionally apply Docker Desktop updates.

**docker_daemon_restart** — Gracefully restart the Docker daemon.

**docker_daemon_recover** — Attempt to recover a non-responsive Docker daemon.
- Includes retry logic, service restart, Docker Desktop restart

### System Tools

**system_management** (portmanteau):
- Actions: info, health, df, version, events, ping
- Returns system-wide Docker information

**capabilities** — List all server capabilities and feature detection results.

**health** — Server health check endpoint.

**get_dashboard** — Dashboard overview with system info and container summary.

### Agentic Workflow

**agentic_container_workflow** — Multi-step container operations via LLM sampling.
- Parameters: goal (str, required) — Natural language description of what to achieve
- Uses ctx.sample() to plan and execute multi-step workflows autonomously

### Prefab UI Cards

**docker_containers_card** — Rich card showing container list with status badges.
**docker_desktop_status_card** — Docker Desktop health as a visual card.
**docker_system_info_card** — Engine system info as a Prefab card.

### Web Dashboard Bridge

**api_containers / api_system / api_images / api_dashboard** — REST API bridge endpoints for the web dashboard.

**chat** — LLM-powered chat about Docker operations.
**llm_providers** — List available LLM providers for chat integration.

### Logging System

**logs_query** — Query activity logs with filtering.
**logs_stats** — Log statistics and volume analysis.
**logs_export** — Export logs to file.
**logs_clear** — Clear all logs.

## Configuration

**Environment Variables:**
- DOCKER_HOST — Docker daemon socket (default: named pipe on Windows, /var/run/docker.sock on Linux)
- WEB_PORT, API_PORT — Web dashboard ports (defaults: 10806/10807)
- LOG_LEVEL — Logging verbosity (default: INFO)
- LOG_FILE — Log file path (default: logs/dockermcp.log)
- MCP_TRANSPORT — Transport mode (stdio, http, sse)
- MCP_HTTP_PORT — MCP HTTP transport port (default: 8000)

**Docker Requirements:**
- Docker Desktop 4.0+ (Windows) or Docker Engine 20.10+ (Linux)
- For GPU monitoring: nvidia-smi (NVIDIA) or rocm-smi (AMD)
- Docker SDK for Python (docker-py)

## Data Sources

- **Docker Engine API** — Primary data source for all container, image, volume, network operations
- **Docker Desktop** — Windows/macOS desktop daemon management
- **nvidia-smi / rocm-smi** — GPU hardware monitoring
- **Filesystem** — Container file operations, log storage, image build contexts
- **SQLite** — Activity log persistence and analytics

## Prompts

The server registers the following FastMCP prompts:
- **docker_expert** — Instructions for Docker operations expertise

## Resources

Dynamic MCP resources:
- **docker://containers** — Live container list
- **docker://system** — System information
- **docker://gpus** — GPU information
- **logs://activity** — Recent activity log entries

## Integration Points

- **FastMCP 3.3** — stdio (Claude Desktop) + HTTP/SSE transports
- **FastAPI Web Dashboard** — Port 10807 with REST endpoints
- **Vite React Frontend** — Port 10806 with container management UI
- **Tauri Desktop App** — NSIS installer with embedded PyInstaller
- **Loki** — Structured log shipping to Grafana Loki
- **LLM Providers** — Ollama, LM Studio, and OpenAI-compatible chat
- **GPU Monitoring** — NVIDIA and AMD GPU metrics
- **Agentic Workflows** — Sampling-based multi-step operations

## Advanced Container Operations

### Container Lifecycle State Machine
Container management follows the standard Docker lifecycle with the following states and transitions:
- **created** — Initial state after creation. Container has a configuration but no running process.
- **running** — Container process is actively executing. Entrypoint is started and PID 1 is active.
- **paused** — Process suspended via SIGSTOP. Resources are still allocated but no CPU is consumed. Useful for temporary investigation without full restart.
- **exited** — Process has terminated, either normally with exit code 0 or with an error code. The container's filesystem and configuration are preserved.
- **dead** — Container resources are partially cleaned up but the container is not fully removed. Usually requires force removal.

The container_management tool handles all state transitions with proper error handling and timeout support. State transitions that may block (stop, restart) accept a timeout parameter with a default of 10 seconds, automatically escalating to SIGKILL if the container does not respond to SIGTERM within the timeout period.

### Container Resource Management
When creating containers, the following resource constraints can be applied:
- **Memory limits**: Specify maximum memory in bytes or human-readable format ("512m", "2g"). Can also set memory reservation (soft limit) and swap limits.
- **CPU limits**: Specify CPU count (0.5, 2) or CPU shares (relative weight, 1024 = default). CPU pinning to specific cores via cpuset_cpus.
- **Block I/O**: Read/write bandwidth limits in bytes per second or IOPS (operations per second). Per-device limits supported.
- **Network I/O**: Traffic shaping via network-specific bandwidth limits via compose integration.
- **Restart policies**: "no" (never restart), "on-failure" (restart on non-zero exit), "always" (always restart), "unless-stopped" (restart unless explicitly stopped).
- **Health check**: Custom health check commands, interval, timeout, retries, start period. Container status shows "healthy", "unhealthy", or "starting".

### Image Management Details
The server supports the full Docker image workflow:
- **Pull**: Downloads images from configured registries with support for authentication, platform selection (linux/amd64, linux/arm64), and progress streaming. Tag parsing includes implicit ":latest" handling and digest-based pulling.
- **Build**: Builds images from Dockerfiles with support for build arguments, target stages for multi-stage builds, cache-from images, squash, network mode, and output platform selection. The build context can be a local directory path.
- **History**: Shows the layer history of any image including layer IDs, created timestamps, and layer commands. Useful for understanding image composition and identifying optimization opportunities (too many layers, unnecessary packages).
- **Pruning**: Removes unused images (dangling and unreferenced) with optional filtering by label, reference, or time since creation.

### Volume and Data Persistence
Docker volumes are the recommended mechanism for persisting data. The server supports:
- **Named volumes**: Managed by Docker, stored in Docker's volume directory. Can be created with specific drivers (local, nfs, tmpfs, cloud) and driver options. Labels for metadata and organization.
- **Bind mounts**: Direct host filesystem mounts into containers. The bind mount source must exist on the host and is specified as an absolute path.
- **Volume mounting**: Containers can mount volumes at specific container paths with read-only or read-write mode. Multiple volumes can be mounted per container with distinct container paths.
- **Volume lifecycle**: Create, list with driver and mountpoint details, inspect for metadata, remove (with force option for in-use volumes), and prune for cleanup of unused volumes.
- **Backup workflow**: Volumes can be backed up by running a temporary container with the volume mounted and using tar or rsync to export data.

### Network Configuration Details
The network management system supports:
- **Bridge networks**: Default network type for single-host communication. Supports custom subnets, gateways, IP ranges, and DNS configuration. Containers on the same bridge network can communicate using container names as hostnames.
- **Overlay networks**: Multi-host networking for Docker Swarm or Swarm-mode clusters. Encrypted communication between nodes.
- **Host network**: Container shares the host's network stack directly. No network isolation, but also no NAT overhead.
- **Macvlan/Ipvlan networks**: Assign MAC/IP addresses directly from the physical network. Useful for legacy applications that need direct network access.
- **Network-scoped aliases**: Containers can have network-specific aliases for service discovery.
- **DNS configuration**: Custom DNS servers, search domains, and DNS options per network or per container.
- **Network isolation**: Internal networks (no external access) for security-sensitive workloads like databases.

### GPU Integration Details
The GPU monitoring subsystem detects and reports:
- **NVIDIA GPUs**: Queries nvidia-smi for device name, memory (total, used, free), utilization (GPU, memory, encoder, decoder), temperature, power draw, PCI-e bandwidth, and compute capability. Supports all NVIDIA GPU architectures from Maxwell onwards.
- **AMD GPUs**: Queries rocm-smi for device info, memory, and utilization where available.
- **GPU passthrough to containers**: When using nvidia-container-toolkit or similar, containers can be created with --gpus all or specific GPU device requests.
- **Monitoring intervals**: Configurable interval (0.5-10 seconds) and sample count for continuous monitoring. Historical data available through log queries.

### Docker Desktop Integration Details
The Docker Desktop management tools provide:
- **Status detection**: Checks Docker Desktop service status, daemon health, container count, image count, version, and uptime. Using sample_interval for CPU sampling in resource metrics.
- **Daemon recovery**: Multi-stage recovery process for unresponsive daemons: first attempts graceful restart via Docker API, then Docker Desktop restart via platform-specific methods, then service restart via system services. Each stage has error capture and escalation on failure.
- **Update detection**: Checks Docker Desktop's current version against latest available version. Reports update availability and release notes.
- **Daemon restart**: Graceful daemon restart with configurable timeout and waiting period for containers to settle.

### Agentic Workflow Engine
The agentic_container_workflow tool uses FastMCP 3.3 sampling (ctx.sample) to plan and execute multi-step container operations from natural language goals. The workflow engine:

1. Receives a natural language goal from the user (e.g., "Create a Python dev environment")
2. Uses the host LLM to decompose the goal into a sequence of tool calls
3. Executes each step, passing results between sequential operations
4. Returns a summary of all steps taken and their outcomes

Example workflows the agent can handle:
- Setting up development environments (Python, Node, database containers)
- Deploying multi-container stacks with sidecar and init containers
- Troubleshooting container connectivity by exec-ing diagnostic commands
- Backup workflows by creating temporary containers with volume mounts
- Cleanup operations targeting specific image types or label patterns

### Logging and Observability System
The server maintains a structured logging system for all operations:
- **Activity log**: SQLite-backed log of all tool calls with timestamp, tool name, parameters, result status, and duration. Queryable by level, search term, time range, and tool name.
- **Log levels**: DEBUG (detailed diagnostic info), INFO (normal operation), WARNING (potential issues), ERROR (operation failures), CRITICAL (server-level failures).
- **Log export**: Export functionality for JSON, CSV, and plain text formats. Supports filtering by level before export.
- **Log statistics**: Count breakdowns by level, tool, and time period. Useful for identifying frequently failing operations.
- **Log clearing**: Manual or automatic clearing based on retention policy.
- **Loki integration**: Optional structured log shipping to Grafana Loki for centralized fleet observability.

## Error Handling

All tools return consistent error patterns:
- Docker connection errors: `{"error": "Cannot connect to Docker daemon", "recovery": "Start Docker Desktop"}`
- Container not found: `{"error": "Container not found: name_or_id"}`
- Permission errors: `{"error": "Access denied", "recovery": "Run with appropriate permissions"}`
- GPU monitoring unavailable: `{"error": "GPU monitoring not available", "recovery": "Install nvidia-smi"}`

## Docker Platform Support Details

On Windows, the server connects to Docker Desktop via the npipe:////./pipe/docker_engine named pipe. Docker Desktop must be running and configured to expose the daemon on the named pipe. The docker_desktop_status tool checks the Docker Desktop service state, engine health, container counts, and version information. The docker_daemon_recover tool attempts a multi-stage recovery of an unresponsive daemon: first a Docker API reconnect attempt, then a Docker Desktop restart via the Windows service manager, and finally a force restart of the Docker Engine service.

On Linux, the server connects via the unix:///var/run/docker.sock Unix socket. Docker Engine 20.10 or later is required. GPU monitoring requires nvidia-container-toolkit for NVIDIA GPUs or the appropriate AMD ROCm drivers for AMD GPUs. The list_gpus tool executes nvidia-smi or rocminfo as subprocesses to enumerate available GPU hardware.

On macOS, Docker Desktop uses a Unix socket at ~/.docker/run/docker.sock. The same Docker Desktop management tools are available as on Windows.

## Container Management Lifecycle Details

The container lifecycle follows the Docker Engine state machine with proper error handling at each transition. The create operation validates the image existence, port availability, volume mount existence, and network accessibility before creating the container. If validation fails, a detailed error message is returned explaining which resource is unavailable.

The start operation transitions a container from created or exited to running. If the container exits immediately due to an application error, the exit code and logs are available through container_inspect and container_logs. The stop operation sends SIGTERM with a configurable timeout, followed by SIGKILL if the container does not exit gracefully within the timeout period.

The remove operation deletes the container's metadata and optionally its filesystem. The force parameter enables removal of running containers by first stopping them. The volumes parameter controls whether anonymous volumes attached to the container are also removed.

## Image Build and Management Details

Image building uses the Docker Engine's build API with support for all standard Dockerfile instructions. The build context is a local directory path that is tarred and sent to the Docker daemon. Build arguments are passed via the buildargs parameter as a dictionary of key-value pairs. Multi-stage builds are supported through standard Dockerfile FROM ... AS syntax. The cache_from parameter specifies images to use as additional cache sources for faster rebuilds.

The get_image_history tool returns the image's layer metadata including the ID, creation timestamp, created by command, size, and comment for each layer. This is useful for understanding the composition of an image and identifying opportunities for optimization such as merging RUN commands or removing unnecessary layers.

Image pruning removes unused images from the local storage. Dangling images (untagged and unreferenced by any container) are removed by default. The filters parameter enables additional filtering by label, reference (image name), or time since creation (until filter).

## Volume Management Details

Named volumes are the preferred data persistence mechanism. They are created with configurable drivers (local for default, nfs for network storage, cloud-specific drivers for cloud storage). Driver options can be specified as a dictionary of key-value pairs for driver-specific configuration. Labels enable organizational metadata on volumes.

Bind mounts directly map a host directory into the container. The host path must be an absolute path and must exist on the host filesystem. Bind mounts have a risk of permission issues on Windows due to the different user namespace models compared to Linux containers.

Volume pruning removes all unused volumes (not mounted by any container). This operation is irreversible and should be used with caution. The force parameter must be explicitly set for pruning operations on in-use volumes.

## Network Management Details

Bridge networks provide isolation between groups of containers while allowing inter-container communication via container names as hostnames. Custom subnets, gateways, and IP ranges can be specified for precise IP address management. Internal networks (no external access) are useful for database containers that should not be reachable from outside the host.

Overlay networks enable multi-host communication in Docker Swarm mode. They require a Swarm cluster with at least one manager node. Encrypted overlay networks provide IPSEC encryption for data in transit between nodes.

The connect and disconnect operations attach or detach containers from networks at runtime without restarting the container. Containers can belong to multiple networks simultaneously, enabling complex network topologies with separate management, data, and public-facing networks.

## Service Monitoring and Metrics

The server provides monitoring at multiple levels. Container-level stats report CPU usage as a percentage of total host CPU, memory usage in bytes and percentage, network I/O in bytes transmitted and received, and block I/O in bytes read and written. Process-level information is available through the top operation which lists running processes within a container.

System-level monitoring includes disk usage broken down by Docker object type (images, containers, volumes, build cache), engine information with version and configuration, and health checks that verify the daemon is responding. Event monitoring captures real-time Docker events with filtering by type (container, image, volume, network, daemon) and event action (create, destroy, start, stop, etc.).

## Docker Desktop Recovery Process

The docker_daemon_recover tool implements a multi-stage recovery process for unresponsive Docker daemons. Stage 1 attempts to reconnect to the Docker API with exponential backoff starting at 1 second and doubling up to 30 seconds. If the API responds, recovery is successful. Stage 2 attempts to restart the Docker Desktop service using platform-specific service management commands. On Windows, this uses net stop/start for the Docker Desktop service. On macOS, it uses the Docker Desktop menu application. Stage 3 attempts a more aggressive restart by terminating the Docker Desktop process and letting the service manager restart it. Stage 4 as a last resort kills all Docker-related processes and starts fresh. Each stage reports its outcome and the overall recovery status. If all stages fail, the tool provides guidance for manual intervention including checking Windows event logs, verifying virtualization is enabled, and reinstalling Docker Desktop if corruption is suspected.

## Container File Operations

The container_files tool supports copying files between the host and containers, and reading file contents from within containers without executing shell commands. File copy operations support both directions: host-to-container for deploying configuration files and application updates, and container-to-host for extracting logs and output files. File contents can be read directly from containers using standard Docker API calls, providing access to configuration files and log output without needing to exec into the container.

## GPU Device Monitoring Implementation

GPU monitoring uses platform-specific tools to gather hardware metrics. On NVIDIA GPUs, the server executes nvidia-smi commands and parses the CSV output for device name, driver version, CUDA version, memory usage, GPU utilization, temperature, power draw, PCIe bandwidth, and encoder/decoder utilization. On AMD GPUs, it uses rocm-smi for similar metrics. The list_gpus tool returns all detected GPUs with their properties. The monitor_gpu_usage tool samples GPU metrics at configurable intervals for trend analysis. The get_gpu_info tool returns detailed capabilities including supported CUDA compute capabilities and architecture generation.

## Container Stats and Metrics

The container_stats tool provides real-time resource usage metrics for running containers. CPU usage is reported as a percentage of total host CPU capacity (100% = one full core). Memory usage is reported in bytes with a percentage of the container's memory limit or the host's total memory if no limit is set. Network I/O reports total bytes received and transmitted across all container network interfaces. Block I/O reports total bytes read and written to block devices. All metrics are instantaneous snapshots taken at the time of the API call. For trend analysis, call container_stats multiple times at intervals and compare the values.

## Docker Context Support

The server supports multiple Docker contexts through the DOCKER_CONTEXT environment variable or the docker_context module. A Docker context encapsulates the connection parameters for a specific Docker daemon or swarm. Switching contexts enables managing multiple Docker hosts from the same server instance. The list of available contexts is shown in system_management(action="info"). The default context connects to the local Docker daemon.
