"""
Tool Template for FastMCP 2.12+

This file serves as a template for creating new tools following FastMCP 2.12+ standards.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# FastMCP imports
from fastmcp.tools.tool import Tool

# Local imports
from dockermcp.logging_config import logger

@Tool(
    name="example_tool",
    description="Example tool following FastMCP 2.12+ standards",
    parameters={
        'type': 'object',
        'properties': {
            'param1': {
                'type': 'string',
                'description': 'First parameter',
                'default': 'default_value'
            },
            'param2': {
                'type': 'integer',
                'description': 'Second parameter',
                'default': 42
            }
        },
        'required': ['param1']
    }
)
async def example_tool(
    param1: str = 'default_value',
    param2: int = 42
) -> Dict[str, Any]:
    """
    Example tool that demonstrates the FastMCP 2.12+ pattern.
    
    Args:
        param1: First parameter description
        param2: Second parameter description (default: 42)
        
    Returns:
        Dictionary containing the result of the operation
        
    Example:
        >>> example_tool(param1="test", param2=123)
        {
            "status": "success",
            "result": {
                "processed_param1": "test_processed",
                "processed_param2": 246
            }
        }
        
        >>> # Error case
        {
            "status": "error",
            "message": "Detailed error message"
        }
    """
    try:
        # Implementation goes here
        result = {
            "status": "success",
            "result": {
                "processed_param1": f"{param1}_processed",
                "processed_param2": param2 * 2
            }
        }
        
        return result
        
    except Exception as e:
        error_msg = f"Error in example_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "message": error_msg
        }
