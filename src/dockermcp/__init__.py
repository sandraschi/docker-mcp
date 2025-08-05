"""
DockerMCP - FastMCP 2.10 server for Docker operations with Austrian efficiency.

This module provides a comprehensive interface for managing Docker containers,
images, networks, and volumes through the Model Control Protocol (MCP).
"""

__version__ = "0.1.0"

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import server components
from .server import main  # noqa: F401

__all__ = ["__version__", "main"]
