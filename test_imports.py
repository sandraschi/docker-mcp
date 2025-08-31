#!/usr/bin/env python3
"""Test script to verify all dockermcp imports work after pydantic v2 fixes."""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

def test_import(module_name, description):
    try:
        __import__(module_name)
        print(f"✅ {description}")
        return True
    except Exception as e:
        print(f"❌ {description}: {str(e)}")
        return False

def main():
    print("Testing dockermcp imports after pydantic v2 fixes...\n")
    
    tests = [
        ("dockermcp.tools.containers.container_models", "Container models"),
        ("dockermcp.tools.images.image_models", "Image models"),
        ("dockermcp.tools.networks.network_models", "Network models"),
        ("dockermcp.tools.volumes.volume_models", "Volume models"),
        ("dockermcp.tools.system.system_models", "System models"),
        ("dockermcp.tools.compose.compose_models", "Compose models"),
        ("dockermcp", "Main dockermcp module"),
    ]
    
    passed = 0
    total = len(tests)
    
    for module, desc in tests:
        if test_import(module, desc):
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} imports successful")
    
    if passed == total:
        print("🎉 All imports working! Pydantic v2 fix successful.")
        return 0
    else:
        print(f"💥 {total - passed} imports still failing.")
        return 1

if __name__ == "__main__":
    exit(main())
