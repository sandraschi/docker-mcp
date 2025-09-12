"""
Docker MCP Server - Main entry point.

This module initializes and runs the Docker MCP server.
"""
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
src_dir = str(Path(__file__).parent.absolute())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from dockermcp.logging_config import configure_logging, logger

# Configure logging
configure_logging()

# Import the MCP instance first to ensure it's created
from .mcp_instance import get_mcp

# Import API endpoints to register them
try:
    from dockermcp.api import containers
except ImportError:
    # Fallback for direct script execution
    from api import containers

# Import tools to ensure they're registered with the MCP instance
try:
    from dockermcp import tools  # This will register all tools via the import
    logger.info("Successfully imported tools")
except ImportError as e:
    logger.error(f"Failed to import tools: {e}", exc_info=True)
    raise

def main():
    """Initialize and run the Docker MCP server."""
    try:
        # Configure root logger to be silent
        logging.basicConfig(
            level=logging.CRITICAL,
            force=True,
            handlers=[logging.NullHandler()]
        )
        
        # Silence common noisy loggers
        for logger_name in ['fastmcp', 'mcp', 'uvicorn', 'httpx', 'httpcore', 'h11', 'asyncio']:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        
        logger.info("=== Docker MCP Server Starting ===")
        logger.info(f"Python Path: {sys.path}")
        
        # Get the singleton instance
        logger.info("Getting FastMCP instance...")
        mcp = get_mcp()
        
        # Configure FastMCP logging
        mcp.logger.setLevel("CRITICAL")
        
        logger.info("MCP server initialized. Starting main loop...")
        
        # Run with proper logging configuration
        mcp.run(
            log_level="CRITICAL",
            json_response=True
        )
        
    except Exception as e:
        import traceback
        logger.error(f"=== ERROR: {str(e)}")
        logger.error("Stack trace:")
        logger.error(traceback.format_exc())
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
