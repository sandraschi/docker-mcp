"""
Tool Template for FastMCP 2.12+

This file serves as a template for creating new tools following FastMCP 2.12+ standards.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Annotated
from pydantic import Field, BaseModel

# FastMCP imports
from fastmcp import FastMCP

# Initialize MCP instance
mcp = FastMCP("Docker MCP")

# Local imports
from dockermcp.logging_config import logger

class ExampleToolParams(BaseModel):
    """Parameters for the example tool."""
    param1: str = Field(
        ...,
        description="First parameter"
    )
    param2: int = Field(
        default=42,
        description="Second parameter"
    )

@mcp.tool(
    name="example_tool",
    description="Example tool following FastMCP 2.12+ standards"
)
async def example_tool(params: ExampleToolParams) -> Dict[str, Any]:
    """
    Example tool that demonstrates the FastMCP 2.12+ pattern.
    
    Args:
        params: ExampleToolParams containing:
            - param1: First parameter
            - param2: Second parameter (default: 42)
            
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
        # Your implementation here
        result = {
            'status': 'success',
            'message': 'Operation completed successfully',
            'data': {
                'param1': params.param1,
                'param2': params.param2,
                'processed': True
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
