"""
Docker MCP Server - Main entry point.

This module initializes and runs the Docker MCP server.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
src_dir = str(Path(__file__).parent.absolute())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

from fastmcp import FastMCP
from .json_encoder import dumps as custom_dumps, loads as custom_loads

# Import API endpoints to register them
try:
    from dockermcp.api import containers
except ImportError:
    # Fallback for direct script execution
    from api import containers

# Configure logging
s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def main():
    """Initialize and run the Docker MCP server."""
    try:
logger.info("=== Docker MCP Server Starting ===")
logger.info(f"Python Path: {sys.path}")
        
        # Initialize FastMCP with custom JSON encoder
logger.info("Initializing FastMCP...")
        mcp = FastMCP(
            name="docker-mcp",
            version="1.0.0",
            description="Docker Management and Control Plane",
            json_dumps=custom_dumps,
            json_loads=custom_loads
        )
        
        logger.info("Starting Docker MCP server...")
logger.info("MCP server initialized. Starting main loop...")
        mcp.run()
        
    except Exception as e:
        import traceback
logger.info(f"=== ERROR: {str(e)}")
logger.info("Stack trace:")
        traceback.print_exc()
        logger.error(f"Failed to start Docker MCP server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
