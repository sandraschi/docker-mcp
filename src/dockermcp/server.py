#!/usr/bin/env python3
"""
Docker MCP Server - Main Entry Point

This module initializes and runs the Docker MCP server with FastMCP 3.1+ compatibility.
Includes both MCP stdio transport and FastAPI HTTP server for the webapp.
"""
import asyncio
import logging
import sys
import warnings
from pathlib import Path
from typing import List, Tuple, Callable
import threading

# Suppress Pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Import local modules
from dockermcp.logging_config import configure_logging, logger
from dockermcp.tools.assorted_crap import SafeFastMCP, SafeJSONEncoder, warn_with_log

# Configure logging with JSON format and proper stream handling
# Disable JSON for RPC logs to prevent parsing issues
configure_logging(
    enable_console=True,
    json_format=True,
    log_file=str(Path("logs/dockermcp.log")),
    disable_json_for_rpc=True
)

# Get logger for this module
logger = logging.getLogger('dockermcp.server')

# Redirect warnings to the logger
warnings.showwarning = warn_with_log

# Get the singleton FastMCP instance
from .transport import run_server, run_server_async
from .mcp_instance import get_mcp
mcp = get_mcp()

# Override the default JSON encoder
mcp.json_encoder = SafeJSONEncoder()

# Log that we're using the singleton instance
logger.info("Using singleton FastMCP instance from mcp_instance.py")

# Import tool modules to register them with @mcp.tool decorators
try:
    # Import tool modules - these will be registered via @mcp.tool decorators
    from dockermcp.tools.containers import list_containers
    # from dockermcp.tools.workflows import workflow_management  # TEMPORARILY DISABLED - SYNTAX ERROR
    from dockermcp.tools.networks import network_management
    from dockermcp.tools.volumes import volume_management
    from dockermcp.tools.system import system_management
    from dockermcp.tools import agentic_container_workflow  # SEP-1577 agentic workflows
    
    # Import desktop tools
    from dockermcp.tools.desktop import (
        docker_desktop_status,
        docker_daemon_recover,
        docker_daemon_restart,
        docker_desktop_update,
    )

    # Log successful imports
    logger.info("Successfully imported all tool modules including Docker Desktop tools and SEP-1577 agentic workflows")

except ImportError as e:
    logger.error(f"Failed to import tool modules: {e}", exc_info=True)
    sys.exit(1)

def run_fastapi_server():
    """Run FastAPI server in a separate thread"""
    import uvicorn
    from dockermcp.api.app import create_app
    
    app = create_app()
    logger.info("Starting FastAPI server on port 10807...")
    uvicorn.run(app, host="127.0.0.1", port=10807, log_level="warning")

def main() -> None:
    """Initialize and run the Docker MCP server with stdio transport and FastAPI HTTP."""
    try:
        # Start FastAPI server in a background thread
        fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=True)
        fastapi_thread.start()
        logger.info("FastAPI server started in background thread")
        
        # Give FastAPI time to start
        import time
        time.sleep(2)
        
        # Start MCP stdio server
        logger.info("Starting Docker MCP server with stdio transport...")
        asyncio.run(run_server(mcp, server_name="docker-mcp"))
    except KeyboardInterrupt:
        logger.info("Shutting down Docker MCP server...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
