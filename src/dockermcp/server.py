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

# Import all tool modules
try:
    # Import tool modules
    from dockermcp.tools.containers.list_containers import list_containers
    from dockermcp.tools.workflows.workflow_management import (
        create_workflow,
        start_workflow,
        stop_workflow,
        get_workflow_status
    )
    from dockermcp.tools.networks.network_management import (
        list_networks,
        create_network,
        remove_network,
        connect_container_to_network,
        disconnect_container_from_network
    )
    from dockermcp.tools.volumes.volume_management import (
        list_volumes,
        create_volume,
        remove_volume,
        prune_volumes
    )
    from dockermcp.tools.system.system_management import (
        get_system_info,
        get_disk_usage,
        prune_system
    )
    
    # Register all tools with FastMCP
    # Container tools
    mcp.register_tool(list_containers)
    
    # Workflow tools
    mcp.register_tool(create_workflow)
    mcp.register_tool(start_workflow)
    mcp.register_tool(stop_workflow)
    mcp.register_tool(get_workflow_status)
    
    # Network tools
    mcp.register_tool(list_networks)
    mcp.register_tool(create_network)
    mcp.register_tool(remove_network)
    mcp.register_tool(connect_container_to_network)
    mcp.register_tool(disconnect_container_from_network)
    
    # Volume tools
    mcp.register_tool(list_volumes)
    mcp.register_tool(create_volume)
    mcp.register_tool(remove_volume)
    mcp.register_tool(prune_volumes)
    
    # System tools
    mcp.register_tool(get_system_info)
    mcp.register_tool(get_disk_usage)
    mcp.register_tool(prune_system)
    
    logger.info("Successfully registered all tools with FastMCP")
    
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
