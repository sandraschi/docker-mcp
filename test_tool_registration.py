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

from fastmcp import FastMCP
from dockermcp.mcp_instance import FastMCPSingleton

async def test_tool_registration():
    """Test that tools are properly registered with FastMCP."""
    print("Testing FastMCP tool registration...")
    
    # Initialize FastMCP
    mcp_singleton = FastMCPSingleton()
    mcp = mcp_singleton.mcp
    
    # Get registered tools
    tools = mcp.get_tools()
    print(f"\nFound {len(tools)} registered tools:")
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")
    
    # Test list_containers tool
    if 'list_containers' in [t['name'] for t in tools]:
        print("\nTesting list_containers tool...")
        try:
            # Find the tool
            tool = next(t for t in tools if t['name'] == 'list_containers')
            
            # Call the tool
            result = await tool['function'](all_states=False)
            
            if result.get('status') == 'success':
                print(f"✓ Successfully listed {len(result.get('containers', []))} containers")
            else:
                print(f"✗ Error: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"✗ Error testing list_containers: {str(e)}")
    else:
        print("\n✗ list_containers tool not found")

if __name__ == "__main__":
    asyncio.run(test_tool_registration())
