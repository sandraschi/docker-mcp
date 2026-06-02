"""
Docker MCP Tools - FastMCP 3.3+ compatible tools.

Tool modules register via @mcp.tool in dockermcp.tool_registration.register_all_tools().
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from dockermcp.logging_config import configure_logging, logger

configure_logging(level="INFO")

for logger_name in ("fastmcp", "mcp", "uvicorn", "httpx", "httpcore", "h11", "asyncio"):
    logging.getLogger(logger_name).setLevel(logging.WARNING)

T = TypeVar("T")


class ToolResponse[T](BaseModel):
    """Standard response model for all tools."""

    success: bool
    message: str
    data: T | None = None
    error: str | None = None

    @classmethod
    def from_success(cls, message: str, data: T | None = None) -> ToolResponse[T]:
        return cls(success=True, message=message, data=data)

    @classmethod
    def from_error(cls, message: str, error: Exception | None = None) -> ToolResponse[Any]:
        error_msg = str(error) if error else message
        return cls(success=False, message=message, error=error_msg)


def discover_tools() -> set[str]:
    """Discover tool modules (optional; registration uses tool_registration)."""
    tools_dir = Path(__file__).parent
    discovered: set[str] = set()
    modules = [
        name
        for _, name, _ in pkgutil.iter_modules([str(tools_dir)])
        if not name.startswith("_") and name != "models" and not name.startswith("test_")
    ]
    for name in modules:
        try:
            importlib.import_module(f".{name}", package=__name__)
            discovered.add(name)
        except ImportError as e:
            logger.warning(f"Failed to import module {name}: {e!s}")
    return discovered


discovered_tools: set[str] = set()

__all__ = ["ToolResponse", "discover_tools", "discovered_tools"]
