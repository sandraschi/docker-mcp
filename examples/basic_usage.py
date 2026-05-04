"""
Basic Usage Examples for DockerMCP

This script demonstrates how to use the DockerMCP API to perform common Docker operations.
"""
import asyncio

from fastmcp import MCPClient

# Initialize the client
client = MCPClient("http://localhost:8000")

# Set your API key (replace with your actual API key)
client.api_key = "your-api-key-here"

async def list_containers() -> None:
    """List all running containers."""
    print("\n=== Listing Running Containers ===")
    response = await client.list_containers()
    if response.get("status") == "success":
        for container in response.get("containers", []):
            print(f"ID: {container['id']}")
            print(f"  Name: {container['name']}")
            print(f"  Image: {container['image']}")
            print(f"  Status: {container['status']}")
            print(f"  Created: {container['created']}")
            print("-" * 50)
    else:
        print(f"Error: {response.get('error')}")

async def create_container() -> None:
    """Create a new Nginx container."""
    print("\n=== Creating Nginx Container ===")
    container_config = {
        "image": "nginx:latest",
        "name": "web-server",
        "ports": {"80/tcp": 8080},
        "environment": {"ENV": "development"},
        "labels": {"app": "demo"}
    }

    response = await client.create_container(**container_config)
    if response.get("status") == "success":
        print(f"Container created with ID: {response['container_id']}")

        # Start the container
        start_response = await client.start_container(response['container_id'])
        if start_response.get("status") == "success":
            print("Container started successfully")
        else:
            print(f"Failed to start container: {start_response.get('error')}")
    else:
        print(f"Failed to create container: {response.get('error')}")

async def manage_images() -> None:
    """Demonstrate image management operations."""
    print("\n=== Managing Images ===")

    # List all images
    print("\nListing all images:")
    response = await client.list_images(all=True)
    if response.get("status") == "success":
        for image in response.get("images", [])[:3]:  # Show first 3 images
            print(f"- {image.get('repo_tags', ['<none>'])[0]} (Size: {image.get('size', 0) / (1024*1024):.2f} MB)")
    else:
        print(f"Error: {response.get('error')}")

    # Pull a new image
    print("\nPulling Redis image:")
    pull_response = await client.pull_image("redis:alpine")
    if pull_response.get("status") == "success":
        print("Redis image pulled successfully")
    else:
        print(f"Failed to pull image: {pull_response.get('error')}")

async def network_operations() -> None:
    """Demonstrate network operations."""
    print("\n=== Network Operations ===")

    # List all networks
    print("\nListing all networks:")
    response = await client.list_networks()
    if response.get("status") == "success":
        for network in response.get("networks", []):
            print(f"- {network['name']} ({network['driver']})")
    else:
        print(f"Error: {response.get('error')}")

    # Create a new network
    print("\nCreating a new network:")
    network_config = {
        "name": "my-network",
        "driver": "bridge",
        "labels": {"purpose": "demo"}
    }
    create_response = await client.create_network(**network_config)
    if create_response.get("status") == "success":
        print(f"Network created with ID: {create_response['network_id']}")
    else:
        print(f"Failed to create network: {create_response.get('error')}")

async def volume_operations() -> None:
    """Demonstrate volume operations."""
    print("\n=== Volume Operations ===")

    # List all volumes
    print("\nListing all volumes:")
    response = await client.list_volumes()
    if response.get("status") == "success":
        for volume in response.get("volumes", [])[:3]:  # Show first 3 volumes
            print(f"- {volume['name']} ({volume['driver']})")
    else:
        print(f"Error: {response.get('error')}")

    # Create a new volume
    print("\nCreating a new volume:")
    volume_config = {
        "name": "app-data",
        "driver": "local",
        "labels": {"app": "demo"}
    }
    create_response = await client.create_volume(**volume_config)
    if create_response.get("status") == "success":
        print(f"Volume created with name: {create_response['name']}")
    else:
        print(f"Failed to create volume: {create_response.get('error')}")

async def system_info() -> None:
    """Display system information."""
    print("\n=== System Information ===")

    # Get Docker system info
    response = await client.system_info()
    if response.get("status") == "success":
        info = response["info"]
        print(f"Docker Version: {info.get('docker_version')}")
        print(f"OS/Arch: {info.get('os')}/{info.get('architecture')}")
        print(f"Containers: {info.get('containers_running', 0)} running, {info.get('containers_stopped', 0)} stopped")
        print(f"Images: {info.get('images', 0)}")
        print(f"CPUs: {info.get('n_cpu', 0)}")
        print(f"Total Memory: {info.get('mem_total', 0) / (1024*1024*1024):.2f} GB")
    else:
        print(f"Error: {response.get('error')}")

    # Get disk usage
    print("\nDisk Usage:")
    usage_response = await client.disk_usage()
    if usage_response.get("status") == "success":
        usage = usage_response["disk_usage"]
        print(f"Total Space: {usage.get('total_space', 0) / (1024*1024):.2f} MB")
        print(f"Used Space: {usage.get('used_space', 0) / (1024*1024):.2f} MB")
        print(f"Reclaimable Space: {usage.get('reclaimable_space', 0) / (1024*1024):.2f} MB")
    else:
        print(f"Error: {usage_response.get('error')}")

async def workflow_example() -> None:
    """Demonstrate workflow operations."""
    print("\n=== Workflow Example ===")

    # Define a simple workflow
    workflow_definition = {
        "name": "web-app",
        "services": {
            "web": {
                "image": "nginx:alpine",
                "ports": {"80": "8080"},
                "depends_on": ["db"]
            },
            "db": {
                "image": "postgres:13-alpine",
                "environment": {
                    "POSTGRES_PASSWORD": "example",
                    "POSTGRES_DB": "mydb"
                },
                "volumes": ["postgres_data:/var/lib/postgresql/data"]
            }
        },
        "volumes": {
            "postgres_data": {}
        }
    }

    # Create the workflow
    print("Creating workflow...")
    create_response = await client.create_workflow(workflow_definition)
    if create_response.get("status") != "success":
        print(f"Failed to create workflow: {create_response.get('error')}")
        return

    workflow_id = create_response["workflow_id"]
    print(f"Workflow created with ID: {workflow_id}")

    # Start the workflow
    print("Starting workflow...")
    start_response = await client.start_workflow(workflow_id)
    if start_response.get("status") != "success":
        print(f"Failed to start workflow: {start_response.get('error')}")
        return

    print("Workflow started successfully")

    # Monitor workflow status
    print("\nMonitoring workflow status (press Ctrl+C to stop):")
    try:
        while True:
            status_response = await client.workflow_status(workflow_id)
            if status_response.get("status") == "success":
                status = status_response["workflow"]
                print(f"\rStatus: {status['status']}", end="", flush=True)

                if status["status"] in ["completed", "failed"]:
                    print("\n")
                    break

            await asyncio.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")

    # Clean up
    print("\nCleaning up...")
    stop_response = await client.stop_workflow(workflow_id)
    if stop_response.get("status") == "success":
        print("Workflow stopped successfully")
    else:
        print(f"Failed to stop workflow: {stop_response.get('error')}")

async def main() -> None:
    """Run all examples."""
    try:
        print("=== DockerMCP Examples ===")

        # Run examples
        await list_containers()
        await create_container()
        await manage_images()
        await network_operations()
        await volume_operations()
        await system_info()
        await workflow_example()

        print("\nAll examples completed!")
    except Exception as e:
        print(f"An error occurred: {e!s}")

if __name__ == "__main__":
    asyncio.run(main())
