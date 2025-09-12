"""
Web Interface Tools for Monitoring Stack

This module provides tools to access the web interfaces of the monitoring stack.
"""
import webbrowser
from typing import Dict, Any, Optional

from fastmcp.tools import Tool
from dockermcp.tools.monitoring import monitoring_manager

@Tool(
    name="open_grafana",
    description="Open the Grafana web interface in the default browser",
    parameters={
        'type': 'object',
        'properties': {
            'port': {
                'type': 'integer',
                'default': 3000,
                'description': 'Port number for Grafana'
            },
            'path': {
                'type': 'string',
                'default': '',
                'description': 'Additional path to open in Grafana (e.g., /dashboards)'
            }
        }
    }
)
async def open_grafana(port: int = 3000, path: str = '') -> Dict[str, Any]:
    """
    Open the Grafana web interface in the default browser.
    
    Args:
        port: Port number for Grafana
        path: Additional path to open in Grafana
        
    Returns:
        Dictionary with the result of the operation
        
    Example:
        >>> await open_grafana()
        {
            'status': 'success',
            'message': 'Opened Grafana in browser',
            'url': 'http://localhost:3000'
        }
    """
    try:
        url = f"http://localhost:{port}{path}"
        webbrowser.open(url)
        return {
            "status": "success",
            "message": "Opened Grafana in browser",
            "url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to open Grafana: {str(e)}",
            "url": url
        }

@Tool(
    name="open_prometheus",
    description="Open the Prometheus web interface in the default browser",
    parameters={
        'type': 'object',
        'properties': {
            'port': {
                'type': 'integer',
                'default': 9090,
                'description': 'Port number for Prometheus'
            },
            'path': {
                'type': 'string',
                'default': '',
                'description': 'Additional path to open in Prometheus'
            }
        }
    }
)
async def open_prometheus(port: int = 9090, path: str = '') -> Dict[str, Any]:
    """
    Open the Prometheus web interface in the default browser.
    
    Args:
        port: Port number for Prometheus
        path: Additional path to open in Prometheus
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        url = f"http://localhost:{port}{path}"
        webbrowser.open(url)
        return {
            "status": "success",
            "message": "Opened Prometheus in browser",
            "url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to open Prometheus: {str(e)}",
            "url": url
        }

@Tool(
    name="open_loki",
    description="Open the Loki web interface in the default browser",
    parameters={
        'type': 'object',
        'properties': {
            'port': {
                'type': 'integer',
                'default': 3100,
                'description': 'Port number for Loki'
            },
            'path': {
                'type': 'string',
                'default': '',
                'description': 'Additional path to open in Loki'
            }
        }
    }
)
async def open_loki(port: int = 3100, path: str = '') -> Dict[str, Any]:
    """
    Open the Loki web interface in the default browser.
    
    Args:
        port: Port number for Loki
        path: Additional path to open in Loki
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        url = f"http://localhost:{port}{path}"
        webbrowser.open(url)
        return {
            "status": "success",
            "message": "Opened Loki in browser",
            "url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to open Loki: {str(e)}",
            "url": url
        }

@Tool(
    name="open_monitoring_dashboard",
    description="Open a specific monitoring dashboard in the default browser",
    parameters={
        'type': 'object',
        'properties': {
            'dashboard': {
                'type': 'string',
                'enum': ['overview', 'docker', 'host', 'applications', 'custom'],
                'default': 'overview',
                'description': 'Type of dashboard to open'
            },
            'port': {
                'type': 'integer',
                'default': 3000,
                'description': 'Port number for Grafana'
            },
            'custom_path': {
                'type': 'string',
                'description': 'Custom dashboard path (only used when dashboard is "custom")'
            }
        },
        'required': ['dashboard']
    }
)
async def open_monitoring_dashboard(
    dashboard: str = 'overview',
    port: int = 3000,
    custom_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Open a monitoring dashboard in the default browser.
    
    Args:
        dashboard: Type of dashboard to open (overview, docker, host, applications, custom)
        port: Port number for Grafana
        custom_path: Custom dashboard path (only used when dashboard is "custom")
        
    Returns:
        Dictionary with the result of the operation
        
    Example:
        >>> await open_monitoring_dashboard(dashboard="docker")
        {
            'status': 'success',
            'message': 'Opened Docker dashboard in browser',
            'url': 'http://localhost:3000/d/edg_docker/docker-resource-monitoring'
        }
    """
    try:
        # Dashboard UIDs for pre-configured dashboards
        dashboard_paths = {
            'overview': '/d/edg_overview/overview',
            'docker': '/d/edg_docker/docker-resource-monitoring',
            'host': '/d/edg_host/host-metrics',
            'applications': '/d/edg_applications/application-metrics',
            'custom': custom_path or ''
        }
        
        if dashboard not in dashboard_paths:
            return {
                "status": "error",
                "error": f"Unknown dashboard type: {dashboard}",
                "available_dashboards": list(dashboard_paths.keys())
            }
        
        path = dashboard_paths[dashboard]
        url = f"http://localhost:{port}{path}"
        webbrowser.open(url)
        
        return {
            "status": "success",
            "message": f"Opened {dashboard} dashboard in browser",
            "url": url,
            "dashboard": dashboard
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to open {dashboard} dashboard: {str(e)}",
            "dashboard": dashboard
        }
