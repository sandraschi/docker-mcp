"""
Grafana integration utilities for Docker MCP.

This module provides functionality to interact with Grafana instances running in Docker,
including setup instructions, dashboard management, and monitoring.
"""
from typing import Dict, Any, Optional, List
import logging
import json
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class GrafanaManager:
    """Manager for Grafana integration with Docker MCP."""
    
    GRAFANA_IMAGE = "grafana/grafana:latest"
    GRAFANA_PORT = 13000  # Changed from 3000 to avoid conflicts
    DEFAULT_USER = "admin"
    DEFAULT_PASSWORD = "admin"  # Should be changed after first login
    
    def __init__(self, docker_client=None):
        """Initialize the Grafana manager.
        
        Args:
            docker_client: Optional Docker client instance
        """
        self.docker_client = docker_client
        self.base_url = None
        self.auth = None
        
    async def is_grafana_running(self) -> Dict[str, Any]:
        """Check if a Grafana container is running.
        
        Returns:
            Dict with status and container info if found
        """
        try:
            containers = self.docker_client.containers.list(filters={"ancestor": self.GRAFANA_IMAGE})
            if containers:
                container = containers[0]
                ports = container.ports or {}
                http_port = f"{self.GRAFANA_PORT}/tcp"
                
                if http_port in ports:
                    port_bindings = ports[http_port]
                    host_port = port_bindings[0]["HostPort"] if port_bindings else self.GRAFANA_PORT
                    host = f"http://localhost:{host_port}"
                    
                    return {
                        "status": "running",
                        "container_id": container.short_id,
                        "host": host,
                        "port": host_port,
                        "state": container.status
                    }
            
            return {"status": "not_running"}
            
        except Exception as e:
            logger.error(f"Error checking Grafana status: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def setup_grafana(self, port: int = 3000, volume: str = "grafana-storage") -> Dict[str, Any]:
        """Set up a Grafana container with default configuration.
        
        Args:
            port: Host port to bind Grafana to
            volume: Name of the volume to use for persistent storage
            
        Returns:
            Dict with setup status and connection details
        """
        try:
            # Check if Grafana is already running
            status = await self.is_grafana_running()
            if status["status"] == "running":
                return {
                    "success": True,
                    "message": "Grafana is already running",
                    "details": status
                }
            
            # Pull the Grafana image if not present
            try:
                self.docker_client.images.pull(self.GRAFANA_IMAGE)
            except Exception as e:
                logger.warning(f"Could not pull Grafana image: {str(e)}")
            
            # Create a volume for persistent storage if it doesn't exist
            volumes = self.docker_client.volumes.list()
            if volume not in [v.name for v in volumes]:
                self.docker_client.volumes.create(volume)
            
            # Start the Grafana container with custom configuration
            container = self.docker_client.containers.run(
                self.GRAFANA_IMAGE,
                ports={"3000/tcp": port},  # Map internal 3000 to host port
                volumes={volume: {"bind": "/var/lib/grafana", "mode": "rw"}},
                detach=True,
                name="grafana",
                environment={
                    "GF_SECURITY_ADMIN_USER": self.DEFAULT_USER,
                    "GF_SECURITY_ADMIN_PASSWORD": self.DEFAULT_PASSWORD,
                    "GF_USERS_ALLOW_SIGN_UP": "false"
                }
            )
            
            return {
                "success": True,
                "message": "Grafana container started successfully",
                "details": {
                    "container_id": container.id,
                    "host": f"http://localhost:{port}",
                    "username": self.DEFAULT_USER,
                    "password": self.DEFAULT_PASSWORD,
                    "note": "Please change the default password on first login"
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to set up Grafana: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "details": str(e)
            }
    
    async def get_grafana_dashboard(self, dashboard_uid: str, host: str = None, 
                                 auth: tuple = None) -> Dict[str, Any]:
        """Get a Grafana dashboard by UID.
        
        Args:
            dashboard_uid: UID of the dashboard to retrieve
            host: Grafana host URL (default: auto-detect)
            auth: Tuple of (username, password) for authentication
            
        Returns:
            Dict with dashboard data or error information
        """
        try:
            if not host:
                status = await self.is_grafana_running()
                if status["status"] != "running":
                    return {"error": "Grafana is not running"}
                host = status["host"]
            
            if not auth:
                auth = (self.DEFAULT_USER, self.DEFAULT_PASSWORD)
            
            url = urljoin(host, f"/api/dashboards/uid/{dashboard_uid}")
            response = requests.get(url, auth=auth)
            response.raise_for_status()
            
            return {
                "success": True,
                "dashboard": response.json()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to fetch dashboard: {str(e)}",
                "status_code": getattr(e.response, 'status_code', None)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }
    
    @staticmethod
    def get_grafana_documentation() -> Dict[str, Any]:
        """Get comprehensive Grafana documentation for home automation monitoring.
        
        Returns:
            Dict with documentation sections and content
        """
        return {
            "what_is_grafana": {
                "title": "Grafana for Home Automation",
                "content": (
                    "Grafana is an open-source platform that transforms your home automation data into "
                    "beautiful, real-time dashboards. It's perfect for monitoring security cameras, "
                    "smart devices, and environmental sensors throughout your home."
                )
            },
            "key_features": {
                "title": "Key Features for Home Monitoring",
                "items": [
                    "Real-time camera feeds and motion detection alerts",
                    "Environmental monitoring (temperature, humidity, air quality)",
                    "Smart device status and energy usage tracking",
                    "Custom dashboards for different areas of your home",
                    "Mobile-friendly interface for remote monitoring",
                    "Alerting for security and maintenance issues"
                ]
            },
            "getting_started": {
                "title": "Getting Started with Home Monitoring",
                "steps": [
                    "1. Start Grafana: 'await setup_grafana()'",
                    "2. Access Grafana at http://localhost:13000 (admin/admin)",
                    "3. Add your data sources (e.g., MQTT, InfluxDB, Prometheus)",
                    "4. Import home automation dashboards or create custom ones",
                    "5. Set up alerts for motion detection or sensor thresholds"
                ]
            },
            "recommended_integrations": {
                "title": "Recommended Integrations",
                "items": [
                    "Cameras: RTSP/ONVIF compatible cameras with motion detection",
                    "Sensors: Temperature, humidity, motion, and door/window sensors",
                    "Smart Home: Home Assistant, OpenHAB, or Node-RED integration",
                    "Data Storage: InfluxDB for time-series data, PostgreSQL for events",
                    "Alerting: Push notifications, email, or SMS alerts"
                ]
            },
            "example_dashboards": {
                "title": "Example Home Dashboards",
                "items": [
                    "Security Overview: Camera feeds, motion events, and door/window status",
                    "Environmental: Temperature, humidity, and air quality trends",
                    "Energy Usage: Smart plug and appliance monitoring",
                    "Network: Internet speed and device connectivity"
                ]
            },
            "resources": {
                "title": "Useful Resources",
                "items": [
                    "Grafana Home Automation Guide: https://grafana.com/grafana/dashboards/?search=home+automation",
                    "Home Assistant Integration: https://www.home-assistant.io/integrations/grafana/",
                    "Community Dashboards: https://grafana.com/grafana/dashboards/",
                    "Alerting Setup: https://grafana.com/docs/grafana/latest/alerting/"
                ]
            }
        }
