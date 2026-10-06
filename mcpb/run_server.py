"""MCPB entry point: runs the docker-mcp FastMCP server over stdio for Claude Desktop.

The Tauri/NSIS sidecar uses the repo-root run_server.py (HTTP by default, ``--stdio`` for IDEs).
This bundle script is the stdio launcher: it puts the staged mcpb/src on sys.path, becomes a thin
proxy to an already-running healthy docker-mcp daemon if there is one (fleet SOTA_REQUIREMENTS 2.3,
probe BEFORE any Docker/tool init), and otherwise starts the standalone stdio server.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from docker_mcp.daemon_probe import proxy_if_daemon  # noqa: E402

if __name__ == "__main__" and proxy_if_daemon():
    sys.exit(0)

from dockermcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
