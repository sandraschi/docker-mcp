#!/usr/bin/env python3
"""MCPJam launcher script for Docker MCP."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and run the server
from dockermcp.server import main

if __name__ == "__main__":
    main()
