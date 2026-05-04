"""
Test script to verify Docker connection handling.
"""

import asyncio
import logging
import sys
from pathlib import Path

import docker

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_docker_connection():
    """Test the Docker connection handling."""
    try:
        # Try to connect to Docker
        client = docker.from_env()
        client.ping()
        print("✅ Docker is running")
        return True
    except Exception as e:
        print(f"❌ Docker is not available: {e!s}")
        return False

if __name__ == "__main__":
    # Run the test
    print("Testing Docker connection...")
    connected = asyncio.run(test_docker_connection())

    if connected:
        print("\nTo test Docker down scenarios:")
        print("1. Stop Docker Desktop")
        print("2. Run this script again")
    else:
        print("\n✅ Test successful! The script correctly detected that Docker is not running.")
        print("\nTo complete testing:")
        print("1. Start Docker Desktop")
        print("2. Run this script again to verify it detects when Docker is running")
