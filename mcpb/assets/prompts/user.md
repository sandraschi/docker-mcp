# schip-mcp-docker — User Guide

## Quick Start

### Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Python 3.10+ with uv

### Installation
```bash
git clone https://github.com/sandraschi/docker-mcp
cd docker-mcp
uv sync
```

### Start the Server
```bash
# MCP stdio mode (for Claude Desktop)
uv run run_server.py

# HTTP mode (for web dashboard)
set MCP_TRANSPORT=http
uv run run_server.py

# Full webapp (requires webapp setup)
.\start.ps1
# Opens http://localhost:10806 (frontend) / http://localhost:10807 (API)
```

### Register with Claude Desktop
```json
{
  "mcpServers": {
    "docker-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:/Dev/repos/docker-mcp", "run_server.py"],
      "env": { "PYTHONPATH": "${workspaceFolder}/src" }
    }
  }
}
```

## Tutorials

### Tutorial 1: List All Containers
See all containers, both running and stopped:
```
list_containers(all=true)
```
For only running containers:
```
list_containers(all=false)
```
The response includes container IDs, names, images, status (running/exited/paused), port mappings, and creation timestamps.

### Tutorial 2: Inspect a Container in Detail
Get full configuration details for a container:
```
container_inspect(container="my_app")
```
Returns JSON with mounts, networks, environment variables, restart policy, resource limits, and more.

### Tutorial 3: Start, Stop, and Restart Containers
Control container lifecycle:
```
# Start a stopped container
container_management(operation="start", container_id="my_app")

# Gracefully stop a running container
container_management(operation="stop", container_id="my_app")

# Restart with timeout
container_management(operation="restart", container_id="my_app", timeout=10)
```

### Tutorial 4: Create and Run a New Container
Launch a new container with custom settings:
```
container_management(
  operation="create",
  image="nginx:latest",
  name="web_server",
  ports={"80/tcp": 8080},
  volumes={"/host/html": {"bind": "/usr/share/nginx/html", "mode": "ro"}},
  environment={"NGINX_HOST": "localhost"},
  detach=true
)
```

### Tutorial 5: Execute Commands Inside a Container
Run commands in a running container:
```
container_exec(container="my_app", command="ls -la /app/data", workdir="/app", user="root")
```
For interactive debugging:
```
container_exec(container="my_app", command="cat /var/log/app.log", workdir="/app")
```

### Tutorial 6: View Container Logs
Fetch recent logs from a container:
```
container_logs(container="my_app", tail=50, timestamps=true)
```
Get logs since a specific time:
```
container_logs(container="my_app", tail=200, since="2025-01-01T00:00:00Z")
```

### Tutorial 7: Monitor Container Resource Usage
See live CPU, memory, and network stats:
```
container_stats(container="my_app")
```
List all containers with resource metrics:
```
list_containers(all=true, stats=true)
```

### Tutorial 8: Manage Docker Volumes
List all volumes:
```
volume_management(operation="list")
```
Create a new volume:
```
volume_management(operation="create", name="app_data", driver="local")
```
Remove unused volumes:
```
volume_management(operation="prune")
```

### Tutorial 9: Work with Docker Images
List available images:
```
list_images()
```
Pull an image from a registry:
```
container_management(operation="pull", image="python:3.13-slim")
```
View image layers:
```
get_image_history(image="python:3.13-slim")
```

### Tutorial 10: GPU Monitoring
List available GPUs:
```
list_gpus()
```
Monitor GPU usage over time:
```
monitor_gpu_usage(interval_seconds=2, count=10)
```
Get detailed GPU info:
```
get_gpu_info()
```

### Tutorial 11: Docker Desktop Management
Check Docker Desktop health:
```
docker_desktop_status()
```
If Docker becomes unresponsive:
```
docker_daemon_recover()
```
Restart the daemon:
```
docker_daemon_restart()
```

### Tutorial 12: Network Management
List Docker networks:
```
network_management(operation="list")
```
Create a network:
```
network_management(operation="create", name="my_network", driver="bridge", subnet="172.20.0.0/16")
```
Connect a container:
```
network_management(operation="connect", network="my_network", container="my_app")
```

### Tutorial 13: System Health Dashboard
Full system overview:
```
get_dashboard()
```
System information:
```
system_management(operation="info")
```
Disk usage:
```
system_management(operation="df")
```

