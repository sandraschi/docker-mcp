#!/usr/bin/env python3
"""
Test script for Docker MCP graceful connection handling.
"""
import asyncio
import sys

# Add src to path
sys.path.insert(0, 'src')

async def test_graceful_connection():
    """Test the graceful Docker connection handling."""
    print("🔧 Testing Docker MCP graceful connection handling...")

    try:
        # Import the module - this should NOT crash even if Docker is down
        print("1. Testing module import (should not crash)...")
        from dockermcp import (
            get_docker_status,
        )
        print("   ✅ Module import successful!")

        # Test connection status
        print("2. Testing connection status...")
        status = get_docker_status()
        print(f"   Docker available: {status['available']}")
        print(f"   Connection error: {status.get('error', 'None')}")

        # Test status tool
        print("3. Testing docker_status tool...")
        from dockermcp.tools.system.status_tools import docker_status
        result = await docker_status()
        print(f"   Status tool success: {result['success']}")
        print(f"   Docker available: {result['docker_status']['available']}")

        # Test reconnection tool
        print("4. Testing docker_reconnect tool...")
        from dockermcp.tools.system.status_tools import docker_reconnect
        reconnect_result = await docker_reconnect()
        print(f"   Reconnect tool success: {reconnect_result['success']}")

        print("\n🎯 Test Results Summary:")
        print("   - Module imports without crashing: ✅")
        print(f"   - Docker connection status: {'✅' if status['available'] else '⚠️  Unavailable (gracefully handled)'}")
        print(f"   - Status tool works: {'✅' if result['success'] else '❌'}")
        print(f"   - Reconnect tool works: {'✅' if reconnect_result['success'] else '❌'}")

        if not status['available']:
            print("\n📋 Docker unavailable - this is expected if Docker isn't running.")
            print(f"   Error: {status.get('error', 'Unknown')}")
            print("   The key fix: MCP starts successfully instead of crashing!")

        return True

    except Exception as e:
        print(f"❌ Test failed with exception: {e!s}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_graceful_connection())
    sys.exit(0 if success else 1)
