# Docker MCP User Guide

## Getting Started

Docker MCP provides comprehensive Docker container management through natural conversation. Before starting, verify Docker Desktop or the Docker daemon is running on your system. Docker MCP auto-detects the Docker socket location on Windows (//./pipe/docker_engine), Linux (/var/run/docker.sock), and macOS (/var/run/docker.sock).

To begin, start your container management session by checking system status with the docker_system_info operation. This verifies connectivity, reports Docker version, and lists container counts by state. Then explore your current Docker resources: list containers, images, networks, and volumes.

When Docker Desktop is not running or the socket is unreachable, MCP reports the error with guidance to start Docker Desktop or verify socket permissions. On Linux, ensure your user is in the docker group or use rootless Docker.

## Core Workflows

### Container Lifecycle Management

List all containers with status filtering. Use docker_container_list with operation=list to show running, stopped, paused, or exited containers. Add filters for ancestor image, label key-value pairs, and name substring matching. The response includes container ID, image, command, created time, status, ports, and names.

Start a container from an existing image with docker_container_start. Specify the image name, optional command, environment variables as key-value pairs, port mappings in host_port:container_port format, volume mounts with source:destination pairs, network attachments by name, and resource limits for CPU and memory. The response returns the container ID and assigned name.

Inspect container details with docker_container_inspect. Returns full container configuration including network settings with IP addresses for each network, mount information with source and destination paths, environment variables, port bindings, restart policy, health check configuration and status, resource limits in effect, and labels.

Stop containers gracefully with docker_container_stop. Specify the grace period in seconds before SIGKILL is sent. The default timeout is 10 seconds. For forceful termination when containers hang, use docker_container_kill with a specific signal like SIGKILL or SIGTERM.

Execute commands inside running containers with docker_container_exec. Provide the container identifier, command with arguments, optional working directory inside the container, environment variable overrides, and whether to allocate a pseudo-TTY for interactive programs. Response includes stdout, stderr, and exit code.

### Log Management

Retrieve container logs with docker_container_logs. Control the output with parameters: tail limits the number of most recent lines (default 100), since filters to entries after a timestamp or relative time like 10m or 1h, timestamps prepends RFC3339 timestamps to each line, and follow streams new log entries as they arrive.

For structured log analysis, use JSON output format which parses Docker's JSON log driver entries into structured fields. For raw log inspection, use text output format. Combine with exec operations to run grep, awk, or jq inside containers for advanced log processing.

### Image Operations

List local images with docker_image_list. Supports filters for reference matching, dangling images, label key-value pairs, and temporal before/since markers. Returns repository, tag, image ID, created time, and virtual size.

Pull images from registries with docker_image_pull. Supports public images from Docker Hub, private registry authentication, platform selection for multi-architecture images specifies the OS and architecture variant, and digest pinning for immutable references.

Build images from Dockerfiles with docker_image_build. Specify the build context directory containing the Dockerfile. The Dockerfile path defaults to Dockerfile in the context directory. Tag with one or more name:tag references. Build arguments inject compile-time variables. Multi-stage build targets select a specific build stage as the final output. Cache configuration controls cache-from sources and cache-to destinations for CI pipeline optimization.

Push images to registries with docker_image_push. The server uses pre-configured registry credentials. Tag the image with the registry URL prefix before pushing.

## Docker Compose Workflows

Compose stacks are managed through docker_compose operations. Start a stack with docker_compose_up specifying the project directory containing the docker-compose.yml file. The detach parameter runs services in the background. Build before starting rebuilds service images if the Dockerfile changed.

Stop a stack with docker_compose_down. The remove_orphans flag cleans up containers not defined in the compose file. The volumes flag removes named volumes declared in the compose file.

View logs across the compose stack with docker_compose_logs. Filter by service name to focus on specific components. Use tail for recent lines and follow for live streaming.

Run one-off commands in service containers with docker_compose_exec. This is useful for database migrations, seeding, and administrative tasks. The service must be running.

Build service images independently with docker_compose_build. This caches build results for faster startup on subsequent up operations.

Scale services with docker_compose_scale to adjust replica counts for horizontally scalable services. The compose file must define the service with deploy.replicas for scaling to take effect.

## Network Management

Create custom networks with docker_network_create. Specify driver type: bridge for single-host networking, overlay for swarm multi-host networking, macvlan for giving containers MAC addresses on the physical network, or ipvlan for layer-2 or layer-3 network virtualization. Configure subnet and gateway CIDR notation. Set IP range for automatic address allocation. Set internal to disable external DNS resolution.

List networks with docker_network_list. Returns driver, scope, subnet, gateway, connected containers with IP addresses, and network options including IPv6, internal, and attachable flags.

Connect containers to networks with docker_network_connect. Specify per-container IP address for static assignment. Set aliases for DNS-based service discovery within the network.

Disconnect containers with docker_network_disconnect. Force disconnect when the container is stopped or unresponsive.

Remove networks with docker_network_remove. All containers must be disconnected first. Prune unused networks with docker_network_prune, filtered by custom label criteria.

## Volume Management

Create named volumes with docker_volume_create. Specify volume driver: local for host-local storage, nfs for network filesystem mounts, or cloud-specific drivers for S3, Azure, or GCS. Driver options include NFS server address, mount options, and filesystem type.

List volumes with docker_volume_list. Returns driver, mountpoint location on the host, labels, and scope for swarm local or cluster-wide volumes.

Inspect volumes with docker_volume_inspect. Returns detailed configuration including driver-specific options, creation timestamp, and labels. Useful for verifying mount options before attaching to containers.

Remove volumes with docker_volume_remove. Volumes must not be mounted by any container. Force bypasses this check. Prune unused volumes with docker_volume_prune. Filter by label to remove only specific volumes.

Common volume usage patterns include database data directories mounted to /var/lib/postgresql/data for PostgreSQL or /var/lib/mysql for MySQL, configuration files mounted as read-only, log directories for centralized log collection, and application upload directories for persistent user content.

## System Monitoring

Monitor Docker resource usage with docker_system_df. Reports disk usage broken down by image count and reclaimable size, container count and writable layer size, local volume count and estimated size, and build cache size. Useful for identifying cleanup candidates.

Check Docker system information with docker_system_info. Returns comprehensive details: server version and API version, operating system and architecture, kernel version and build, storage driver with backing filesystem, logging driver, Cgroup driver, security options, swarm status with node count, and container counts by running, paused, stopped state.

Stream Docker events with docker_system_events. Filter by event type: container, image, volume, network, daemon, plugin. Filter by specific object name or ID. Use since and until temporal parameters for time-bounded queries. Events include attach, commit, copy, create, destroy, detach, die, exec_create, exec_detach, exec_start, export, health_status, import, kill, load, mount, oom, pause, pull, push, reload, rename, resize, restart, save, start, stop, top, unmount, unpause, and update.

## Agentic Workflows

Complex multi-step Docker operations are automated through agentic workflows. These workflows use the Docker MCP sampling capability to plan and execute operations with intermediate validation.

The build-run-test-stop workflow builds a Docker image from source, starts a container from the image, runs tests inside the container, collects test results, stops the container, and optionally removes it. This is useful for CI/CD pipeline simulation and development iteration.

The compose-deploy workflow deploys a Compose stack with environment variable injection for different deployment targets, verifies all services reach healthy state, runs smoke tests against the stack, and reports service endpoints and health status. Useful for staging environment setup.

The image-optimize workflow analyzes image layers with docker_image_history, identifies layer size optimization opportunities, suggests multi-stage build refactoring, and generates an optimized Dockerfile. Useful for reducing image size for production deployment.

The migrate-workload workflow stops a running container, creates a volume backup to a tar archive, pulls the updated image, starts a new container with migrated volumes and networks, and verifies the migration. Useful for zero-downtime image updates.

The monitoring-stack workflow deploys Prometheus and Grafana as Docker containers configured to scrape Docker metrics, imports a Docker dashboard into Grafana, and reports access URLs for the monitoring interfaces. Useful for infrastructure observability setup.

The backup-workflow creates database dumps from running containers, archives volume data to compressed tar files, exports container configuration JSON, and stores backups to a configured backup directory with timestamped filenames. Useful for disaster recovery preparation.

## Troubleshooting Guide

Docker daemon not reachable: Verify Docker Desktop is running and check socket path. On Windows restart Docker Desktop from the system tray. On Linux check systemctl status docker and verify user is in docker group with groups command. On macOS restart Docker Desktop from the menu bar.

Port already allocated error: Check which container is using the port with docker_container_list showing port mappings. Stop the conflicting container or change the host port mapping. Use random host port assignment by omitting the host port or specifying 0:container_port.

Image not found locally: Docker MCP attempts automatic pull from configured registries when the image is not found locally. Verify image name spelling and tag existence on the registry. Check registry authentication if using a private registry.

Container exits immediately: Check the command and entrypoint for correctness. View logs with docker_container_logs to see error output. Verify environment variables and mounted configuration files. Run interactively with TTY and stdin open for debugging.

Disk space full: Run docker_system_df to identify reclaimable resources. Remove unused containers, images, volumes, and build cache. Use docker_container_prune, docker_image_prune, docker_volume_prune, and docker_system_prune for cleanup.

Permission denied on Docker socket: On Linux add user to docker group with sudo usermod -aG docker $USER and log out and back in. On macOS and Windows Docker Desktop manages permissions automatically.

Network connectivity issues between containers: Verify containers are on the same Docker network with docker_network_inspect. Use container names for DNS resolution on user-defined bridge networks. Check firewall rules if using iptables or Windows Firewall.

Container DNS resolution failure: Check Docker daemon DNS configuration in daemon.json. Override DNS servers per container with --dns parameter. Use docker_container_exec with nslookup or dig for diagnosis.

TLS handshake error with remote daemon: Verify DOCKER_TLS_VERIFY and DOCKER_CERT_PATH environment variables. Check client certificates expiration. Ensure the remote daemon is configured for TLS access.

Out of memory (OOM) killed container: Check container memory limit settings with docker_container_inspect. Monitor actual memory usage with docker_container_stats. Increase memory limit or optimize application memory usage. Add swap limit with --memory-swap for burst capacity.

## Performance Tips

Use docker_container_list with specific filter labels rather than scanning all containers. Filtering by ancestor, status, or label are indexed queries on the Docker daemon side.

Enable BuildKit by default for faster builds with DOCKER_BUILDKIT=1 environment variable. BuildKit supports concurrent build stages, better cache invalidation, and SSH agent forwarding. Use secrets mounts instead of COPY for build-time credentials.

Optimize docker_container_logs by specifying tail and since parameters. Avoid retrieving full logs when only recent entries are needed. For continuous log streaming, use the follow parameter which establishes a persistent connection.

Batch image cleanup with prune operations rather than removing individual images. docker_image_prune with the dangling-only filter removes untagged intermediary layers. docker_system_prune performs comprehensive cleanup of all unused Docker objects.

Set resource limits on all containers to prevent resource starvation. CPU limits with --cpus use fractional values like 1.5 for one and a half cores. Memory limits with --memory specify values like 512m or 2g. Combine soft limits with --memory-reservation for burst capacity with a safety floor.

## Docker Socket Configuration

Docker socket discovery follows platform-specific defaults. On Windows, the named pipe at //./pipe/docker_engine connects to Docker Desktop. The socket is accessed without permission issues when Docker Desktop runs as the current user. Docker Desktop on Windows uses WSL2 backend for Linux container support.

On Linux, the Unix socket at /var/run/docker.sock requires docker group membership for non-root access. Rootless Docker uses a user-specific socket at ~/.docker/run/docker.sock. Docker contexts switch between multiple daemon endpoints for multi-environment management.

On macOS, Docker Desktop creates the socket at /var/run/docker.sock which is symlinked to the Desktop VM socket inside the hypervisor. No additional permissions are needed beyond having Docker Desktop running.

Remote Docker daemons connect via TCP with TLS authentication. Set DOCKER_HOST to tcp://hostname:2376 for TLS-enabled connections. The client certificate and key files in ~/.docker/ authenticate to the remote daemon. SSH connections use docker context to manage remote hosts with ssh://user@hostname endpoints.

## Development Environment Setup

Setting up a development environment with Docker Compose follows a standard pattern. Create a docker-compose.yml file with service definitions for your application components. Common services include application servers, databases, caches, message queues, and reverse proxies. Configuration is managed through environment variables in a .env file in the same directory as the compose file.

Development compose files typically use bind mounts to sync source code changes into containers for hot-reload. Set the build context to the project root directory. Expose service ports for direct access from the host development tools. Add health checks for dependent service readiness verification.

Development databases use named volumes for data persistence between container restarts. Initialize databases with SQL scripts mounted to the docker-entrypoint-initdb.d directory. Set resource limits lower than production to detect memory leaks during development.

Development networking creates a shared bridge network for inter-service communication. Use service names as hostnames for service discovery. Expose only the reverse proxy port to the host for a single entry point.

## Production Deployment

Production deployments require hardened container configurations. Use specific image tags, not latest, for reproducible deployments. Pin base image versions in Dockerfile FROM statements. Use health checks for automatic container recovery. Set restart policies to unless-stopped or always for critical services.

Production resource limits prevent noisy-neighbor problems. Set CPU limits with --cpus using fractional core allocation. Set memory limits with --memory and reserve with --memory-reservation. Configure swap behavior with --memory-swap equals memory for no swap. Set ulimit values for file descriptor and process limits.

Production logging uses structured log drivers like json-file with log rotation or fluentd for centralized log aggregation. Monitor log sizes with max-size and max-file options. Configure log levels at the application level for granular control.

Production secrets management uses Docker secrets for swarm services or mounted secret files. Never bake secrets into images. Use environment variables injected at runtime for non-sensitive configuration. Rotate credentials regularly with container replacement.

## Integration with CI/CD

Docker MCP integrates with CI/CD pipelines through automated build and deploy workflows. Build images in CI with docker_image_build using BuildKit for performance. Tag images with commit SHA and branch name for traceability. Push to registry with docker_image_push for deployment access.

Deployment strategies include blue-green with parallel stacks and traffic switch, rolling updates with container replacement, canary releases with traffic splitting, and rollback with previous image tag redeployment. Each strategy uses Docker MCP compose operations for orchestration.

Test integration runs test containers with docker_container_start targeting the CI database service. Execute test suites with docker_container_exec and collect results from stdout. Clean up test resources with container and volume removal in post-test steps.

Health monitoring after deployment runs smoke tests through docker_container_exec. Check API endpoints, database connectivity, and dependent service availability. Rollback automatically if health checks fail with docker_compose_down and previous version redeployment.

## Advanced Operations

Container checkpoint and restore creates point-in-time snapshots of running container state. Checkpoints include memory, process tree, and filesystem changes. Use for live migration between hosts and development environment snapshots.

Container resource updates adjust CPU and memory limits on running containers without restart. Use docker_container_update with --cpus and --memory flags. Monitor with docker_container_stats and adjust based on observed usage patterns.

Image exporting saves images as tar files for offline transfer. Use docker_image_save with multiple image references in a single archive. Load on target systems with docker_image_load for air-gapped deployment.

Network traffic control with the tc (traffic control) command fine-tunes container network performance. Set bandwidth limits, latency, packet loss, and jitter for network resilience testing. Applied through docker_container_exec with appropriate capabilities.

Volume backup creates consistent snapshots of Docker volumes. For databases, lock tables or use transaction snapshots before backup. Archive the volume path on the host filesystem. Restore by extracting to a new volume and reconnecting the container.

## Container Resource Configuration

CPU resource allocation uses multiple parameters for fine-grained control. The --cpus parameter specifies the number of CPU cores as a float value. A value of 1.5 allows the container to use up to one and a half cores. The --cpuset-cpus parameter pins the container to specific CPU cores using a comma-separated list or range like 0-3. The --cpu-shares parameter sets relative CPU weight compared to other containers with a default of 1024. Higher values like 2048 give the container double the CPU time under contention. The --cpu-quota and --cpu-period parameters set the CFS scheduler quota in microseconds for precise CPU bandwidth control. A quota of 50000 with a period of 100000 limits the container to 50% of one CPU core.

Memory resource allocation uses --memory for the hard limit and --memory-reservation for the soft limit. The hard limit triggers OOM killer when exceeded. The soft limit is used when the host is under memory pressure. The --memory-swap parameter sets the total memory and swap combined limit. Setting --memory-swap equal to --memory disables swap usage entirely. The --memory-swappiness parameter controls the kernel tendency to swap container pages with values from 0 to 100 where lower values reduce swapping. The --oom-kill-disable parameter prevents the OOM killer from terminating the container when memory is exhausted at the risk of system instability.

Blkio resource allocation uses --blkio-weight for relative block I/O priority with values from 10 to 1000. The --device-read-bps and --device-write-bps parameters set per-device I/O rate limits in bytes per second. The --device-read-iops and --device-write-iops parameters set per-device I/O operation limits per second. These parameters control storage performance isolation between containers sharing the same storage subsystem.

GPU resource allocation requires nvidia-container-runtime or nvidia-container-toolkit on the host. The --gpus parameter specifies GPU access. Use --gpus all for all available GPUs or --gpus '"device=0,1"' for specific GPU indices. GPU capabilities like compute, utility, graphics, and display can be specified with --gpus '"capabilities=gpu"'. GPU memory and compute utilization is reported through nvidia-smi inside the container.

## Container Security Hardening

User namespace remapping isolates container root from host root. Configure userns-remap in daemon.json to map container UIDs to a non-privileged host user range. This prevents container root from having host root privileges. All container processes run as a mapped high-numbered UID on the host. This adds overhead to volume permission management since host file ownership does not match container UIDs.

Seccomp security profiles restrict the system calls available to container processes. Docker applies a default seccomp profile that blocks dangerous syscalls like kexec_load, open_by_handle_at, init_module, and finit_module. Custom seccomp profiles in JSON format allow fine-grained syscall allow and deny lists. Apply with --security-opt seccomp=/path/to/profile.json.

AppArmor and SELinux provide mandatory access control for containers. AppArmor profiles confine container processes to specific file system paths, network capabilities, and process operations. SELinux context labeling applies type enforcement rules to container processes. Apply with --security-opt apparmor=profile_name or --security-opt label=type:container_t.

Capability management follows the principle of least privilege. The default capability set includes CHOWN, DAC_OVERRIDE, FSETID, FOWNER, MKNOD, NET_RAW, SETGID, SETUID, SETFCAP, SETPCAP, NET_BIND_SERVICE, SYS_CHROOT, KILL, and AUDIT_WRITE. Remove unnecessary capabilities with --cap-drop=ALL then --cap-add=required_cap. Common required capabilities include NET_ADMIN for network configuration, SYS_PTRACE for debugging tools, and SYS_ADMIN for mount operations inside containers.

Read-only root filesystems prevent container processes from writing to the filesystem. Use --read-only to enforce read-only rootfs. Add tmpfs mounts with --tmpfs /var/run and --tmpfs /tmp for directories that need write access. This prevents malware persistence and configuration drift in production containers.

## Docker Registry Operations

Docker Hub is the default public registry. Official images like nginx, postgres, python, node, ubuntu, and alpine are maintained by the Docker team and upstream projects. Autobuild images are built from GitHub and Bitbucket repositories. Verified publisher images are maintained by commercial software vendors. Community images are contributed by Docker Hub users.

Private registries require authentication for push and optional authentication for pull. Configure registry credentials in ~/.docker/config.json using docker login. The config file stores credentials base64-encoded. Credential helpers like wincred on Windows and osxkeychain on macOS store credentials in the system credential manager for better security. Registry mirror configuration in daemon.json caches frequently pulled images on a local registry for faster pulls in CI environments.

Image tagging follows the repository:tag format. The latest tag is the default when no tag is specified. Semantic versioning tags like 1.0.0, 1.0, and 1 allow consumers to pin major versions while receiving minor updates. Digest pinning uses the image digest format like nginx@sha256:abc123 for immutable image references that cannot be overwritten. Manifests list tags for testing before applying the same image to production.

Multi-architecture images use manifest lists to present a single image reference that resolves to different platform-specific images. Docker automatically selects the correct variant for the pulling host. Build multi-architecture images with docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 and push to a registry. The manifest list includes the OS, architecture, and variant for each platform entry.

## BuildKit Advanced Configuration

BuildKit is the next-generation Docker image builder. Enable BuildKit with DOCKER_BUILDKIT=1 environment variable or by setting features.buildkit: true in daemon.json. BuildKit provides concurrent build stage execution, improved cache invalidation with LLB intermediate representation, SSH agent forwarding with --ssh default, secret mounts for build-time credentials with --secret id=mysecret, and cache mounts for persistent package caches with --mount=type=cache,target=/root/.cache/pip.

BuildKit cache mounts persist between builds for the same cache directory. This speeds up package manager operations for pip, apt, npm, and go modules. The cache is stored in the BuildKit cache directory and can be exported to a registry with --cache-to type=registry,ref=mycache and imported with --cache-from type=registry,ref=mycache for CI pipeline acceleration.

BuildKit frontend images provide alternative build formats. The docker/dockerfile:1 frontend supports the standard Dockerfile syntax. The docker/dockerfile:1-labs frontend adds experimental features like heredoc support in RUN commands and chown flag for COPY --from. The docker/dockerfile:1.5 frontend adds RUN --mount=type=bind for mounting files from the build context without copying.

## Docker Context and Multi-Environment Management

Docker contexts manage connection to multiple Docker daemons. Create contexts for development, staging, and production environments. Each context stores the Docker endpoint URL, TLS certificate paths, and default namespace for swarm services. Switch between contexts with docker context use context_name. Default contexts include default for the local daemon and desktop-linux for Docker Desktop WSL2 backend.

Remote Docker contexts connect to daemons over SSH for encrypted management. Configure with docker context create remote --docker host=ssh://user@hostname. SSH key authentication uses the default SSH agent or specified identity file. Remote contexts support all Docker commands including container lifecycle, image management, and compose operations with the same latency considerations as local contexts.

Docker orchestration platforms extend the Docker API. Docker Swarm mode provides native clustering with docker swarm init and docker swarm join. Swarm services use docker service create with --replicas for scale and --update-parallelism for rolling updates. Swarm stacks deploy compose files with docker stack deploy. Docker contexts switch between swarm managers for multi-cluster management.

Kubernetes integration through Docker Desktop deploys compose files to a local single-node Kubernetes cluster. The kubernetes option in Docker Desktop settings enables the Kubernetes server. The docker compose convert command generates Kubernetes deployment YAML from compose files. The kubectl CLI provides full Kubernetes API access for advanced orchestration needs.

## Docker API Rate Limiting and Authentication

Docker Hub enforces anonymous and authenticated pull rate limits. Anonymous pulls are limited to 100 pulls per six hours per IP address. Authenticated pulls are limited to 200 pulls per six hours per Docker ID. Docker Pro and Team subscriptions provide higher rate limits. Use docker login to authenticate pulls and track pull counts in the Docker Hub account dashboard.

To avoid rate limit issues in CI environments, configure registry mirrors for cached pulls. Pull images once and tag them to a private registry. Use docker_image_pull with authentication credentials for images from private registries. Monitor pull rate with the Docker Hub rate limit headers: Ratelimit-Limit, Ratelimit-Remaining, and Ratelimit-Reset which indicate the current rate limit status and reset time.

## Container Migration and Portability

Exporting containers creates portable tar archives. Use docker_container_export to export the container filesystem as a tar archive. The export includes all container filesystem layers flattened to a single filesystem snapshot. It does not include container metadata, configuration, or layer history. Import the archive as a new image with docker image import for recovery or migration.

Committing containers creates new images from running container state. Use docker_container_commit to create an image snapshot of a container with all filesystem changes. Tag the committed image with a descriptive label. Committed images retain the container entrypoint and cmd but lose volume and network configuration. Use commit for debugging and snapshot purposes rather than image building.

Loading and saving images transfers images between daemons without a registry. Use docker_image_save to export one or more images as a single tar file. Use docker_image_load to import saved images. Saved images include all layers and metadata. Transfer the tar file between hosts for air-gapped environments or restricted networks.

## Container Networking Modes

Bridge networking is the default mode for containers. Each container gets a virtual Ethernet interface connected to the docker0 bridge. Containers on the same bridge communicate by IP address. User-defined bridge networks provide DNS resolution by container name. Expose ports with -p for host access to container services.

Host networking shares the host network namespace. The container uses the host IP address and port range. No port mapping is needed since the container binds directly to host interfaces. Host networking provides the best network performance but reduces container isolation. Use for performance-critical proxy and load balancer containers.

Macvlan networking assigns MAC addresses to containers. Containers appear as physical devices on the host network. The host interface must be in promiscuous mode. Macvlan is useful for legacy applications that require direct network access. IPvlan networking uses the same MAC address as the host interface and routes based on IP addresses.

None networking disables all networking for the container. Only the loopback interface is available. Use for security-sensitive workloads that do not require network access. Useful for batch processing, offline data analysis, and test containers.

Overlay networking enables multi-host communication in swarm mode. Containers on different swarm nodes communicate through an encrypted VXLAN tunnel. The overlay network supports service discovery with DNS resolution across nodes. Application traffic is encrypted at the network layer by default.
