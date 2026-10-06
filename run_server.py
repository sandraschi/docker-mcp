"""PyInstaller sidecar entry - dual transport, same contract as arxiv-mcp.

* default (no flags): HTTP web bridge + REST + /mcp. This is how the Tauri operator spawns it.
* ``--stdio`` or ``MCP_TRANSPORT=stdio``: MCP over stdio, without the web bridge. This is what an
  IDE / Claude Desktop MCP registration of the installed sidecar passes explicitly, so it never
  contends for port 10807 with a dev stack. Logs go to stderr; stdout carries JSON-RPC only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


# PyInstaller lazy-import traps (fleet Tauri protocol)
import _datetime  # noqa: F401
import _strptime  # noqa: F401

import mcp.types  # noqa: F401  (freeze the mcp bootstrap before fastmcp touches it)


def _stdio_requested() -> bool:
    return "--stdio" in sys.argv[1:] or os.environ.get("MCP_TRANSPORT", "").lower() == "stdio"


def _run_http() -> None:
    port = int(os.environ.get("MCP_PORT", os.environ.get("PORT", "10807")))
    host = os.environ.get("MCP_HOST", "127.0.0.1")

    import uvicorn

    from customization.server import app

    uvicorn.run(app, host=host, port=port, log_level="info")


def _run_stdio() -> None:
    # Probe first, before any Docker/tool init: if the desktop app / dev stack backend is up and
    # healthy, proxy to it instead of running a second instance (SOTA_REQUIREMENTS 2.3).
    from docker_mcp.daemon_probe import proxy_if_daemon

    if proxy_if_daemon():
        return

    from dockermcp.server import main as stdio_main

    stdio_main(web_bridge=False)


def main() -> None:
    if _stdio_requested():
        _run_stdio()
    else:
        _run_http()


if __name__ == "__main__":
    main()
