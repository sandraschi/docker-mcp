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
logger = logger.getChild('server')

# Redirect warnings to the logger
warnings.showwarning = warn_with_log

# Get the singleton FastMCP instance
from .mcp_instance import get_mcp
mcp = get_mcp()

# Override the default JSON encoder
mcp.json_encoder = SafeJSONEncoder()

# Log that we're using the singleton instance
logger.info("Using singleton FastMCP instance from mcp_instance.py")

# Import all tool modules
try:
    # Import tool modules
    from dockermcp.tools.containers import get_container_tools
    from dockermcp.tools.workflow import get_tools as get_workflow_tools
    from dockermcp.tools.networks import get_tools as get_network_tools
    from dockermcp.tools.volumes import get_tools as get_volume_tools
    from dockermcp.tools.system import get_tools as get_system_tools
    
    # Register all tools
    tool_modules: List[Tuple[str, List[Callable]]] = [
        ('Container', get_container_tools()),
        ('Workflow', get_workflow_tools()),
        ('Network', get_network_tools()),
        ('Volume', get_volume_tools()),
        ('System', get_system_tools())
    ]
    
    # Register tools and log registration
    for module_name, tools in tool_modules:
        logger.info(f"Registering {len(tools)} {module_name} tools")
        for tool in tools:
            mcp.tool(tool)
    
    logger.info("All tools registered successfully")
    
except ImportError as e:
    logger.error(f"Failed to import tool modules: {e}")
    raise

def main() -> None:
    """Initialize and run the Docker MCP server."""
    try:
        logger.info("Starting Docker MCP server...")
        
        # Run the MCP server with stdio communication
        asyncio.run(mcp.serve())
        
    except KeyboardInterrupt:
        logger.info("Shutting down Docker MCP server...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
