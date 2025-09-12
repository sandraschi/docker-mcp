"""
Monitoring Tools for DockerMCP

This module provides tools for managing the monitoring stack (Prometheus, Grafana, Loki, etc.).
"""
from typing import Dict, Any, List, Optional
import subprocess
import logging
from pathlib import Path

from dockermcp.mcp_instance import mcp
from dockermcp.logging_config import logger

class MonitoringManager:
    """Manages the monitoring stack."""
    
    def __init__(self):
        self.monitoring_dir = Path(__file__).parent.parent.parent.parent.parent / "monitoring"
        self.compose_file = self.monitoring_dir / "docker-compose-monitoring.yml"
        self.compose_cmd = ["docker-compose", "-f", str(self.compose_file)]
    
    def run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.monitoring_dir),
                capture_output=True,
                text=True,
                check=False
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "command": " ".join(cmd)
            }
    
    def start_services(self) -> Dict[str, Any]:
        """Start the monitoring services."""
        return self.run_command(self.compose_cmd + ["up", "-d"])
    
    def stop_services(self) -> Dict[str, Any]:
        """Stop the monitoring services."""
        return self.run_command(self.compose_cmd + ["down"])
    
    def restart_services(self) -> Dict[str, Any]:
        """Restart the monitoring services."""
        self.stop_services()
        return self.start_services()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of monitoring services."""
        return self.run_command(self.compose_cmd + ["ps"])
    
    def get_logs(self, service: Optional[str] = None, tail: int = 100) -> Dict[str, Any]:
        """Get logs from monitoring services."""
        cmd = self.compose_cmd + ["logs", f"--tail={tail}"]
        if service:
            cmd.append(service)
        return self.run_command(cmd)

# Create a singleton instance
monitoring_manager = MonitoringManager()

@mcp.tool(
    name="start_monitoring",
    description="Start the monitoring stack (Prometheus, Grafana, Loki, etc.)",
    parameters={
        'type': 'object',
        'properties': {
            'build': {
                'type': 'boolean',
                'description': 'Whether to rebuild the container images',
                'default': False
            }
        },
        'required': []
    }
)
async def start_monitoring(build: bool = False) -> Dict[str, Any]:
    """
    Start the monitoring stack including Prometheus, Grafana, Loki, and other services.
    
    Args:
        build: Whether to rebuild the container images
        
    Returns:
        Dictionary with the result of the operation
        
    Example:
        >>> await start_monitoring()
        {
            'status': 'success',
            'message': 'Monitoring services started',
            'services': ['prometheus', 'grafana', 'loki', 'promtail', 'redis']
        }
    """
    try:
        if build:
            result = monitoring_manager.run_command(
                monitoring_manager.compose_cmd + ["build"]
            )
            if result["status"] == "error":
                return result
        
        result = monitoring_manager.start_services()
        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Monitoring services started",
                "details": result["stdout"],
                "services": ["prometheus", "grafana", "loki", "promtail", "redis"]
            }
        return {
            "status": "error",
            "error": f"Failed to start monitoring services: {result.get('stderr', 'Unknown error')}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error starting monitoring services: {str(e)}"
        }

@mcp.tool(
    name="stop_monitoring",
    description="Stop the monitoring stack",
    parameters={
        'type': 'object',
        'properties': {
            'remove_volumes': {
                'type': 'boolean',
                'default': False,
                'description': 'Whether to remove volumes when stopping'
            }
        }
    }
)
async def stop_monitoring(remove_volumes: bool = False) -> Dict[str, Any]:
    """
    Stop the monitoring stack.
    
    Args:
        remove_volumes: Whether to remove volumes when stopping
        
    Returns:
        Dictionary with the result of the operation
        
    Example:
        >>> await stop_monitoring()
        {
            'status': 'success',
            'message': 'Monitoring services stopped'
        }
    """
    try:
        cmd = monitoring_manager.compose_cmd + ["down"]
        if remove_volumes:
            cmd.append("-v")
            
        result = monitoring_manager.run_command(cmd)
        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Monitoring services stopped",
                "details": result["stdout"]
            }
        return {
            "status": "error",
            "error": f"Failed to stop monitoring services: {result.get('stderr', 'Unknown error')}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error stopping monitoring services: {str(e)}"
        }

@mcp.tool(
    name="monitoring_status",
    description="Get the status of the monitoring stack",
    parameters={
        'type': 'object',
        'properties': {
            'detailed': {
                'type': 'boolean',
                'default': False,
                'description': 'Whether to include detailed container information'
            }
        }
    }
)
async def monitoring_status(detailed: bool = False) -> Dict[str, Any]:
    """
    Get the status of the monitoring stack.
    
    Args:
        detailed: Whether to include detailed container information
        
    Returns:
        Dictionary with the status of monitoring services
        
    Example:
        >>> await monitoring_status()
        {
            'status': 'success',
            'services': [
                {'name': 'prometheus', 'status': 'running'},
                {'name': 'grafana', 'status': 'running'},
                {'name': 'loki', 'status': 'running'},
                {'name': 'promtail', 'status': 'running'},
                {'name': 'redis', 'status': 'running'}
            ]
        }
    """
    try:
        if detailed:
            result = monitoring_manager.run_command(
                ["docker", "ps", "--filter", "name=monitoring_", "--format", "{{.Names}}|{{.Status}}"]
            )
        else:
            result = monitoring_manager.get_status()
        
        if result["status"] != "success":
            return result
        
        # Parse the output
        services = []
        for line in result["stdout"].splitlines():
            if "|" in line:
                name, status = line.split("|", 1)
                services.append({"name": name, "status": status})
        
        return {
            "status": "success",
            "services": services or [{"error": "No monitoring services found or not running"}],
            "raw_output": result["stdout"] if detailed else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error getting monitoring status: {str(e)}"
        }

@mcp.tool(
    name="monitoring_logs",
    description="Get logs from monitoring services",
    parameters={
        'type': 'object',
        'properties': {
            'service': {
                'type': 'string',
                'description': 'Name of the service to get logs from (optional)'
            },
            'tail': {
                'type': 'integer',
                'default': 100,
                'description': 'Number of lines to show from the end of the logs'
            },
            'follow': {
                'type': 'boolean',
                'default': False,
                'description': 'Follow log output'
            }
        }
    }
)
async def monitoring_logs(service: Optional[str] = None, tail: int = 100, follow: bool = False) -> Dict[str, Any]:
    """
    Get logs from monitoring services.
    
    Args:
        service: Name of the service to get logs from (optional)
        tail: Number of lines to show from the end of the logs
        follow: Whether to follow the log output
        
    Returns:
        Dictionary with the logs
        
    Example:
        >>> await monitoring_logs(service="grafana", tail=50)
        {
            'status': 'success',
            'service': 'grafana',
            'logs': '...last 50 lines of logs...'
        }
    """
    try:
        cmd = monitoring_manager.compose_cmd + ["logs", f"--tail={tail}"]
        if follow:
            cmd.append("-f")
        if service:
            cmd.append(service)
            
        result = monitoring_manager.run_command(cmd)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "service": service or "all",
                "logs": result["stdout"] or "No logs available"
            }
        return {
            "status": "error",
            "error": f"Failed to get logs: {result.get('stderr', 'Unknown error')}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error getting logs: {str(e)}"
        }
