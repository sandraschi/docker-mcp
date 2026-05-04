"""
Test core Docker functionality without FastMCP dependencies.
"""

import asyncio
import sys

import docker


async def test_docker_operations():
    """Test basic Docker operations."""
    try:
        # Initialize Docker client
        client = docker.from_env()

        # Test connection
        print("\n=== Testing Docker Connection ===")
        client.ping()
        print("✅ Successfully connected to Docker daemon")

        # Get Docker version
        version = client.version()
        print(f"Docker Version: {version.get('Version', 'Unknown')}")
        print(f"API Version: {version.get('ApiVersion', 'Unknown')}")

        # List containers
        print("\n=== Listing Containers ===")
        containers = client.containers.list(all=True, limit=5)
        print(f"Found {len(containers)} containers")
        for i, container in enumerate(containers, 1):
            print(f"{i}. {container.name} ({container.status})")

        # List images (first 3)
        print("\n=== Listing Images (first 3) ===")
        images = client.images.list()
        print(f"Found {len(images)} total images")
        for i, image in enumerate(images[:3], 1):  # Show first 3 images
            print(f"{i}. {image.tags[0] if image.tags else 'untagged'}")

        return True, "✅ All Docker operations completed successfully"

    except docker.errors.DockerException as e:
        return False, f"❌ Docker error: {e!s}"
    except Exception as e:
        return False, f"❌ Unexpected error: {e!s}"

if __name__ == "__main__":
    print("Testing core Docker functionality...")

    try:
        success, message = asyncio.run(test_docker_operations())
        print(f"\n{message}")

        if success:
            print("\n✅ Test successful! Core Docker functionality is working correctly.")
            print("This confirms that the Docker daemon is operational.")
        else:
            print("\n❌ Test failed. There was an issue with Docker functionality.")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e!s}")
        sys.exit(1)
