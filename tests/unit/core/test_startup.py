#!/usr/bin/env python3
"""
Test script to verify dockermcp server starts properly after FastMCP 2.12 fixes.
"""
import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all imports work correctly."""
    print("🔧 Testing imports...")
    
    try:
        # Test main module import
        print("  ✓ Importing dockermcp...")
        import dockermcp
        
        # Test tools import
        print("  ✓ Importing dockermcp.tools...")
        import dockermcp.tools
        
        # Test individual tool modules
        print("  ✓ Testing individual tool modules...")
        from dockermcp.tools import containers
        print("    ✓ containers module")
        
        from dockermcp.tools import images
        print("    ✓ images module")
        
        from dockermcp.tools import networks
        print("    ✓ networks module")
        
        from dockermcp.tools import volumes
        print("    ✓ volumes module")
        
        from dockermcp.tools import system
        print("    ✓ system module")
        
        from dockermcp.tools import workflow
        print("    ✓ workflow module")
        
        from dockermcp.tools import compose
        print("    ✓ compose module")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

def test_tool_discovery():
    """Test that tool discovery works."""
    print("\n🔧 Testing tool discovery...")
    
    try:
        from dockermcp.tools import get_tools
        tools = get_tools()
        print(f"  ✓ Found {len(tools)} tools")
        
        # Check if we have some basic tools
        tool_names = [getattr(tool, 'name', str(tool)) for tool in tools]
        print(f"  ✓ Tool names: {tool_names[:5]}{'...' if len(tool_names) > 5 else ''}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool discovery failed: {str(e)}")
        traceback.print_exc()
        return False

def test_server_creation():
    """Test that we can create the MCP server."""
    print("\n🔧 Testing server creation...")
    
    try:
        from dockermcp.server import create_server
        server = create_server()
        print("  ✓ Server created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Server creation failed: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Docker MCP FastMCP 2.12 Compatibility Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_tool_discovery,
        test_server_creation
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    if all(results):
        print("🎉 ALL TESTS PASSED! Docker MCP is compatible with FastMCP 2.12")
        return 0
    else:
        print("💥 SOME TESTS FAILED! Check the output above for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())
