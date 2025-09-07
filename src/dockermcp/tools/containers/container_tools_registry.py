"""
Container tools registry for Docker MCP.

This module registers all container management tools with the FastMCP 2.12+ server.
It provides a centralized way to register all container-related tools and their schemas.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Type, Callable, Union, TypeVar

# FastMCP imports
from fastmcp import FastMCP
from fastmcp.tools import Tool, get_tools_metadata
from fastmcp.exceptions import ToolError
from pydantic import BaseModel

# Configure logging
from dockermcp.logging_config import logger, configure_logging
configure_logging()

# Type aliases
T = TypeVar('T', bound=BaseModel)
ToolRegistration = Union[Tool, Callable, Type[BaseModel]]

def get_all_tools() -> List[ToolRegistration]:
    """
    Get all container tools and models that should be registered.
    
    This function imports all tool modules and collects their exported tools.
    It ensures all container-related functionality is properly registered with FastMCP.
    
    Returns:
        List of tools, functions, and models to register with FastMCP
        
    Example:
        >>> tools = get_all_tools()
        >>> assert any(t.name == 'list_containers' for t in tools if hasattr(t, 'name'))
    """
    tools: List[ToolRegistration] = []
    
    # Import all tool modules
    from . import (
        container_lifecycle,
        container_logs,
        container_exec,
        container_inspect,
        container_models,
        container_operations,
        container_utils,
        container_tools
    )
    
    # Core modules that contain tools to register
    modules = [
        container_lifecycle,  # Container lifecycle operations
        container_logs,      # Log management
        container_exec,      # Command execution
        container_inspect,   # Inspection and monitoring
        container_tools      # Main facade with all tools re-exported
    ]
    
    # Get all models from container_models
    if hasattr(container_models, 'get_tools'):
        tools.extend(container_models.get_tools())
    
    # Get tools from each module
    for module in modules:
        try:
            if hasattr(module, 'get_tools'):
                module_tools = module.get_tools()
                if not isinstance(module_tools, list):
                    logger.warning(f"Expected {module.__name__}.get_tools() to return a list, got {type(module_tools)}")
                    continue
                tools.extend(module_tools)
                logger.debug(f"Added {len(module_tools)} tools from {module.__name__}")
        except Exception as e:
            logger.error(f"Error getting tools from {module.__name__}: {str(e)}", exc_info=True)
    
    # Log the total number of tools found
    logger.info(f"Registered {len(tools)} container tools with FastMCP")
    
    return tools

def register_container_tools(mcp: FastMCP) -> None:
    """
    Register all container tools with the FastMCP server.
    
    This function registers all container-related tools including:
    - Container lifecycle management (create, start, stop, restart, remove, prune)
    - Container inspection and monitoring
    - Container logs streaming and retrieval
    - Command execution in containers
    - Container statistics and process information
    - All container-related Pydantic models
    
    Args:
        mcp: FastMCP server instance to register tools with
        
    Raises:
        ToolError: If there's an error registering any tool
        
    Example:
        ```python
        from fastmcp import FastMCP
        from dockermcp.tools.containers import register_container_tools
        
        # Create FastMCP instance
        mcp = FastMCP()
        
        # Register all container tools
        register_container_tools(mcp)
        
        # Start the server
        mcp.run()
        ```
    """
    try:
        # Get all tools and models
        tools = get_all_tools()
        registered_count = 0
        
        # Register each tool
        for tool in tools:
            try:
                # Skip None values that might be returned by get_tools()
                if tool is None:
                    continue
                    
                # Log detailed information about the tool being registered
                tool_name = (
                    getattr(tool, 'name', None) or 
                    getattr(tool, '__name__', str(tool))
                )
                logger.debug(f"Registering tool: {tool_name}")
                
                # Register the tool with FastMCP
                mcp.register_tool(tool)
                registered_count += 1
                
                # Log successful registration
                logger.debug(f"Successfully registered tool: {tool_name}")
                
            except Exception as e:
                error_msg = f"Failed to register tool {tool_name if 'tool_name' in locals() else 'unknown'}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise ToolError(error_msg) from e
        
        # Log summary of registration
        logger.info(f"Successfully registered {registered_count} container tools with FastMCP")
        
    except Exception as e:
        logger.error(f"Failed to register container tools: {e}", exc_info=True)
        raise ToolError(f"Failed to register container tools: {e}") from e

def get_tools() -> List[Tool]:
    """
    Get all container tools as Tool instances for registration with FastMCP.
    
    This function collects all container-related tools from various modules and
    returns them in a format suitable for registration with the FastMCP server.
    
    Returns:
        List of Tool instances to register with FastMCP
        
    Example:
        >>> from fastmcp.tools import get_tools_metadata
        >>> tools = get_tools()
        >>> assert any(t.name == 'list_containers' for t in tools)
    """
    try:
        from fastmcp.tools import get_tools_metadata, Tool
        
        # Get all tools and models
        all_items = get_all_tools()
        
        # Filter to only include Tool instances
        tool_instances = [
            item for item in all_items 
            if isinstance(item, Tool) or hasattr(item, '_is_tool')
        ]
        
        # Log the number of tools found
        logger.info(f"Found {len(tool_instances)} container tools for registration")
        
        # Log the names of the tools for debugging
        if logger.isEnabledFor(logging.DEBUG):
            tool_names = [
                getattr(t, 'name', getattr(t, '__name__', str(t)))
                for t in tool_instances
            ]
            logger.debug(f"Container tools to register: {', '.join(tool_names)}")
        
        return tool_instances
        
    except Exception as e:
        error_msg = f"Error getting container tools: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
