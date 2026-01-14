"""
Web Interface Tools for Monitoring Stack

This module provides tools to access the web interfaces of the monitoring stack.
"""
import webbrowser
from typing import Dict, Any, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError

from dockermcp.mcp_instance import mcp
from dockermcp.logging_config import logger

class OpenGrafanaParams(BaseModel):
    """Parameters for opening Grafana web interface."""
    port: int = Field(
        3000,
        ge=1,
        le=65535,
        description="Port number for Grafana"
    )
    path: str = Field(
        "",
        description="Additional path to open in Grafana (e.g., /dashboards)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "port": 3000,
                "path": "/dashboards"
            }
        }
    )

@mcp.tool
async def open_grafana(params: OpenGrafanaParams) -> Dict[str, Any]:
    """
    Open the Grafana web interface in the default browser.
    
    Args:
        params: OpenGrafanaParams containing connection details
        
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
        url = f"http://localhost:{params.port}{params.path}"
        webbrowser.open(url)
        logger.info(f"Opened Grafana at {url}")
        return {
            "status": "success",
            "message": "Opened Grafana in browser",
            "url": url
        }
    except Exception as e:
        error_msg = f"Failed to open Grafana: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg,
            "url": f"http://localhost:{params.port}{params.path}"
        }

class OpenPrometheusParams(BaseModel):
    """Parameters for opening Prometheus web interface."""
    port: int = Field(
        9090,
        ge=1,
        le=65535,
        description="Port number for Prometheus"
    )
    path: str = Field(
        "",
        description="Additional path to open in Prometheus"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "port": 9090,
                "path": "/graph"
            }
        }
    )

@mcp.tool
async def open_prometheus(params: OpenPrometheusParams) -> Dict[str, Any]:
    """
    Open the Prometheus web interface in the default browser.
    
    Args:
        params: OpenPrometheusParams containing connection details
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        url = f"http://localhost:{params.port}{params.path}"
        webbrowser.open(url)
        logger.info(f"Opened Prometheus at {url}")
        return {
            "status": "success",
            "message": "Opened Prometheus in browser",
            "url": url
        }
    except Exception as e:
        error_msg = f"Failed to open Prometheus: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg,
            "url": f"http://localhost:{params.port}{params.path}"
        }

class OpenLokiParams(BaseModel):
    """Parameters for opening Loki web interface."""
    port: int = Field(
        3100,
        ge=1,
        le=65535,
        description="Port number for Loki"
    )
    path: str = Field(
        "",
        description="Additional path to open in Loki"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "port": 3100,
                "path": "/explore"
            }
        }
    )

@mcp.tool
async def open_loki(params: OpenLokiParams) -> Dict[str, Any]:
    """
    Open the Loki web interface in the default browser.
    
    Args:
        params: OpenLokiParams containing connection details
        
    Returns:
        Dictionary with the result of the operation
    """
    try:
        url = f"http://localhost:{params.port}{params.path}"
        webbrowser.open(url)
        logger.info(f"Opened Loki at {url}")
        return {
            "status": "success",
            "message": "Opened Loki in browser",
            "url": url
        }
    except Exception as e:
        error_msg = f"Failed to open Loki: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg,
            "url": f"http://localhost:{params.port}{params.path}"
        }

class OpenMonitoringDashboardParams(BaseModel):
    """Parameters for opening a monitoring dashboard."""
    dashboard: Literal['overview', 'docker', 'host', 'applications', 'custom'] = Field(
        'overview',
        description='Type of dashboard to open'
    )
    port: int = Field(
        3000,
        ge=1,
        le=65535,
        description='Port number for Grafana'
    )
    custom_path: Optional[str] = Field(
        None,
        description='Custom dashboard path (only used when dashboard is "custom")'
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dashboard": "docker",
                "port": 3000,
                "custom_path": None
            }
        }
    )

@mcp.tool
async def open_monitoring_dashboard(params: OpenMonitoringDashboardParams) -> Dict[str, Any]:
    """
    Open a monitoring dashboard in the default browser.
    
    Args:
        params: OpenMonitoringDashboardParams containing dashboard configuration
        
    Returns:
        Dictionary with the result of the operation
        
    Example:
        >>> await open_monitoring_dashboard(params=OpenMonitoringDashboardParams(dashboard="docker"))
        {
            'status': 'success',
            'message': 'Opened Docker dashboard in browser',
            'url': 'http://localhost:3000/d/docker'
        }
    """
    try:
        # Define dashboard paths (these should match your actual Grafana dashboard UIDs)
        dashboard_paths = {
            'overview': '/d/overview',
            'docker': '/d/docker',
            'host': '/d/host',
            'applications': '/d/applications',
            'custom': params.custom_path or ''
        }
        
        try:
            if params.dashboard not in dashboard_paths and params.dashboard != 'custom':
                error_msg = f"Unknown dashboard type: {params.dashboard}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg,
                    "available_dashboards": list(dashboard_paths.keys())
                }
                
            path = dashboard_paths[params.dashboard] if params.dashboard != 'custom' else params.custom_path
            if not path:
                error_msg = "custom_path is required when dashboard is 'custom'"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg
                }
                
            url = f"http://localhost:{params.port}{path}"
            webbrowser.open(url)
            logger.info(f"Opened {params.dashboard} dashboard at {url}")
            return {
                "status": "success",
                "message": f"Opened {params.dashboard} dashboard in browser",
                "url": url,
                "dashboard": params.dashboard
            }
        except Exception as e:
            error_msg = f"Failed to open {params.dashboard} dashboard: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "error": error_msg,
                "dashboard": params.dashboard,
                "url": f"http://localhost:{params.port}"
            }
    except Exception as e:
        error_msg = f"Failed to open {params.dashboard} dashboard: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg,
            "dashboard": params.dashboard
        }