### Tutorial 14: Agentic Container Workflow
Use natural language for complex operations:
```
agentic_container_workflow(goal="Create a Python 3.13 container named 'dev_env' with port 8000 exposed, mount the current directory, and start it with 'python -m http.server'")
```
The LLM plans and executes the multi-step operation automatically.

### Tutorial 15: View and Export Activity Logs
Query activity logs:
```
logs_query(limit=50, level="INFO")
```
Get log statistics:
```
logs_stats()
```
Export to file:
```
logs_export(format="json", level="WARNING")
```
Clear old logs:
```
logs_clear()
```

### Tutorial 16: Use Prefab UI Cards
Rich visual cards in supporting MCP clients:
```
docker_containers_card()
docker_desktop_status_card()
docker_system_info_card()
```

## API Reference

### REST Endpoints (FastAPI, port 10807)

**GET /api/health** — Server health check

**GET /api/dashboard** — Dashboard overview data

**GET /api/containers** — List containers (query: ?all=true)

**GET /api/containers/{id}** — Container details

**POST /api/containers/{id}/start** — Start container

**POST /api/containers/{id}/stop** — Stop container

**POST /api/containers/{id}/restart** — Restart container

**DELETE /api/containers/{id}** — Remove container

**GET /api/containers/{id}/logs** — Container logs (query: ?tail=100)

**GET /api/system** — System information

**GET /api/images** — List images

**POST /api/images/pull** — Pull image

**DELETE /api/images/{id}** — Remove image

### MCP Tool Response Format
```json
{
  "success": true,
  "operation": "list",
  "data": [{ "id": "abc123", "name": "my_app", "image": "nginx:latest", "status": "running", "ports": {"80/tcp": 8080} }],
  "count": 1
}
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Cannot connect to Docker daemon" | Docker not running | Start Docker Desktop |
| "Container not found" | Wrong name or ID | Use list_containers(all=true) first |
| "Port already allocated" | Port conflict | Use a different host port |
| "Image not found" | Image name typo | Check registry and image name |
| "Permission denied" | Insufficient rights | Run as administrator |
| GPU not detected | No GPU or missing drivers | Check nvidia-smi availability |
| Docker Desktop not responding | Daemon hung | Use docker_daemon_recover() |
| Volume in use | Container references it | Remove the container first |
| Network already exists | Name collision | Use a different network name |
| Build fails | Dockerfile error | Check Dockerfile syntax |

## FAQ

**Q: Does this work with Docker Desktop on Windows?**
A: Yes. Docker Desktop is fully supported including daemon management and named pipe connections.

**Q: Can I manage remote Docker hosts?**
A: Yes. Set the DOCKER_HOST environment variable to the remote daemon URL.

**Q: Does GPU monitoring work with WSL2?**
A: Yes, when using NVIDIA CUDA on WSL2 with the appropriate drivers.

**Q: Can I run Docker commands without Docker Desktop?**
A: On Linux, the Docker Engine can run without Docker Desktop. On Windows, Docker Desktop is required.

**Q: How do I create a container with resource limits?**
A: Use the create action with the resources parameter: `{"memory": "512m", "cpus": 0.5}`

**Q: Can I attach to a running container's shell?**
A: Use container_exec with command="/bin/bash" or "powershell.exe" depending on the container OS.

**Q: Does this support docker-compose?**
A: Basic compose support is planned. Individual container management is fully supported.

**Q: How do I clean up unused resources?**
A: Use volume_management(operation="prune"), network_management(operation="prune"), and the image prune tools.

## Common Deployment Patterns

### Development Environment Setup
Create a full development stack with database, cache, and application containers:
```
# Step 1: Create a dedicated network
network_management(operation="create", name="dev_stack", driver="bridge", subnet="172.25.0.0/16")

# Step 2: Start PostgreSQL with persistent data
container_management(
  operation="create",
  image="postgres:16-alpine",
  name="dev_db",
  environment={"POSTGRES_PASSWORD": "devpass", "POSTGRES_DB": "app_dev"},
  volumes={"pgdata": {"bind": "/var/lib/postgresql/data", "mode": "rw"}},
  network="dev_stack"
)

