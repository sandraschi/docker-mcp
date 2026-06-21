"""
Test script to verify Docker MCP behavior when Docker is not running.

This script tests the error handling and graceful degradation features
when the Docker daemon is not available.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from dockermcp.tools.containers.container_tools import list_containers

from dockermcp import get_docker_status
from dockermcp.tools.docker_reconnect import docker_reconnect
from dockermcp.tools.docker_status import docker_status

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_docker_status():
    """Test the docker_status tool when Docker is down."""
    logger.info("Testing docker_status tool...")
    status = await docker_status()
    print("\n=== docker_status output ===")
    print(json.dumps(status, indent=2))
    print("=" * 30 + "\n")

    # Verify the status shows Docker as not available
    assert isinstance(status, dict), "docker_status should return a dictionary"
    assert "docker_available" in status, "Status should include docker_available flag"
    assert not status["docker_available"], "docker_available should be False when Docker is down"
    assert "error" in status, "Status should include error information"

    logger.info("✅ docker_status test passed")


async def test_list_containers():
    """Test list_containers when Docker is down."""
    logger.info("Testing list_containers tool...")
    from dockermcp.tools.containers.container_models import ListContainersRequest

    # Create a simple request
    request = ListContainersRequest(all=True)
    result = await list_containers(request)

    print("\n=== list_containers output ===")
    print(json.dumps(result, indent=2))
    print("=" * 30 + "\n")

    # Should return empty list when Docker is down
    assert isinstance(result, list), "list_containers should return a list"
    assert len(result) == 0, "Should return empty list when Docker is down"

    logger.info("✅ list_containers test passed")


async def test_docker_reconnect():
    """Test the docker_reconnect tool when Docker is down."""
    logger.info("Testing docker_reconnect tool...")

    # First verify Docker is not available
    initial_status = get_docker_status()
    assert not initial_status["docker_available"], "Docker should not be available initially"

    # Try to reconnect
    result = await docker_reconnect()

    print("\n=== docker_reconnect output ===")
    print(json.dumps(result, indent=2))
    print("=" * 30 + "\n")

    # Should indicate reconnection failed
    assert isinstance(result, dict), "docker_reconnect should return a dictionary"
    assert "success" in result, "Result should include success flag"

    # Reconnection should fail since we haven't started Docker
    assert not result.get("success"), "Reconnection should fail when Docker is not running"

    logger.info("✅ docker_reconnect test passed")


async def run_tests():
    """Run all Docker down tests."""
    logger.info("Starting Docker down tests...")

    try:
        await test_docker_status()
        await test_list_containers()
        await test_docker_reconnect()

        logger.info("\n✅ All Docker down tests passed!")
        return True
    except AssertionError as e:
        logger.error(f"❌ Test failed: {e!s}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e!s}", exc_info=True)
        return False


if __name__ == "__main__":
    # Print initial Docker status
    status = get_docker_status()
    print("\n=== Initial Docker Status ===")
    print(f"Docker Available: {status.get('docker_available', False)}")
    print(f"Error: {status.get('error', 'None')}")

    # Ensure Docker is not running before tests
    if status.get("docker_available", False):
        print("\n❌ ERROR: Docker is running. Please stop Docker Desktop before running these tests.")
        sys.exit(1)

    # Run tests
    success = asyncio.run(run_tests())

    # Exit with appropriate status code
    sys.exit(0 if success else 1)
