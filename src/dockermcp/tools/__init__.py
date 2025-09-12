"""
Docker MCP Tools - FastMCP 2.12.0 compatible tools

Docker MCP Tools Package

This package contains all the FastMCP 2.12.0 compatible tools for Docker operations.
"""
import importlib
import logging
import pkgutil
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Type, TypeVar, Callable

# Add the src directory to the Python path
src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure logging first to ensure all modules use the same config
from dockermcp.logging_config import configure_logging, logger
configure_logging(level="WARNING")

# Silence noisy loggers
for logger_name in ['fastmcp', 'mcp', 'uvicorn', 'httpx', 'httpcore', 'h11', 'asyncio']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Import the singleton instance after logging is configured
from dockermcp.mcp_instance import get_mcp
mcp = get_mcp()

# Ensure the MCP instance has minimal logging
mcp.logger.setLevel("CRITICAL")

def discover_and_register_tools():
    """
    Automatically discover and register all tools from submodules.
    
    FastMCP 2.12+ uses decorator pattern - tools are automatically
    registered when modules are imported via the @Tool decorator.
    """
    tools_dir = Path(__file__).parent
    
    # Skip __pycache__, __init__.py, and models
    modules = [
        name for _, name, is_pkg in pkgutil.iter_modules([str(tools_dir)])
        if not name.startswith('_') and not name == 'models' and not name.startswith('test_')
    ]
    
    for name in modules:
        try:
            # Import the module to register the tools
            importlib.import_module(f'.{name}', package=__name__)
            logger.debug(f'Imported tools module: {name}')
        except ImportError as e:
            logger.warning(f'Failed to import tools module {name}: {e}')
        except Exception as e:
            logger.error(f'Error importing tools module {name}: {e}', exc_info=True)
    
    logger.info(f'Discovered {len(modules)} tools modules')

# Register all tools when this module is imported
discover_and_register_tools()

# Re-export the mcp instance for use in the application
__all__ = ['mcp']
