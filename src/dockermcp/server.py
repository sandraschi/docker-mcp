#!/usr/bin/env python3
"""
Docker MCP Server - Main Entry Point

This module initializes and runs the Docker MCP server with FastMCP 2.11.3 compatibility
and stateful features.
"""
import asyncio
import logging
import os
import sys
import warnings
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from dockermcp.utils.json_utils import safe_json_loads, safe_json_dumps

# Suppress Pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Add the parent directory to the Python path
src_dir = str(Path(__file__).parent.parent.absolute())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure logging to capture warnings
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Send logs to stderr to avoid mixing with JSON output
)
logger = logging.getLogger(__name__)

# Redirect warnings to the logger
def warn_with_log(message, category, filename, lineno, file=None, line=None):
    logger.warning(f"{filename}:{lineno}: {category.__name__}: {message}")

warnings.showwarning = warn_with_log

# Import FastMCP after configuring logging
from fastmcp import FastMCP
import traceback

class SafeFastMCP(FastMCP):
    """Extended FastMCP class with enhanced error handling."""
    
    async def _handle_message(self, message: str) -> str:
        """Handle incoming JSON-RPC messages with proper error handling."""
        try:
            # Log the raw message for debugging
            logger.debug(f"Received message: {message[:200]}..." if len(message) > 200 else f"Received message: {message}")
            
            # Check for common issues
            if not message.strip():
                logger.warning("Received empty message")
                return ''
                
            if message.startswith('Warning:') or message.startswith('Error:'):
                logger.warning(f"Received warning/error message: {message}")
                return ''
                
            # Clean and parse the message
            message = message.strip()
            
            # Skip empty messages or warnings
            if not message or message.startswith(('WARNING:', 'Warning:')):
                logger.warning(f"Skipping message: {message[:200]}...")
                return ''
                
            # Parse the message using our safe JSON loader
            parsed = safe_json_loads(message, context="incoming message")
            if parsed is None:
                return {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error: Invalid JSON"
                    }
                }
            return parsed
            
            # Process the message normally
            return await super()._handle_message(message)
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

# Initialize FastMCP with built-in state management and custom error handling
mcp = SafeFastMCP(
    name="DockerMCP",
    version="2.11.0"
)

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
