"""
Advanced Workflow Example for DockerMCP

This script demonstrates advanced workflow management with DockerMCP, including:
- Multi-service application deployment
- Service dependencies
- Health checks
- Error handling and rollback
- Parallel operations
"""
import asyncio
from typing import Any

from fastmcp import MCPClient

# Initialize the client
client = MCPClient("http://localhost:8000")
client.api_key = "your-api-key-here"

class AdvancedWorkflow:
    """Advanced workflow management with rollback support."""

    def __init__(self, client: MCPClient):
        self.client = client
        self.workflow_id: str | None = None
        self.resources: dict[str, list[dict[str, Any]]] = {
            'containers': [],
            'networks': [],
            'volumes': []
        }

    async def create_network(self, name: str, driver: str = "bridge") -> dict[str, Any]:
        """Create a Docker network and track it for cleanup."""
        print(f"Creating network '{name}'...")
        response = await self.client.create_network(name=name, driver=driver)

        if response.get("status") == "success":
            self.resources['networks'].append({
                'id': response['network_id'],
                'name': name
            })
            print(f"Network '{name}' created successfully")
        else:
            print(f"Failed to create network '{name}': {response.get('error')}")

        return response

    async def create_volume(self, name: str, driver: str = "local") -> dict[str, Any]:
        """Create a Docker volume and track it for cleanup."""
        print(f"Creating volume '{name}'...")
        response = await self.client.create_volume(name=name, driver=driver)

        if response.get("status") == "success":
            self.resources['volumes'].append({
                'name': response['name'],
                'driver': driver
            })
            print(f"Volume '{name}' created successfully")
        else:
            print(f"Failed to create volume '{name}': {response.get('error')}")

        return response

    async def create_container(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create a Docker container and track it for cleanup."""
        name = config.get('name', 'unnamed')
        print(f"Creating container '{name}'...")

        response = await self.client.create_container(**config)

        if response.get("status") == "success":
            container_id = response['container_id']
            self.resources['containers'].append({
                'id': container_id,
                'name': name
            })
            print(f"Container '{name}' created with ID: {container_id}")

            # Start the container
            start_response = await self.client.start_container(container_id)
            if start_response.get("status") == "success":
                print(f"Container '{name}' started successfully")
            else:
                print(f"Failed to start container '{name}': {start_response.get('error')}")
        else:
            print(f"Failed to create container '{name}': {response.get('error')}")

        return response

    async def wait_for_service(
        self,
        container_name: str,
        check_interval: int = 2,
        max_attempts: int = 30
    ) -> bool:
        """Wait for a service to become healthy."""
        print(f"Waiting for service '{container_name}' to become healthy...")

        for attempt in range(max_attempts):
            # Check container status
            containers = await self.client.list_containers(all=True)
            container = next(
                (c for c in containers.get('containers', [])
                 if c.get('name') == container_name),
                None
            )

            if not container:
                print(f"Container '{container_name}' not found")
                return False

            # Check health status
            health = container.get('health', {}).get('status', 'unknown').lower()

            if health == 'healthy':
                print(f"Service '{container_name}' is healthy")
                return True
            elif health == 'unhealthy':
                print(f"Service '{container_name}' is unhealthy")
                return False

            # Still starting up
            if attempt % 5 == 0:  # Print status every 5 attempts
                print(f"  {container_name} status: {health} (attempt {attempt + 1}/{max_attempts})")

            await asyncio.sleep(check_interval)

        print(f"Timeout waiting for service '{container_name}' to become healthy")
        return False

    async def deploy_application(self) -> bool:
        """Deploy a multi-service application with dependencies."""
        try:
            # 1. Create networks
            await self.create_network("app-network")

            # 2. Create volumes
            await self.create_volume("db-data")
            await self.create_volume("cache-data")

            # 3. Deploy database
            db_config = {
                "name": "app-db",
                "image": "postgres:13-alpine",
                "environment": {
                    "POSTGRES_PASSWORD": "example",
                    "POSTGRES_DB": "mydb",
                    "POSTGRES_USER": "user"
                },
                "volumes": ["db-data:/var/lib/postgresql/data"],
                "networks": ["app-network"],
                "healthcheck": {
                    "test": ["CMD-SHELL", "pg_isready -U user -d mydb"],
                    "interval": 5000000000,  # 5 seconds
                    "timeout": 500000000,     # 0.5 seconds
                    "retries": 3,
                    "start_period": 10000000000  # 10 seconds
                }
            }

            await self.create_container(db_config)

            # Wait for database to be ready
            if not await self.wait_for_service("app-db"):
                raise Exception("Database failed to start")

            # 4. Deploy cache
            cache_config = {
                "name": "app-cache",
                "image": "redis:alpine",
                "networks": ["app-network"],
                "volumes": ["cache-data:/data"],
                "healthcheck": {
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": 5000000000,  # 5 seconds
                    "timeout": 500000000,     # 0.5 seconds
                    "retries": 3,
                    "start_period": 5000000000  # 5 seconds
                }
            }

            await self.create_container(cache_config)

            # Wait for cache to be ready
            if not await self.wait_for_service("app-cache"):
                raise Exception("Cache service failed to start")

            # 5. Deploy application services in parallel
            services = [
                {
                    "name": "app-backend",
                    "image": "myapp-backend:latest",
                    "environment": {
                        "DB_HOST": "app-db",
                        "DB_NAME": "mydb",
                        "DB_USER": "user",
                        "DB_PASSWORD": "example",
                        "REDIS_HOST": "app-cache"
                    },
                    "ports": {"3000": "3000"},
                    "networks": ["app-network"],
                    "depends_on": ["app-db", "app-cache"],
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:3000/health"],
                        "interval": 10000000000,  # 10 seconds
                        "timeout": 500000000,      # 0.5 seconds
                        "retries": 3,
                        "start_period": 30000000000  # 30 seconds
                    }
                },
                {
                    "name": "app-frontend",
                    "image": "myapp-frontend:latest",
                    "ports": {"80": "8080"},
                    "networks": ["app-network"],
                    "depends_on": ["app-backend"],
                    "environment": {
                        "API_URL": "http://app-backend:3000"
                    }
                }
            ]

            # Deploy services in parallel
            tasks = [self.create_container(service) for service in services]
            await asyncio.gather(*tasks)

            # Wait for backend to be healthy
            if not await self.wait_for_service("app-backend"):
                raise Exception("Backend service failed to start")

            print("\nApplication deployed successfully!")
            print("Services:")
            print("  - Database:    http://localhost:5432")
            print("  - Backend API: http://localhost:3000")
            print("  - Frontend:    http://localhost:8080")

            return True

        except Exception as e:
            print(f"\nError during deployment: {e!s}")
            print("Initiating rollback...")
            await self.rollback()
            return False

    async def rollback(self) -> None:
        """Rollback all created resources."""
        print("\n=== Starting Rollback ===")

        # Stop and remove containers
        for container in self.resources['containers']:
            print(f"Stopping container {container['name']} ({container['id']})")
            try:
                await self.client.stop_container(container['id'])
                await self.client.remove_container(container['id'])
            except Exception as e:
                print(f"  Error removing container {container['name']}: {e!s}")

        # Remove networks
        for network in self.resources['networks']:
            print(f"Removing network {network['name']} ({network['id']})")
            try:
                await self.client.remove_network(network['id'])
            except Exception as e:
                print(f"  Error removing network {network['name']}: {e!s}")

        # Remove volumes
        for volume in self.resources['volumes']:
            print(f"Removing volume {volume['name']}")
            try:
                await self.client.remove_volume(volume['name'])
            except Exception as e:
                print(f"  Error removing volume {volume['name']}: {e!s}")

        print("\nRollback completed")

    async def cleanup(self) -> None:
        """Clean up all resources."""
        print("\n=== Cleaning Up ===")
        await self.rollback()

async def main() -> None:
    """Run the advanced workflow example."""
    workflow = AdvancedWorkflow(client)

    try:
        success = await workflow.deploy_application()

        if success:
            print("\nApplication is running. Press Ctrl+C to stop...")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")

    except Exception as e:
        print(f"Fatal error: {e!s}")

    finally:
        await workflow.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
