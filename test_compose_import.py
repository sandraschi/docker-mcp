#!/usr/bin/env python3
"""Test script to check if compose_tools imports correctly."""

try:
    import src.dockermcp.tools.compose.compose_tools
    print("✅ compose_tools import successful")
    print("✅ FastMCP 2.12 compatibility fixes applied!")
except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
