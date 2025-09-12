# FastMCP 2.11 to 2.12 Migration Guide

This document outlines the key differences between FastMCP 2.11 and 2.12, focusing on tool development patterns and requirements.

## Table of Contents
- [Import Patterns](#import-patterns)
- [Tool Definition](#tool-definition)
- [Tool Registration](#tool-registration)
- [Error Handling](#error-handling)
- [Response Formats](#response-formats)
- [Best Practices](#best-practices)
- [Common Pitfalls](#common-pitfalls)

## Import Patterns

### FastMCP 2.11 (Old)
```python
# Direct imports from fastmcp
from fastmcp import Tool, get_tools_metadata
from fastmcp.exceptions import ToolError
```

### FastMCP 2.12 (New)
```python
# Preferred: Import from fastmcp.tools
try:
    from fastmcp.tools import Tool, get_tools_metadata
    from fastmcp.exceptions import ToolError
except ImportError:
    # Fallback for backward compatibility
    from fastmcp import Tool, get_tools_metadata
    from fastmcp.exceptions import ToolError
```

## Tool Definition

### FastMCP 2.11 (Old)
```python
@Tool(
    name="tool_name",
    description="Tool description",
    parameters={
        'type': 'object',
        'properties': {
            'param1': {'type': 'string'}
        }
    }
)
def my_tool(param1: str) -> dict:
    return {"result": param1}
```

### FastMCP 2.12 (New)
```python
@Tool(
    name="tool_name",
    description="Tool description",
    parameters={
        'type': 'object',
        'properties': {
            'param1': {
                'type': 'string',
                'description': 'Parameter description',
                'default': 'default_value'  # Optional
            }
        },
        'required': ['param1']  # Explicit required parameters
    }
)
async def my_tool(param1: str) -> dict:
    """
    Detailed docstring with parameter and return type documentation.
    
    Args:
        param1: Description of parameter
        
    Returns:
        dict: Result with status and data
    """
    try:
        return {
            "status": "success",
            "data": param1,
            "message": "Operation completed successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to process: {str(e)}"
        }
```

## Tool Registration

### FastMCP 2.11 (Old)
```python
# In __init__.py
def get_tools():
    from . import my_tool_module
    return [my_tool_module.my_tool]
```

### FastMCP 2.12 (New)
```python
# In __init__.py
def get_tools() -> List[Tool]:
    """
    Get all tools for registration with FastMCP.
    
    Returns:
        List[Tool]: List of Tool instances to be registered
    """
    try:
        from . import my_tool_module
        
        tools = my_tool_module.get_tools()
        
        # Verify all items are Tool instances
        for tool in tools:
            if not isinstance(tool, Tool):
                raise TypeError(f"Expected Tool instance, got {type(tool).__name__}")
        
        logger.info(f"Loaded {len(tools)} tools")
        return tools
        
    except Exception as e:
        logger.error(f"Failed to load tools: {str(e)}", exc_info=True)
        raise
```

## Error Handling

### FastMCP 2.11 (Old)
```python
try:
    # Operation
    return {"result": "success"}
except Exception as e:
    return {"error": str(e)}
```

### FastMCP 2.12 (New)
```python
try:
    # Operation
    return {
        "status": "success",
        "data": result_data,
        "message": "Operation completed"
    }
except Exception as e:
    logger.error(f"Error in my_tool: {str(e)}", exc_info=True)
    return {
        "status": "error",
        "error": str(e),
        "message": f"Failed to complete operation: {str(e)}"
    }
```

## Response Formats

### FastMCP 2.11 (Old)
```json
{
    "result": "some data"
}
```

### FastMCP 2.12 (New)
```json
{
    "status": "success",
    "data": {
        "key": "value"
    },
    "message": "Operation completed successfully"
}
```

## Best Practices

1. **Always use type hints** for function parameters and return values
2. **Document all tools** with detailed docstrings
3. **Use async/await** for I/O bound operations
4. **Log errors** with context
5. **Validate inputs** using Pydantic models when possible
6. **Follow consistent** response formats
7. **Test tools** thoroughly

## Common Pitfalls

1. **Missing type hints** - Can cause issues with FastMCP's type system
2. **Blocking I/O** in async functions - Use `asyncio.to_thread` for CPU-bound operations
3. **Incomplete error handling** - Always catch and log exceptions
4. **Circular imports** - Be careful with imports between tool modules
5. **Resource leaks** - Ensure resources are properly closed
6. **Inconsistent response formats** - Follow the standard response format
7. **Missing documentation** - Document all tools, parameters, and return values
