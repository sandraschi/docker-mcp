#!/usr/bin/env python3
"""Check if all required modules can be imported."""
import sys
import os
from pathlib import Path

print("Python Path:")
for path in sys.path:
    print(f"  - {path}")

print("\nChecking imports...")

try:
    import docker
    print("✅ docker")
except ImportError as e:
    print(f"❌ docker: {e}")

try:
    import fastmcp
    print(f"✅ fastmcp ({fastmcp.__version__ if hasattr(fastmcp, '__version__') else 'version unknown'})")
except ImportError as e:
    print(f"❌ fastmcp: {e}")

try:
    from dockermcp import mcp
    print("✅ dockermcp.mcp")
except ImportError as e:
    print(f"❌ dockermcp.mcp: {e}")

try:
    from dockermcp.tools.images import image_tools
    print("✅ dockermcp.tools.images.image_tools")
except ImportError as e:
    print(f"❌ dockermcp.tools.images.image_tools: {e}")
    print("\nCurrent working directory:", os.getcwd())
    print("Contents of dockermcp directory:")
    for f in (Path(__file__).parent / "src" / "dockermcp").glob("**/*.py"):
        print(f"  - {f.relative_to(Path(__file__).parent / 'src')}")
