#!/usr/bin/env python3
"""
Docker MCP Server

Main entry point for the Docker MCP server using FastMCP 2.12 tool registration.
"""

import asyncio
import logging
import os
import sys
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

# Suppress all warnings
warnings.filterwarnings("ignore")

# Configure root logger to be silent
logging.basicConfig(
    level=logging.CRITICAL, force=True, handlers=[logging.NullHandler()]
)

# Silence common noisy loggers
for logger_name in ["fastmcp", "mcp", "uvicorn", "httpx", "httpcore", "h11", "asyncio"]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Import our logging configuration
from dockermcp.logging_config import configure_logging, logger
from fastmcp import FastMCP
from fastapi import FastAPI, Depends
from docker_mcp.auth import authenticate
from docker_mcp.web import setup_webapp
from docker_mcp.transport import run_server

# Configure our specific logging
configure_logging(
    enable_console=True,
    json_format=False,
    log_file=str(Path("logs/dockermcp.log")),
    level="WARNING",
)

# Use the shared MCP instance that has all tools registered (from dockermcp)
from dockermcp.mcp_instance import get_mcp
mcp = get_mcp()

# FastAPI Bridge - auth only on /api/chat so dashboard/containers work without login
web_app = FastAPI(title="Docker Management Web Bridge")

# Setup webapp bridge with the tool-loaded MCP instance
setup_webapp(web_app, mcp_app=mcp)


def get_all_tools() -> List[callable]:
    """
    Discover all FastMCP 2.12+ tools by scanning for @Tool decorated functions.

    Returns:
        List of tool functions that have been decorated with @Tool
    """
    from inspect import isfunction, getmembers
    import importlib
    import pkgutil
    from pathlib import Path

    tools_dir = Path(__file__).parent / "dockermcp" / "tools"
    tools = []

    # Skip __pycache__, __init__.py, and models
    modules = [
        name
        for _, name, is_pkg in pkgutil.iter_modules([str(tools_dir)])
        if not name.startswith("_")
        and not name == "models"
        and not name.startswith("test_")
    ]

    # Import all modules to register the tools
    for name in modules:
        try:
            module = importlib.import_module(f"dockermcp.tools.{name}")
            logger.debug(f"Imported module: dockermcp.tools.{name}")

            # Find all functions with _tool attribute (added by @Tool decorator)
            for func_name, func in getmembers(module, isfunction):
                if hasattr(func, "_tool"):
                    tools.append(func)
                    logger.debug(f"Discovered tool: {name}.{func.__name__}")

        except ImportError as e:
            logger.warning(f"Failed to import module {name}: {e}")
        except Exception as e:
            logger.error(f"Error processing module {name}: {e}", exc_info=True)

    logger.info(f"Discovered {len(tools)} tools")
    return tools


async def run_server():
    """Run the FastMCP server with all tools."""
    # Get the singleton FastMCP instance
    from dockermcp.mcp_instance import get_mcp

    mcp = get_mcp()

    # Get all tools
    tools = get_all_tools()

    # Register all tools
    for tool in tools:
        mcp.register_tool(tool)

    # Log startup information
    logger.info(f"Starting Docker MCP server with {len(tools)} tools")
    logger.info("Registered tools: " + ", ".join([t.__name__ for t in tools]))

    # Configure logging for FastMCP
    mcp.logger.setLevel("CRITICAL")  # Only show critical errors

    # Run the server with stdio transport and proper logging config
    logger.info("Starting FastMCP server with stdio transport...")
    await mcp.run_async(
        transport="stdio",
        log_level="CRITICAL",  # Ensure minimal logging
        json_response=True,  # Set JSON response formatting
    )


def main():
    """Initialize and run the Docker MCP server with all tools."""
    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Redirect stdout and stderr to log files
        sys.stdout = open(logs_dir / "stdout.log", "w")
        sys.stderr = open(logs_dir / "stderr.log", "w")

        # Create and run the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(run_server())
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        except Exception as e:
            logger.error(f"Error in MCP server: {e}", exc_info=True)
            return 1
        finally:
            # Cleanup
            loop.close()

    except Exception as e:
        logger.error(f"Error starting Docker MCP server: {str(e)}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