# Step 3: Start Redis for caching
container_management(
  operation="create",
  image="redis:7-alpine",
  name="dev_cache",
  ports={"6379/tcp": 16379},
  network="dev_stack"
)

# Step 4: Build and run the application
container_management(
  operation="create",
  image="python:3.13-slim",
  name="dev_app",
  command="sleep infinity",
  ports={"8000/tcp": 8000},
  volumes={"D:/project": {"bind": "/app", "mode": "rw"}},
  working_dir="/app",
  environment={"DATABASE_URL": "postgresql://devpass@dev_db:5432/app_dev", "REDIS_URL": "redis://dev_cache:6379/0"},
  network="dev_stack"
)

# Step 5: Start everything
container_management(operation="start", container_id="dev_db")
container_management(operation="start", container_id="dev_cache")
container_management(operation="start", container_id="dev_app")

# Step 6: Verify connectivity
container_exec(container="dev_app", command="python -c 'import socket; print(socket.gethostbyname(\"dev_db\"))'")
```

### CI/CD Pipeline Container
Create a build container for automated CI/CD:
```
container_management(
  operation="create",
  image="ubuntu:24.04",
  name="ci_builder",
  command="sleep 3600",
  volumes={"D:/repo": {"bind": "/workspace", "mode": "rw"}},
  environment={"CI": "true", "BUILD_NUMBER": "42"},
  working_dir="/workspace"
)

container_management(operation="start", container_id="ci_builder")

# Install build dependencies
container_exec(container="ci_builder", command="apt-get update && apt-get install -y build-essential cmake ninja-build")

# Run builds inside the container
container_exec(container="ci_builder", command="cmake -B build -G Ninja")
container_exec(container="ci_builder", command="ninja -C build")

# Clean up
container_management(operation="stop", container_id="ci_builder")
container_management(operation="remove", container_id="ci_builder")
```

### Database Backup Workflow
Backup a PostgreSQL database using Docker:
```
# Step 1: Create a dump using pg_dump in a temporary container
container_exec(
  container="dev_db",
  command="pg_dump -U postgres app_dev > /tmp/backup.sql"
)

# Step 2: Copy the dump to the host
container_exec(
  container="dev_db",
  command="cat /tmp/backup.sql"
)
# Capture the output and save it locally

# Step 3: For larger databases, use docker cp equivalent via volume mounts
container_management(
  operation="create",
  image="postgres:16-alpine",
  name="backup_helper",
  command="pg_dump -h dev_db -U postgres app_dev > /backup/app_dev_2025.sql",
  environment={"PGPASSWORD": "devpass"},
  volumes={"D:/backups": {"bind": "/backup", "mode": "rw"}},
  network="dev_stack"
)

# Step 4: Remove the helper
container_management(operation="remove", container_id="backup_helper")
```

### Multi-Container Monitoring Setup
Monitor application performance with Prometheus and Grafana:
```
# Create monitoring network
network_management(operation="create", name="monitoring", driver="bridge")

# Start Prometheus
container_management(
  operation="create",
  image="prom/prometheus:latest",
  name="prometheus",
  ports={"9090/tcp": 19090},
  network="monitoring"
)

# Start Grafana
container_management(
  operation="create",
  image="grafana/grafana:latest",
  name="grafana",
  ports={"3000/tcp": 13000},
  network="monitoring"
)

# Start node-exporter on each host
container_management(
  operation="create",
  image="prom/node-exporter:latest",
  name="node_exporter",
  ports={"9100/tcp": 19100},
  network="monitoring"
)
```

### Cleanup and Maintenance Routines
Regular maintenance tasks:
```
# Remove all stopped containers
# Use agentic workflow for smart cleanup
agentic_container_workflow(goal="Remove all stopped containers that are older than 24 hours")

# Remove dangling images
agentic_container_workflow(goal="Clean up dangling images and unused networks")

# Full system cleanup
# Check disk usage first
system_management(operation="df")

