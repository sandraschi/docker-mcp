"""
FastMCP Singleton Instance

This module provides a single, shared FastMCP instance for the entire application.
This is the ONLY place where FastMCP should be initialized.
"""
import logging
import threading
from fastmcp import FastMCP
from . import __version__

# Thread-safe singleton pattern
class FastMCPSingleton:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(FastMCPSingleton, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        if not self._initialized:
            self._initialized = True
            
            # Initialize FastMCP with minimal settings
            self.mcp = FastMCP(
                name="docker-mcp",
                version=__version__,
                include_fastmcp_meta=False
            )

# Create the singleton instance
_singleton = FastMCPSingleton()

# Get the FastMCP instance from the singleton
def get_mcp():
    """
    Get the shared FastMCP instance.
    This is the ONLY way to access the FastMCP instance in the application.
    """
    return _singleton.mcp

# For backward compatibility
mcp = get_mcp()
