"""
Container tools registry for Docker MCP.

This module registers container management tools with the FastMCP server.
"""
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP
from fastmcp.tools import Tool

from .container_models import (
    ContainerLifecycleRequest,
    ContainerLifecycleResponse,
    ContainerLogsRequest,
    ContainerLogsResponse,
    ContainerExecRequest,
    ContainerExecResponse
)
from .container_lifecycle import manage_container_lifecycle
from .container_logs import stream_container_logs
from .container_exec import execute_in_container

def register_container_tools(mcp: FastMCP) -> None:
    """Register container management tools with the MCP server.
    
    Args:
        mcp: FastMCP server instance to register tools with
    """
    # Register container lifecycle tool
    mcp.register_tool(
        Tool(
            name="manage_container_lifecycle",
            description="Manage container lifecycle (start, stop, restart, remove, pause, unpause)",
            method=manage_container_lifecycle,
            input_model=ContainerLifecycleRequest,
            output_model=ContainerLifecycleResponse,
            examples=[
                {
                    "name": "Stop a container",
                    "input": {
                        "container_id": "my-container",
                        "action": "stop",
                        "timeout": 10
                    },
                    "output": {
                        "success": True,
                        "message": "Successfully stopped container my-container",
                        "container_id": "my-container",
                        "action": "stop",
                        "state": {
                            "Status": "exited",
                            "Running": False,
                            "Paused": False,
                            "Restarting": False,
                            "OOMKilled": False,
                            "Dead": False,
                            "Pid": 0,
                            "ExitCode": 0,
                            "Error": "",
                            "StartedAt": "2023-01-01T12:00:00Z",
                            "FinishedAt": "2023-01-01T12:00:10Z"
                        }
                    }
                },
                {
                    "name": "Force remove a running container",
                    "input": {
                        "container_id": "my-container",
                        "action": "remove",
                        "force": True,
                        "remove_volumes": True
                    },
                    "output": {
                        "success": True,
                        "message": "Successfully removed container my-container",
                        "container_id": "my-container",
                        "action": "remove"
                    }
                }
            ]
        )
    )
    
    # Register container logs tool
    mcp.register_tool(
        Tool(
            name="stream_container_logs",
            description="Stream logs from a container with filtering options",
            method=stream_container_logs,
            input_model=ContainerLogsRequest,
            output_model=ContainerLogsResponse,
            examples=[
                {
                    "name": "Get last 100 logs",
                    "input": {
                        "container_id": "my-container",
                        "tail": 100,
                        "timestamps": True
                    },
                    "output": {
                        "success": True,
                        "message": "Logs retrieved successfully",
                        "container_id": "my-container",
                        "logs": [
                            {
                                "timestamp": "2023-01-01T12:00:00Z",
                                "stream": "stdout",
                                "line": "Server started on port 8080"
                            },
                            {
                                "timestamp": "2023-01-01T12:00:01Z",
                                "stream": "stderr",
                                "line": "Warning: Configuration file not found"
                            }
                        ]
                    }
                },
                {
                    "name": "Follow logs in real-time",
                    "input": {
                        "container_id": "my-container",
                        "follow": True,
                        "stream_type": "stdout"
                    },
                    "output": {
                        "success": True,
                        "message": "Streaming logs from container my-container",
                        "container_id": "my-container",
                        "logs": []
                    }
                }
            ]
        )
    )
    
    # Register container exec tool
    mcp.register_tool(
        Tool(
            name="execute_in_container",
            description="Execute a command inside a running container",
            method=execute_in_container,
            input_model=ContainerExecRequest,
            output_model=ContainerExecResponse,
            examples=[
                {
                    "name": "Run a simple command",
                    "input": {
                        "container_id": "my-container",
                        "command": "ls -la /app"
                    },
                    "output": {
                        "success": True,
                        "message": "Command executed in container my-container with exit code 0",
                        "container_id": "my-container",
                        "command": "ls -la /app",
                        "result": {
                            "exit_code": 0,
                            "stdout": "total 16\ndrwxr-xr-x 1 root root 4096 Jan  1 12:00 .\ndrwxr-xr-x 1 root root 4096 Jan  1 12:00 ..\n-rw-r--r-- 1 root root  220 Jan  1 12:00 app.py\n",
                            "stderr": "",
                            "output": "total 16\ndrwxr-xr-x 1 root root 4096 Jan  1 12:00 .\ndrwxr-xr-x 1 root root 4096 Jan  1 12:00 ..\n-rw-r--r-- 1 root root  220 Jan  1 12:00 app.py\n",
                            "success": True
                        }
                    }
                },
                {
                    "name": "Run interactive shell",
                    "input": {
                        "container_id": "my-container",
                        "command": "/bin/bash",
                        "tty": True,
                        "stream": True
                    },
                    "output": {
                        "success": True,
                        "message": "Interactive shell started in container my-container",
                        "container_id": "my-container",
                        "command": "/bin/bash",
                        "result": {
                            "exit_code": 0,
                            "stdout": "",
                            "stderr": "",
                            "output": "",
                            "success": True
                        }
                    }
                }
            ]
        )
    )