# Then prune what's needed
volume_management(operation="prune")
network_management(operation="prune")
```

## Troubleshooting Guide

### Docker Desktop Connection Issues
1. Check if Docker Desktop is running: `docker_desktop_status()`
2. If not running, start Docker Desktop manually or use the recovery tools
3. If running but unresponsive: `docker_daemon_recover()`
4. If still unresponsive: `docker_daemon_restart()`
5. Check Windows Firewall settings for Docker networking

### Container Fails to Start
1. Inspect the container for exit code: `container_inspect(container="my_app")`
2. Check logs for error messages: `container_logs(container="my_app", tail=100)`
3. Verify all dependencies (volumes, networks, configs) exist
4. Try running with an interactive command like "sleep infinity" to debug

### Port Conflict Resolution
1. Identify the conflicting process: Use the error message to identify the port
2. Stop the conflicting container or change the host port in container creation
3. Common conflicts: port 80/443 (IIS, nginx on host), 3000 (Node dev servers), 5432 (local PostgreSQL)

## Advanced Port and Resource Configuration

### Port Mapping Patterns
```
# Simple port mapping (HOST:CONTAINER)
"ports": {"80/tcp": 8080}

# Multiple ports
"ports": {"80/tcp": 8080, "443/tcp": 8443, "5432/tcp": 15432}

# UDP ports
"ports": {"53/udp": 10053}

# Range mapping
"ports": {"8000-8010/tcp": "8000-8010"}
```

### Volume Mount Patterns
```
# Named volume
"volumes": {"my_volume": {"bind": "/data", "mode": "rw"}}

# Bind mount (host path → container path)
"volumes": {"D:/project": {"bind": "/workspace", "mode": "rw"}}

# Read-only bind mount
"volumes": {"D:/config": {"bind": "/etc/config", "mode": "ro"}}

