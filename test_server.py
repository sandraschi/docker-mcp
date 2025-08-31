#!/usr/bin/env python3
"""
Test script for Docker MCP server.
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add the parent directory to the Python path
src_dir = str(Path(__file__).parent.absolute() / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

async def test_list_images():
    """Test listing Docker images."""
    from dockermcp import mcp
    
    try:
        # Call the list_images tool
        result = await mcp.tools["list_images"]()
        print("List Images Result:")
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        print(f"Total Images: {result.get('total', 0)}")
        
    except Exception as e:
        print(f"Error testing list_images: {e}")
        raise

async def main():
    """Main test function."""
    try:
        print("Testing Docker MCP server...")
        await test_list_images()
        
    except Exception as e:
        print(f"Test failed: {e}")
        return 1
    
    print("Tests completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
