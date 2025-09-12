"""
Miscellaneous utilities and helper classes for Docker MCP.

This module contains various utility functions and classes that don't fit neatly
into other modules.
"""
import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar, Union, List, Tuple

from fastmcp import FastMCP

# Define a type alias for JSON-RPC response
JSONRPCResponse = Dict[str, Any]

# Configure logger
logger = logging.getLogger(__name__)

class SafeJSONEncoder(json.JSONEncoder):
    """A JSON encoder that safely handles non-serializable types."""
    
    def default(self, obj: Any) -> Any:
        """Convert non-serializable objects to a serializable format."""
        try:
            return super().default(obj)
        except (TypeError, OverflowError):
            # Convert non-serializable objects to string representation
            return str(obj)

class SafeFastMCP(FastMCP):
    """A safer version of FastMCP with enhanced error handling."""
    
    async def _handle_request(
        self, 
        method: str, 
        params: Optional[Union[Dict, list]] = None, 
        request_id: Optional[Union[int, str]] = None
    ) -> JSONRPCResponse:
        """Handle JSON-RPC requests with enhanced error handling."""
        try:
            return await super()._handle_request(method, params, request_id)
        except Exception as e:
            logger.error(f"Error handling request {method}: {str(e)}", exc_info=True)
            return self._create_error_response(
                code=-32603,  # Internal error
                message=f"Internal error: {str(e)}",
                request_id=request_id
            )

def warn_with_log(message: str, category: Type[Warning] = UserWarning, stacklevel: int = 1) -> None:
    """
    Log a warning message and emit a warning.
    
    Args:
        message: The warning message
        category: The warning category (default: UserWarning)
        stacklevel: The stack level for the warning (default: 1)
    """
    import warnings
    logger.warning(f"{category.__name__}: {message}")
    warnings.warn(message, category=category, stacklevel=stacklevel + 1)
