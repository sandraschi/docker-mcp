#!/usr/bin/env python3
"""
Docker MCP Server - Main Entry Point

This module initializes and runs the Docker MCP server with FastMCP 2.12.0 compatibility.
All tool implementations have been moved to their respective modules in the tools/ directory.
"""
import asyncio
import logging
import sys
import warnings
from pathlib import Path
from typing import List, Tuple, Callable

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

    # Log successful imports
    logger.info("Successfully imported all tool modules including SEP-1577 agentic workflows")

except ImportError as e:
    logger.error(f"Failed to import tool modules: {e}", exc_info=True)
    sys.exit(1)

def main() -> None:
    """Initialize and run the Docker MCP server with stdio transport."""
    try:
        logger.info("Starting Docker MCP server with stdio transport...")
        asyncio.run(mcp.run_stdio_async())
    except KeyboardInterrupt:
        logger.info("Shutting down Docker MCP server...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