# tmpfs mount (in-memory)
"tmpfs": {"/tmp": "size=100M"}
```

## Container Orchestration Reference

### Docker REST API Equivalent Commands
| MCP Tool | Docker CLI Equivalent | REST API |
|----------|----------------------|----------|
| list_containers | docker ps | GET /containers/json |
| container_inspect | docker inspect | GET /containers/{id}/json |
| container_logs | docker logs | GET /containers/{id}/logs |
| container_stats | docker stats | GET /containers/{id}/stats |
| container_exec | docker exec | POST /containers/{id}/exec |
| list_images | docker images | GET /images/json |
| get_image_history | docker history | GET /images/{name}/history |
| volume_management(list) | docker volume ls | GET /volumes |
| network_management(list) | docker network ls | GET /networks |
| system_management(info) | docker info | GET /info |
| system_management(df) | docker system df | GET /system/df |

## Docker Compose Integration

While the server primarily manages individual containers, the compose integration provides basic Compose file support through the container and network creation tools. For full Compose workflow, the recommended approach is to create each service individually using container_management and connect them using network_management. This provides more granular control and monitoring compared to the all-in-one compose up approach.

## Security Best Practices

When using Docker MCP in production, follow these security practices: never run containers with the --privileged flag unless absolutely necessary, use read-only root filesystems where possible, drop unnecessary Linux capabilities, use user namespaces to remap container users to non-root host users, scan images for vulnerabilities regularly, use secrets management for sensitive environment variables (Docker secrets or external vaults), and restrict outbound network access from containers that do not need it.

The server supports all standard Docker security features including seccomp profiles, AppArmor profiles (Linux), and Windows-specific security configurations for Windows containers. Resource limits (CPU, memory, disk) should be set on all containers to prevent resource exhaustion attacks.

## Container Networking Patterns

Common networking patterns include: bridge network for single-host multi-container applications where containers need to communicate by name, host network for applications that need direct access to host network interfaces with minimal overhead, overlay network for multi-host microservices that need to span multiple Docker hosts in a Swarm cluster, and macvlan for legacy applications that require direct MAC addresses on the physical network.

For development environments, the recommended pattern is to create a single bridge network for all application containers, connect database containers to an internal network that has no external access, and expose only the frontend container's ports to the host. For production, use Docker Compose or Swarm stacks with defined network topologies.

## Advanced Troubleshooting Guide

### Docker Daemon Won't Start
If Docker Desktop fails to start or the daemon is unresponsive, follow this diagnostic sequence: check docker_desktop_status for current state, review Windows Event Viewer for Docker-related errors under Applications and Services Logs, verify that virtualization is enabled in BIOS (required for WSL2 backend), check that Hyper-V and Windows Hypervisor Platform are enabled Windows features, ensure no conflicting software is running (VirtualBox, VMware, older Docker Toolbox), and try docker_daemon_recover which attempts a multi-stage recovery. If all else fails, restart the Docker Desktop service from the system tray menu.

### Container Network Connectivity Issues
If a container cannot reach network services, verify the container is connected to the correct network with container_inspect, check that the container's DNS configuration is correct by exec-ing nslookup or dig from within the container, verify the host firewall is not blocking container traffic, ensure the container's network is not configured as internal (no external access), check for IP address conflicts with other containers or host services, and verify that Docker's DNS service (127.0.0.11 within containers) is functioning correctly.

### Volume Mount Permission Issues
On Windows, permission issues with bind mounts commonly arise from the mismatch between Windows user permissions and Linux container user IDs. Solutions include using named volumes instead of bind mounts for better permission handling, setting the container user to match the host user's UID, using chmod within the container startup script, or mounting volumes with the :Z or :z SELinux flags on Linux. For Windows containers (not WSL2), permissions follow standard Windows ACLs and are generally more predictable.

### Image Pull Failures
If docker pull fails, check internet connectivity from the container host, verify that the image name and tag are correct, ensure Docker Hub or the private registry is accessible, check for rate limiting on Docker Hub (anonymous pulls are limited to 100/6h, authenticated to 200/6h), verify registry authentication if pulling from a private registry, and check that the image exists for the requested platform (linux/amd64 vs linux/arm64).

### GPU Not Detected in Container
To use GPU acceleration in containers, ensure the NVIDIA Container Toolkit (nvidia-container-toolkit) is installed on Linux, or Docker Desktop with WSL2 CUDA support is configured on Windows. Verify GPU availability with list_gpus, then test GPU passthrough by running a GPU-enabled container like nvidia/cuda:12.0-runtime with nvidia-smi.

## Production Deployment Guide

For production Docker environments, follow these recommendations: pin image tags to specific versions (never use :latest in production), use read-only root filesystems for application containers, set memory limits on all containers, implement health checks on all services, use Docker secrets for sensitive configuration, enable Docker Content Trust for image signing, configure container restart policies (always or unless-stopped), use resource reservation to guarantee minimum resources, implement log rotation within containers, and regularly prune unused images and volumes to reclaim disk space.

The server's monitoring tools can be used to establish baseline performance metrics and alert on anomalies. Set up regular log export with logs_export to maintain audit trails. Use the agentic_container_workflow for automated maintenance tasks like weekly image pruning and volume cleanup.

## Docker Compose Equivalent Operations

While the server does not directly run docker-compose, individual Compose operations can be replicated through the tools. Creating a network with specific subnet settings replaces the networks section of a Compose file. Creating containers with port mappings, volumes, environment variables, and network connections replaces the services section. The container_management create operation accepts all parameters that a Compose service definition supports, including ports, volumes, environment, working_dir, entrypoint, command, user, restart_policy, and network_mode.

For multi-container applications, create the network first, then create containers in dependency order (database first, then cache, then application), start them in the same order, and use container_exec to run database migrations or initialization scripts after all containers are running. The agentic_container_workflow can automate this complete setup process from a single natural language goal.

## Resource Limit Configuration Examples

CPU limits: use cpus=1.5 for one and a half CPU cores, cpuset_cpus="0-1" for specific cores 0 and 1, cpu_shares=512 for lower relative priority (default is 1024). Memory limits: use memory="512m" for 512 megabytes, memory_reservation="256m" for soft limit, memory_swap="1g" for memory+swap limit. Block I/O limits: use blkio_weight=500 for lower I/O priority (default 500), device-specific limits via blkio_device_read_bps and blkio_device_write_bps. All limits are optional and can be combined in any configuration.

## Docker Event Monitoring

The events operation provides real-time Docker daemon event streaming. Events are categorized by type: container events (create, destroy, start, stop, die, restart, pause, unpause, exec_create, exec_start, exec_die, export, resize, attach, rename, update, health_status), image events (pull, push, tag, untag, delete, save, load, import), volume events (create, destroy, mount, unmount), network events (create, connect, disconnect, destroy, remove), and daemon events (reload, shutdown, update). Each event includes the timestamp, type, action, ID, and optional metadata like exit codes, error messages, and labels.

Events can be filtered by type, action, label, and time range. The system_management(operation="events", since="2025-01-01T00:00:00Z") call returns events from the specified start time. Events are useful for auditing container lifecycle changes, troubleshooting unexpected container terminations, and monitoring deployment rollouts.

## Container Image Build Optimization

Optimizing Docker image builds reduces build time and image size. Key practices include: use multi-stage builds to separate build dependencies from runtime dependencies, combine RUN commands to reduce layer count, use .dockerignore to exclude unnecessary files from the build context, order layers from least to most frequently changing to maximize cache utilization, use slim or alpine base images to reduce size, remove package manager caches in the same RUN command that installs packages, and pin base image versions for reproducible builds. The get_image_history tool helps identify optimization opportunities by showing each layer's size and creation command.

## Docker Networking Troubleshooting Reference

Common Docker networking issues and their solutions: containers cannot communicate by hostname - ensure they are on the same user-defined bridge network (the default bridge does not support DNS resolution). Container cannot reach the internet - check that the network is not configured as internal and that the host has internet connectivity. Port mapping not working - verify the host port is not in use by another service, check Windows Firewall rules, and ensure the container is actually listening on the specified container port. DNS resolution fails within container - check /etc/resolv.conf within the container, verify Docker's embedded DNS server (127.0.0.11) is accessible, and consider using custom DNS servers via the dns parameter. Network performance poor - check for CPU or memory contention on the host, verify network driver selection (overlay networks have higher overhead than bridge), and consider using host network mode for latency-sensitive applications.

## Windows-Specific Docker Configuration

On Windows, Docker Desktop offers two backends: WSL2 (recommended) and Hyper-V. WSL2 provides better performance and compatibility with Linux containers. Hyper-V backend is more isolated but has higher resource overhead. Windows containers require the Hyper-V backend and use Windows Server Core or Nano Server base images. To switch between backends, use the Docker Desktop settings. GPU acceleration in WSL2 requires NVIDIA CUDA drivers installed on Windows and the nvidia-container-toolkit configured in WSL2.

## Docker Compose File Migration

When migrating from Docker Compose to individual container management with the server, translate each Compose service definition to a container_management create call. The image, ports, environment, volumes, networks, command, working_dir, and restart_policy fields map directly. The depends_on field does not need a direct equivalent as the server creates containers in the order you specify. Compose network definitions map to network_management create calls. Compose volume definitions map to volume_management create calls. The agentic_container_workflow can automate this translation from a natural language description of the compose configuration.

## Docker Compose File Examples Translated

A typical web application compose file translates to individual MCP tool calls. Create a network named app_network. Create a PostgreSQL container named db on that network with environment variables for credentials and a named volume for data persistence. Create a Redis container named cache on the same network. Create the application container named web on the network, mounting the application code as a volume and exposing port 8000. Set environment variables pointing to db and cache by container name. The API documentation and Swagger UI pages provide interactive exploration of all available endpoints. The web dashboard at port 10806 provides container management UI for users who prefer graphical interfaces over tool calls.

## Additional Troubleshooting Scenarios Docker

Container exits immediately with code 1 typically indicates an application error. Use container_logs to check the error output. Container stays in created state indicates a configuration issue preventing the container from starting. Use container_inspect to check mounts, ports, and environment variables. Container runs but is not reachable on the expected port indicates a port mapping or firewall issue. Verify the container is listening on the correct port with container_exec and check that the host port is not blocked by Windows Firewall.

## Container Resource Monitoring Best Practices

For production monitoring, set up regular container_stats calls at 30-second intervals to track resource usage trends. Log the results with timestamps for historical analysis. Set alert thresholds at 80% CPU, 80% memory, and 90% disk usage. When thresholds are exceeded, use agentic_container_workflow to diagnose and remediate. For critical containers, configure Docker's built-in restart policies (always or unless-stopped) to ensure automatic recovery after crashes or host restarts.

## Volume and Bind Mount Comparison

Named volumes and bind mounts serve different use cases in Docker. Named volumes are managed by Docker, stored in Docker's volume directory, and are portable across environments. They support volume drivers for cloud storage, NFS, and other backends. Named volumes are preferred for persistent data that should be managed by Docker. Bind mounts map any host directory into the container and are useful for development (sharing source code) and configuration (providing host-specific config files). Bind mounts depend on the host filesystem structure and are not portable. Use named volumes for database data, cache directories, and upload directories. Use bind mounts for development code, configuration files, and log output that should be accessible from the host.

## Container Log Management Strategies

Effective log management is essential for containerized applications. The server provides container_logs for accessing recent log output from any container. For production deployments, configure your containers to write logs to stdout and stderr (the default for most applications). Docker collects these and makes them available through the logs API. For long-term log retention, use a log shipper like the Promtail agent to send logs to a centralized Loki instance, or configure Docker's log driver to send logs to a remote syslog server, AWS CloudWatch, or Google Cloud Logging. The server's built-in log management through logs_query provides short-term log access and statistics.

## Container Health Check Configuration

Health checks allow Docker to monitor container application health beyond simple process existence. Configure health checks in the container creation: health_check parameters include test (command to run, e.g., "curl -f http://localhost/health"), interval (how often to check, e.g., 30s), timeout (max time for check to complete, e.g., 10s), retries (consecutive failures before marking unhealthy, e.g., 3), and start_period (grace period before checks start, e.g., 40s). Containers show health status as starting, healthy, or unhealthy. Use container_inspect to check health status. Configure restart policies to automatically restart unhealthy containers.

## Docker Context Management

Docker contexts allow managing multiple Docker hosts from a single server instance. Create contexts for each remote Docker host or Swarm manager. Switch between contexts to run containers on different environments (development, staging, production). The docker_context module in the server provides context listing and switching capabilities. Each context stores the Docker daemon endpoint URL, TLS certificates if needed, and any orchestrator metadata. Contexts are managed through the Docker CLI and are shared across all Docker tools.

## Container File System Operations

The container_files tool enables file operations between host and container filesystems without executing shell commands inside the container. Copy configuration files from the host into a container for application setup. Extract log files from a container to the host for analysis. Read configuration files or output data from containers without starting shell sessions. The file operations use Docker's archive API which supports standard tar streaming for efficient data transfer.

## Docker Capacity Planning

For capacity planning, monitor the following metrics over time: container count trend, image storage usage, volume data growth, network traffic patterns, and GPU utilization. Use the server's monitoring tools to collect baseline data during normal operation. Set alerts at 70% of critical thresholds for proactive capacity management. Plan for 20% annual growth in container count and 30% annual growth in data storage requirements.

## Multi-Architecture Image Support

Docker supports multi-architecture images through manifest lists. When pulling images, the server automatically selects the architecture matching the host system. On Windows with WSL2 backend, Linux amd64 images are used. On ARM systems (Raspberry Pi, Apple Silicon), ARM64 images are selected automatically. The architecture can be overridden with the platform parameter in image pull operations for testing or cross-platform development scenarios.

## Container Security Scanning Integration

While the server does not include built-in container security scanning, it can be integrated with external scanning tools. After pulling or building images, use image inspection tools to check for known vulnerabilities. Use the agentic workflow to automate scanning: pull the image, save it to a tar file, scan with tools like Trivy or Docker Scout, and report findings. The server provides the image management tools needed for the scanning pipeline.

## Docker Cleanup Automation

Regular cleanup of unused Docker resources prevents disk space exhaustion. Schedule the following cleanup operations: daily pruning of dangling images and unused networks, weekly pruning of unused volumes, and monthly removal of stopped containers older than 30 days. The agentic_container_workflow tool can automate these cleanup tasks with natural language goals like "clean up all unused Docker resources" or "remove containers older than 24 hours". The logs_query and logs_stats tools help track cleanup effectiveness over time.

## Docker Networking Security

For secure Docker networking, use internal networks for database and cache containers that should not be accessible from outside the host. Use bridge networks for application containers that need to communicate with each other. Avoid using host network mode for untrusted containers. Use network-level encryption for overlay networks in multi-host deployments. Restrict container outbound access using network policies when using Docker Enterprise or third-party network plugins.

## Docker Build Cache Optimization

Docker build caching significantly speeds up repeated builds. The build cache is automatically used when rebuilding an image with unchanged layers. To optimize cache usage, order Dockerfile commands from least to most frequently changing. Combine RUN commands for package installations to create a single cache layer. Use the --cache-from parameter to specify additional images as cache sources when building in CI environments. The image build output shows which layers used cache and which were rebuilt.

The Docker MCP server provides comprehensive container management through a FastMCP interface with both stdio and HTTP transport modes for flexible deployment.
