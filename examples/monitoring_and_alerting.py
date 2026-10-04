"""
Monitoring and Alerting Example for DockerMCP

This script demonstrates how to set up monitoring and alerting for Docker
containers using DockerMCP. It includes:
- Container metrics collection
- Health checks
- Alerting based on thresholds
- Integration with external monitoring tools
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastmcp import MCPClient

# Absolute log path: a bare filename lands in the host's cwd (BUG-063)
LOG_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "docker-mcp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_DIR / "monitoring.log")],
)
logger = logging.getLogger("docker-monitor")


class ContainerMonitor:
    """Monitor Docker containers and trigger alerts based on metrics."""

    def __init__(self, client: MCPClient):
        self.client = client
        self.monitored_containers: dict[str, dict[str, Any]] = {}
        self.metrics_history: dict[str, list[dict[str, Any]]] = {}
        self.alerts: dict[str, list[dict[str, Any]]] = {}
        self.running = False
        self.metrics_interval = 30  # seconds
        self.max_history = 100  # max data points per container

        # Alert thresholds
        self.thresholds = {
            "cpu_percent": 80.0,  # Alert if CPU > 80%
            "memory_percent": 80.0,  # Alert if memory > 80%
            "memory_usage": 1024 * 1024 * 1024,  # 1GB
            "restart_count": 3,  # Alert if container restarts > 3 times
            "health_status": "unhealthy",  # Alert if container is unhealthy
        }

        # Alert handlers
        self.alert_handlers = {"log": self._log_alert, "console": self._console_alert, "webhook": self._webhook_alert}

    async def start(self) -> None:
        """Start the monitoring service."""
        if self.running:
            logger.warning("Monitor is already running")
            return

        logger.info("Starting Docker container monitor")
        self.running = True

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_shutdown, sig)

        # Start monitoring loop
        while self.running:
            try:
                await self._monitor_containers()
                await asyncio.sleep(self.metrics_interval)
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e!s}", exc_info=True)
                await asyncio.sleep(5)  # Avoid tight loop on errors

    def _handle_shutdown(self, sig) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig.name}, shutting down...")
        self.running = False

    async def _monitor_containers(self) -> None:
        """Monitor all running containers."""
        try:
            # Get list of all running containers
            response = await self.client.list_containers(all=False)
            if response.get("status") != "success":
                logger.error(f"Failed to list containers: {response.get('error')}")
                return

            # Update monitored containers
            current_containers = {c["id"]: c for c in response.get("containers", [])}

            # Add new containers to monitoring
            for container_id, container in current_containers.items():
                if container_id not in self.monitored_containers:
                    logger.info(f"Discovered new container: {container.get('name')} ({container_id[:12]})")
                    self.monitored_containers[container_id] = {
                        "name": container.get("name"),
                        "image": container.get("image"),
                        "status": container.get("status"),
                        "started_at": datetime.utcnow().isoformat(),
                        "metrics": {},
                        "last_alert": {},
                    }
                    self.metrics_history[container_id] = []
                    self.alerts[container_id] = []

            # Remove stopped containers
            removed_containers = set(self.monitored_containers.keys()) - set(current_containers.keys())
            for container_id in removed_containers:
                container = self.monitored_containers[container_id]
                logger.info(f"Container stopped: {container.get('name')} ({container_id[:12]})")
                del self.monitored_containers[container_id]
                del self.metrics_history[container_id]
                del self.alerts[container_id]

            # Collect metrics for each container
            for container_id, _container in self.monitored_containers.items():
                if container_id in current_containers:
                    await self._collect_metrics(container_id, current_containers[container_id])

            # Check for alerts
            await self._check_alerts()

        except Exception as e:
            logger.error(f"Error in container monitoring: {e!s}", exc_info=True)

    async def _collect_metrics(self, container_id: str, container: dict[str, Any]) -> None:
        """Collect metrics for a container."""
        try:
            # Get container stats
            stats_response = await self.client.container_stats(container_id)
            if stats_response.get("status") != "success":
                logger.error(f"Failed to get stats for container {container_id}: {stats_response.get('error')}")
                return

            stats = stats_response.get("stats", {})

            # Calculate CPU usage percentage
            cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0) - stats.get(
                "precpu_stats", {}
            ).get("cpu_usage", {}).get("total_usage", 0)

            system_delta = stats.get("cpu_stats", {}).get("system_cpu_usage", 0) - stats.get("precpu_stats", {}).get(
                "system_cpu_usage", 0
            )

            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * 100.0
                cpu_percent *= stats.get("cpu_stats", {}).get("online_cpus", 1)

            # Calculate memory usage
            memory_stats = stats.get("memory_stats", {})
            memory_usage = memory_stats.get("usage", 0)
            memory_limit = memory_stats.get("limit", 1)  # Avoid division by zero
            memory_percent = (memory_usage / memory_limit) * 100.0

            # Get container health status
            health_status = container.get("health", {}).get("status", "unknown").lower()

            # Create metrics snapshot
            timestamp = datetime.utcnow().isoformat()
            metrics = {
                "timestamp": timestamp,
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage": memory_usage,
                "memory_limit": memory_limit,
                "memory_percent": round(memory_percent, 2),
                "network_rx": stats.get("network", {}).get("rx_bytes", 0),
                "network_tx": stats.get("network", {}).get("tx_bytes", 0),
                "block_read": stats.get("blkio_stats", {}).get("io_service_bytes_recursive", [{}])[0].get("value", 0),
                "block_write": stats.get("blkio_stats", {}).get("io_service_bytes_recursive", [{}])[1].get("value", 0),
                "health_status": health_status,
                "restart_count": container.get("restart_count", 0),
            }

            # Update container metrics
            self.monitored_containers[container_id]["metrics"] = metrics
            self.monitored_containers[container_id]["status"] = container.get("status")

            # Store metrics history
            if container_id in self.metrics_history:
                self.metrics_history[container_id].append(metrics)
                # Keep only the most recent data points
                if len(self.metrics_history[container_id]) > self.max_history:
                    self.metrics_history[container_id] = self.metrics_history[container_id][-self.max_history :]

            logger.debug(f"Collected metrics for {container.get('name')}: {json.dumps(metrics, indent=2)}")

        except Exception as e:
            logger.error(f"Error collecting metrics for container {container_id}: {e!s}", exc_info=True)

    async def _check_alerts(self) -> None:
        """Check for alert conditions and trigger alerts."""
        for container_id, _container in self.monitored_containers.items():
            metrics = container.get("metrics", {})
            container_name = container.get("name", container_id[:12])

            # Check CPU threshold
            if metrics.get("cpu_percent", 0) > self.thresholds["cpu_percent"]:
                await self._trigger_alert(
                    container_id,
                    "high_cpu",
                    f"High CPU usage: {metrics.get('cpu_percent')}% > {self.thresholds['cpu_percent']}%",
                    metrics,
                )

            # Check memory threshold (percentage)
            if metrics.get("memory_percent", 0) > self.thresholds["memory_percent"]:
                await self._trigger_alert(
                    container_id,
                    "high_memory_percent",
                    f"High memory usage: {metrics.get('memory_percent'):.1f}% > {self.thresholds['memory_percent']}%",
                    metrics,
                )

            # Check memory threshold (absolute)
            if metrics.get("memory_usage", 0) > self.thresholds["memory_usage"]:
                await self._trigger_alert(
                    container_id,
                    "high_memory_usage",
                    f"High memory usage: {metrics.get('memory_usage') / (1024 * 1024):.1f}MB > {self.thresholds['memory_usage'] / (1024 * 1024):.1f}MB",
                    metrics,
                )

            # Check restart count
            if metrics.get("restart_count", 0) > self.thresholds["restart_count"]:
                await self._trigger_alert(
                    container_id,
                    "high_restart_count",
                    f"High restart count: {metrics.get('restart_count')} > {self.thresholds['restart_count']}",
                    metrics,
                )

            # Check health status
            if metrics.get("health_status") == self.thresholds["health_status"]:
                await self._trigger_alert(
                    container_id, "unhealthy", f"Container is unhealthy: {metrics.get('health_status')}", metrics
                )

    async def _trigger_alert(self, container_id: str, alert_type: str, message: str, metrics: dict[str, Any]) -> None:
        """Trigger an alert for a container."""
        container = self.monitored_containers.get(container_id, {})
        container_name = container.get("name", container_id[:12])

        # Check if this alert was recently triggered to avoid spam
        last_alert = container.get("last_alert", {}).get(alert_type)
        if last_alert and (datetime.utcnow() - datetime.fromisoformat(last_alert)) < timedelta(minutes=5):
            logger.debug(f"Alert {alert_type} for {container_name} was recently triggered, skipping")
            return

        # Create alert
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "container_id": container_id,
            "container_name": container_name,
            "alert_type": alert_type,
            "message": message,
            "metrics": metrics,
        }

        # Store alert
        if container_id not in self.alerts:
            self.alerts[container_id] = []
        self.alerts[container_id].append(alert)

        # Update last alert time
        if "last_alert" not in self.monitored_containers[container_id]:
            self.monitored_containers[container_id]["last_alert"] = {}
        self.monitored_containers[container_id]["last_alert"][alert_type] = alert["timestamp"]

        # Log the alert
        logger.warning(f"ALERT: {container_name} - {message}")

        # Send alert to all registered handlers
        for handler_name, handler in self.alert_handlers.items():
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler_name}: {e!s}", exc_info=True)

    async def _log_alert(self, alert: dict[str, Any]) -> None:
        """Log alert to file."""
        with open("alerts.log", "a") as f:
            f.write(json.dumps(alert) + "\n")

    async def _console_alert(self, alert: dict[str, Any]) -> None:
        """Print alert to console."""
        print("\n=== ALERT ===")
        print(f"Container: {alert['container_name']} ({alert['container_id'][:12]})")
        print(f"Type:      {alert['alert_type']}")
        print(f"Message:   {alert['message']}")
        print(f"Timestamp: {alert['timestamp']}")
        print("=" * 40)

    async def _webhook_alert(self, alert: dict[str, Any]) -> None:
        """Send alert to a webhook."""
        # Example implementation - replace with actual webhook URL
        webhook_url = "https://webhook.example.com/alerts"
        try:
            # In a real implementation, you would use an HTTP client like aiohttp
            # to send the alert to the webhook
            logger.info(f"Sending alert to webhook: {webhook_url}")
            # response = await http_client.post(webhook_url, json=alert)
            # response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e!s}")

    def get_metrics_history(self, container_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get historical metrics for a container."""
        return self.metrics_history.get(container_id, [])[-limit:]

    def get_alerts(self, container_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Get alerts, optionally filtered by container."""
        if container_id:
            return self.alerts.get(container_id, [])[-limit:]
        else:
            # Return all alerts, sorted by timestamp
            all_alerts = []
            for alerts in self.alerts.values():
                all_alerts.extend(alerts)
            return sorted(all_alerts, key=lambda x: x["timestamp"], reverse=True)[:limit]


async def main() -> None:
    """Run the monitoring example."""
    # Initialize the client
    client = MCPClient("http://localhost:8000")
    client.api_key = "your-api-key-here"

    # Create and start the monitor
    monitor = ContainerMonitor(client)

    try:
        # Start monitoring in the background
        monitor_task = asyncio.create_task(monitor.start())

        print("Docker container monitor started. Press Ctrl+C to stop...")

        # Keep the main task running
        while monitor.running:
            await asyncio.sleep(1)

            # Periodically print a status update
            if int(datetime.utcnow().timestamp()) % 30 == 0:  # Every 30 seconds
                print("\n=== Status Update ===")
                for container_id, container in monitor.monitored_containers.items():
                    metrics = container.get("metrics", {})
                    print(f"{container.get('name', container_id[:12])}:")
                    print(f"  Status: {container.get('status')}")
                    print(f"  CPU: {metrics.get('cpu_percent', 0):.1f}%")
                    print(
                        f"  Memory: {metrics.get('memory_usage', 0) / (1024 * 1024):.1f}MB / {metrics.get('memory_limit', 1) / (1024 * 1024):.1f}MB ({metrics.get('memory_percent', 0):.1f}%)"
                    )
                    print(f"  Health: {metrics.get('health_status', 'unknown')}")
                    print()

    except asyncio.CancelledError:
        logger.info("Shutting down monitor...")
    except Exception as e:
        logger.error(f"Error in main: {e!s}", exc_info=True)
    finally:
        # Stop monitoring
        monitor.running = False
        if "monitor_task" in locals():
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitor stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
