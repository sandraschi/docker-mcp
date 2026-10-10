"""
Test script to verify FastMCP tool registration.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dockermcp.mcp_instance import FastMCPSingleton


async def test_tool_registration():
    """Test that tools are properly registered with FastMCP."""
    print("Testing FastMCP tool registration...")

    # Initialize FastMCP
    mcp_singleton = FastMCPSingleton()
    mcp = mcp_singleton.mcp

    # Get registered tools (FastMCP 3.x API, async)
    tools = await mcp.list_tools()
    print(f"\nFound {len(tools)} registered tools:")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")

    # Test list_containers tool
    if "list_containers" in [t.name for t in tools]:
        print("\nTesting list_containers tool...")
        try:
            # Find the tool
            tool = next(t for t in tools if t.name == "list_containers")

            # Call the tool (3.x Tool.run takes an arguments dict)
            result = await tool.run({"all_states": False})
            print(f"V list_containers call ok: {str(result.content)[:120]}")

        except Exception as e:
            print(f"✗ Error testing list_containers: {e!s}")
    else:
        print("\n✗ list_containers tool not found")


if __name__ == "__main__":
    asyncio.run(test_tool_registration())
