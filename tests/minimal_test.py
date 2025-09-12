"""
Minimal test script to verify Docker connection handling.
This avoids FastMCP dependencies and just tests the core Docker connectivity.
"""

import docker
import sys

def test_docker_connection():
    """Test if we can connect to Docker."""
    try:
        client = docker.from_env()
        client.ping()
        print("✅ Docker is running")
        return True
    except Exception as e:
        print(f"❌ Docker is not available: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Docker connection...")
    connected = test_docker_connection()
    
    if connected:
        print("\nTo test Docker down scenarios:")
        print("1. Stop Docker Desktop")
        print("2. Run this script again")
    else:
        print("\n✅ Test successful! The script correctly detected that Docker is not running.")
