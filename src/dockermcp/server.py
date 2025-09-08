#!/usr/bin/env python3
"""
Docker MCP Server - Main Entry Point

This module initializes and runs the Docker MCP server with FastMCP 2.12.0 compatibility
and stateful features.
"""
import json
import logging
import os
import sys
import traceback
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# Suppress Pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Configure logging to stderr only
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]  # CRITICAL: stderr not stdout
)

# Import FastMCP after initial logging setup
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Import local modules
from dockermcp.logging_config import configure_logging
from dockermcp.utils.json_utils import safe_json_loads, safe_json_dumps

# Configure logging with our centralized config
configure_logging()
logger = logging.getLogger(__name__)

# Redirect warnings to the logger
def warn_with_log(message, category, filename, lineno, file=None, line=None):
    logger.warning(f"{filename}:{lineno}: {category.__name__}: {message}")

warnings.showwarning = warn_with_log

class SafeFastMCP(FastMCP):
    """Extended FastMCP class with enhanced error handling."""
    
    async def _handle_message(self, message: str) -> str:
        """Handle incoming JSON-RPC messages with proper error handling."""
        try:
            # Log the raw message for debugging
            if message and len(message) > 200:
                logger.debug(f"Received message (truncated): {message[:200]}...")
            elif message:
                logger.debug(f"Received message: {message}")
            
            # Check for common issues
            if not message or not message.strip():
                logger.warning("Received empty message")
                return ''
                
            if message.startswith(('Warning:', 'Error:')):
                logger.warning(f"Received warning/error message: {message}")
                return ''
                
            # Clean and parse the message
            message = message.strip()
            
            # Skip empty messages or warnings
            if not message or message.startswith(('WARNING:', 'Warning:')):
                logger.warning(f"Skipping message: {message[:200]}...")
                return ''
                
            # Process the message normally
            return await super()._handle_message(message)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}", exc_info=True)
            return safe_json_dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            })
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return safe_json_dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            })

# Initialize FastMCP with built-in state management and custom error handling
mcp = SafeFastMCP(
    name="DockerMCP",
    version="2.12.0"
)

# Import and register tools
from dockermcp.tools.containers import (
    list_containers,
    create_container,
    start_container,
    stop_container,
    restart_container,
    remove_container,
    inspect_container,
    container_logs,
    execute_in_container
)

# Register container tools
mcp.tool(list_containers)
mcp.tool(create_container)
mcp.tool(start_container)
mcp.tool(stop_container)
mcp.tool(restart_container)
mcp.tool(remove_container)
mcp.tool(inspect_container)
mcp.tool(container_logs)
mcp.tool(execute_in_container)

def main():
    """Initialize and run the Docker MCP server."""
    try:
        logger.info("Starting Docker MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Docker MCP server...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

# Custom JSON encoder that handles common types
class SafeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'model_dump_json'):
            return json.loads(obj.model_dump_json())
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'total_seconds'):
            return obj.total_seconds()
        return super().default(obj)

# Override the default JSON encoder
mcp.json_encoder = SafeJSONEncoder

# Import tools
try:
    # Try absolute import first (when run as module)
    from dockermcp.tools import containers, networks, volumes, system, workflow
except ImportError:
    try:
        # Try relative import (when run directly)
        from .tools import containers, networks, volumes, system, workflow
    except ImportError:
        # Fallback to direct import from tools directory
        from tools import containers, networks, volumes, system, workflow

def main():
    """Initialize and run the Docker MCP server."""
    try:
        logger.info("Starting Docker MCP server...")
        
        # Run the MCP server with stdio communication
        asyncio.run(mcp.serve())
        
    except Exception as e:
        logger.error(f"Failed to start Docker MCP server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
