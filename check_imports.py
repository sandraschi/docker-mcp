from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

#!/usr/bin/env python3
"""Check if all required modules can be imported."""
import sys
import os
from pathlib import Path
logger.info("Python Path:")
for path in sys.path:
logger.info(f"  - {path}")
logger.info("\nChecking imports...")

try:
    import docker
logger.info("✅ docker")
except ImportError as e:
logger.info(f"❌ docker: {e}")

try:
    import fastmcp
logger.info(f"✅ fastmcp ({fastmcp.__version__ if hasattr(fastmcp, '__version__') else 'version unknown'})")
except ImportError as e:
logger.info(f"❌ fastmcp: {e}")

try:
    from dockermcp import mcp
logger.info("✅ dockermcp.mcp")
except ImportError as e:
logger.info(f"❌ dockermcp.mcp: {e}")

try:
    from dockermcp.tools.images import image_tools
logger.info("✅ dockermcp.tools.images.image_tools")
except ImportError as e:
logger.info(f"❌ dockermcp.tools.images.image_tools: {e}")
logger.info("\nCurrent working directory:", os.getcwd())
logger.info("Contents of dockermcp directory:")
    for f in (Path(__file__).parent / "src" / "dockermcp").glob("**/*.py"):
logger.info(f"  - {f.relative_to(Path(__file__).parent / 'src')}")
