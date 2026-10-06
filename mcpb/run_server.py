"""MCPB entry point: runs the docker-mcp FastMCP server over stdio for Claude Desktop.

The Tauri/NSIS sidecar uses the repo-root run_server.py (HTTP). This bundle script is the
stdio launcher; it only puts the staged mcpb/src on sys.path and calls dockermcp.server.main.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from dockermcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
