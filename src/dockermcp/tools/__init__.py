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
# Try different import paths for Tool
try:
    from fastmcp.tools import Tool
except ImportError:
    try:
        from fastmcp.server.tool import Tool
    except ImportError:
        # If neither works, define a basic Tool class
        class Tool:
            pass

# Initialize FastMCP instance
mcp = FastMCP(
    name="Docker MCP Tools",
    version="2.11.3"
)

def discover_and_register_tools() -> None:
    """Automatically discover and register all tools from submodules."""
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
            
            # Find all Tool instances in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, Tool):
                    mcp.tool(attr)
                    
        except ImportError as e:
            print(f"Warning: Failed to import tools from {module_name}: {e}")

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
