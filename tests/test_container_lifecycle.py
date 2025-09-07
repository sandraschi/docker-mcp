"""
Test suite for container lifecycle management tools.

This module contains tests for container lifecycle operations like create, start, stop, etc.
"""
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
import aiodocker
from aiodocker.exceptions import DockerError

# Import the tools we want to test
from dockermcp.tools.containers.container_lifecycle import (
    manage_container_lifecycle,
    ContainerLifecycleRequest,
    ContainerLifecycleResponse,
    ContainerAction
)

# Test constants
TEST_CONTAINER_ID = "test-container-id"
TEST_CONTAINER_NAME = "test-container"
TEST_IMAGE = "test-image:latest"

class TestContainerLifecycle(unittest.IsolatedAsyncioTestCase):
    """Test cases for container lifecycle management tools."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create a mock aiodocker client
        self.docker = AsyncMock(spec=aiodocker.Docker)
        self.docker.close = AsyncMock()
        
        # Create a mock container
        self.mock_container = AsyncMock()
        self.mock_container.id = TEST_CONTAINER_ID
        self.mock_container.name = TEST_CONTAINER_NAME
        
        # Mock container attributes
        self.mock_container._container = {
            'Id': TEST_CONTAINER_ID,
            'Name': TEST_CONTAINER_NAME,
            'State': {
                'Status': 'running',
                'Running': True,
                'Paused': False,
                'Restarting': False,
                'StartedAt': '2023-01-01T00:00:00Z'
            },
            'Config': {
                'Image': 'test-image:latest',
                'Cmd': ['/bin/sh']
            },
            'Name': 'test-container',
            'Id': 'a1b2c3d4e5f6'
        }
        
        # Patch the Docker client
        self.docker_patcher = patch('docker.from_env', return_value=self.docker_client)
        self.mock_docker = self.docker_patcher.start()
    
    def tearDown(self):
        """Clean up after each test."""
        self.docker_patcher.stop()
    
    async def test_start_container(self):
        """Test starting a container."""
        # Setup
        request = ContainerLifecycleRequest(
            container_id="test-container",
            action=ContainerAction.START
        )
        
        # Execute
        response = await manage_container_lifecycle(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertEqual(response["action"], "start")
        self.assertEqual(response["container_id"], "test-container")
        self.assertTrue(response["success"])
        self.mock_container.start.assert_called_once()
    
    async def test_stop_container(self):
        """Test stopping a container."""
        # Setup
        request = ContainerLifecycleRequest(
            container_id="test-container",
            action=ContainerAction.STOP,
            timeout=10
        )
        
        # Execute
        response = await manage_container_lifecycle(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertEqual(response["action"], "stop")
        self.assertTrue(response["success"])
        self.mock_container.stop.assert_called_once_with(timeout=10)
    
    async def test_restart_container(self):
        """Test restarting a container."""
        # Setup
        request = ContainerLifecycleRequest(
            container_id="test-container",
            action=ContainerAction.RESTART,
            timeout=5
        )
        
        # Execute
        response = await manage_container_lifecycle(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertEqual(response["action"], "restart")
        self.assertTrue(response["success"])
        self.mock_container.restart.assert_called_once_with(timeout=5)
    
    async def test_remove_container(self):
        """Test removing a container."""
        # Setup
        request = ContainerLifecycleRequest(
            container_id="test-container",
            action=ContainerAction.REMOVE,
            force=True
        )
        
        # Execute
        response = await manage_container_lifecycle(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertEqual(response["action"], "remove")
        self.assertTrue(response["success"])
        self.mock_container.remove.assert_called_once_with(force=True)
    
    async def test_container_not_found(self):
        """Test handling of non-existent container."""
        # Setup
        self.docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
        request = ContainerLifecycleRequest(
            container_id="nonexistent-container",
            action=ContainerAction.START
        )
        
        # Execute and assert
        with self.assertRaises(ToolError) as context:
            await manage_container_lifecycle(request)
        
        self.assertIn("not found", str(context.exception).lower())
    
    async def test_invalid_action(self):
        """Test handling of invalid action."""
        # Setup
        request = {
            "container_id": "test-container",
            "action": "invalid-action"  # This should be caught by Pydantic
        }
        
        # Execute and assert
        with self.assertRaises(ValidationError):
            ContainerLifecycleRequest(**request)

# Helper function to run async tests
if __name__ == "__main__":
    unittest.main()
