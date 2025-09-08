from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

"""
Docker MCP Tools - FastMCP 2.11.3 compatible tools

Docker MCP Tools Package

This package contains all the FastMCP 2.11.3 compatible tools for Docker operations.
"""
import importlib
import pkgutil
from pathlib import Path
from typing import List, Type

from fastmcp import FastMCP

# Try to import the tool decorator
try:
    from fastmcp.tools import tool as Tool
    TOOL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FastMCP tool decorator not available: {e}")
    TOOL_AVAILABLE = False

# Initialize FastMCP instance
mcp = FastMCP(
    name="Docker MCP Tools",
    version="2.11.3"
)

def discover_and_register_tools() -> None:
    """
    Automatically discover and register all tools from submodules.
    
    This function:
    1. Discovers all Python package submodules in the tools directory
    2. Imports each submodule
    3. Registers tools either directly as Tool instances or via get_tools() functions
    """
    # Get the directory containing this file
    tools_dir = Path(__file__).parent
    
    # Find all subdirectories that are Python packages
    submodules = [
        name for _, name, is_pkg in pkgutil.iter_modules([str(tools_dir)])
        if is_pkg and name != 'examples'  # Skip examples by default
    ]
    
    # Import each submodule and register its tools
    for module_name in submodules:
        try:
            module = importlib.import_module(f".{module_name}", package=__name__)
            logger.info(f"Discovered module: {module_name}")
            
            # Check if the module has a get_tools() function
            if hasattr(module, 'get_tools') and callable(module.get_tools):
                try:
                    tools = module.get_tools()
                    if not TOOL_AVAILABLE:
                        logger.debug(f"Skipping tool registration - FastMCP tool decorator not available")
                        continue
                        
                    if isinstance(tools, list):
                        for tool in tools:
                            try:
                                if hasattr(tool, '__wrapped__'):  # Check if it's a @tool decorated function
                                    mcp.tool(tool)
                                    logger.debug(f"Registered @tool from {module_name}.get_tools(): {tool.__name__}")
                            except Exception as e:
                                logger.error(f"Error registering tool {getattr(tool, '__name__', str(tool))} from {module_name}: {str(e)}")
                    elif hasattr(tools, '__wrapped__'):  # Single @tool decorated function
                        try:
                            mcp.tool(tools)
                            logger.debug(f"Registered @tool from {module_name}.get_tools(): {tools.__name__}")
                        except Exception as e:
                            logger.error(f"Error registering tool {getattr(tools, '__name__', str(tools))} from {module_name}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error getting tools from {module_name}.get_tools(): {str(e)}", exc_info=True)
            
            # Also look for @tool decorated functions in the module if tool decorator is available
            if TOOL_AVAILABLE:
                for attr_name in dir(module):
                    try:
                        if not attr_name.startswith('_'):  # Skip private attributes
                            attr = getattr(module, attr_name)
                            if hasattr(attr, '__wrapped__'):  # Check if it's a @tool decorated function
                                try:
                                    mcp.tool(attr)
                                    logger.debug(f"Registered @tool from {module_name}: {attr_name}")
                                except Exception as e:
                                    logger.error(f"Error registering tool {attr_name} from {module_name}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing attribute {attr_name} in {module_name}: {str(e)}", exc_info=True)
                    
        except ImportError as e:
            logger.info(f"Warning: Failed to import tools from {module_name}: {e}")

# Import the mcp instance from the main package
from dockermcp import mcp

# Register all tools when this module is imported
discover_and_register_tools()

# Import all tool modules to register them
try:
    from dockermcp.tools import containers, images, networks, volumes, system, workflow
except ImportError:
    # Fallback for direct script execution
    from . import containers, images, networks, volumes, system, workflow

# Re-export the mcp instance for use in the application
__all__ = ['mcp']
