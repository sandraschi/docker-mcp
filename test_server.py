#!/usr/bin/env python3
"""
Test script for Docker MCP server.
"""
import sys
import asyncio
from dockermcp.logging_config import logger, configure_logging

# Configure logging
configure_logging()

from pathlib import Path

# Add the parent directory to the Python path
src_dir = str(Path(__file__).parent.absolute() / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure logging
s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

async def test_list_images():
    """Test listing Docker images."""
    from dockermcp import mcp
    
    try:
        # Call the list_images tool
        result = await mcp.tools["list_images"]()
logger.info("List Images Result:")
logger.info(f"Success: {result.get('success')}")
logger.info(f"Message: {result.get('message')}")
logger.info(f"Total Images: {result.get('total', 0)}")
        
    except Exception as e:
logger.info(f"Error testing list_images: {e}")
        raise

async def main():
    """Main test function."""
    try:
logger.info("Testing Docker MCP server...")
        await test_list_images()
        
    except Exception as e:
logger.info(f"Test failed: {e}")
        return 1
logger.info("Tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
