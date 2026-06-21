"""
Miscellaneous utilities and helper classes for Docker MCP.

This module contains various utility functions and classes that don't fit neatly
into other modules.
"""

import json
import logging
from typing import Any, TextIO

from fastmcp import FastMCP

# Define a type alias for JSON-RPC response
JSONRPCResponse = dict[str, Any]

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
        self, method: str, params: dict | list | None = None, request_id: int | str | None = None
    ) -> JSONRPCResponse:
        """Handle JSON-RPC requests with enhanced error handling."""
        try:
            return await super()._handle_request(method, params, request_id)
        except Exception as e:
            logger.error(f"Error handling request {method}: {e!s}", exc_info=True)
            return self._create_error_response(
                code=-32603,  # Internal error
                message=f"Internal error: {e!s}",
                request_id=request_id,
            )


def warn_with_log(
    message: str | Warning,
    category: type[Warning] = UserWarning,
    filename: str = "",
    lineno: int = 0,
    file: TextIO | None = None,
    line: str | None = None,
) -> None:
    """
    Log a warning message and emit a warning.

    This function is compatible with warnings.showwarning signature and can be used
    as a replacement for the built-in showwarning function.

    Args:
        message: The warning message (str or Warning object)
        category: The warning category (default: UserWarning)
        filename: The filename where the warning occurred (default: "")
        lineno: The line number where the warning occurred (default: 0)
        file: The file to write the warning to (default: None)
        line: The source code line (default: None)
    """
    # Convert message to string if it's a Warning object
    if isinstance(message, Warning):
        msg_str = str(message)
    else:
        msg_str = str(message)

    # Log the warning with location info if available
    if filename and lineno:
        logger.warning(f"{category.__name__}: {msg_str} (at {filename}:{lineno})")
    else:
        logger.warning(f"{category.__name__}: {msg_str}")
