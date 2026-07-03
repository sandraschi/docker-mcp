"""PyInstaller + Tauri sidecar entry — HTTP web bridge on port 10807."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


# PyInstaller lazy-import traps (fleet Tauri protocol)
import _strptime  # noqa: F401


def main() -> None:
    port = int(os.environ.get("MCP_PORT", os.environ.get("PORT", "10807")))
    host = os.environ.get("MCP_HOST", "127.0.0.1")

    import uvicorn
    from customization.server import app

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
