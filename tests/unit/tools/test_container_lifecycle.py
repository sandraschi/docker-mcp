"""
Test suite for container lifecycle management tools.

This module contains tests for container lifecycle operations like create, start, stop, etc.
"""
import os
import sys
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
import aiodocker
from aiodocker.exceptions import DockerError

# Import the tools we want to test
try:
    from dockermcp.tools.containers.container_lifecycle import (
        manage_container_lifecycle,
        ContainerLifecycleRequest,
        ContainerLifecycleResponse,
        ContainerAction
    )
except ImportError as e:
    print(f"Error importing modules: {e}")
    raise

# Test constants
TEST_CONTAINER_ID = "test-container-id"
TEST_CONTAINER_NAME = "test-container"
TEST_IMAGE = "test-image:latest"

class TestContainerLifecycle(unittest.IsolatedAsyncioTestCase):
    """Test cases for container lifecycle management tools."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create a mock Docker client
        self.docker_client = MagicMock()
        self.mock_container = MagicMock()
        self.mock_container.id = TEST_CONTAINER_ID
        self.mock_container.name = TEST_CONTAINER_NAME
        self.mock_container.status = 'running'
        
        # Configure the container mock
        self.mock_container.attrs = {
            'Id': TEST_CONTAINER_ID,
            'Name': TEST_CONTAINER_NAME,
            'State': {
                'Status': 'running',
                'Running': True,
                'Paused': False,
                'Restarting': False,
                'OOMKilled': False,
                'Dead': False,
                'Pid': 1234,
                'ExitCode': 0,
                'Error': '',
                'StartedAt': '2023-01-01T00:00:00Z',
                'FinishedAt': '0001-01-01T00:00:00Z'
            },
            'Config': {
                'Image': 'test-image:latest',
                'Cmd': ['/bin/sh'],
                'Env': ['PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'],
                'WorkingDir': '/',
                'Labels': {}
            },
            'HostConfig': {
                'NetworkMode': 'default',
                'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0},
                'AutoRemove': False
            },
            'NetworkSettings': {
                'Networks': {
                    'bridge': {
                        'IPAddress': '172.17.0.2',
                        'Gateway': '172.17.0.1',
                        'NetworkID': 'bridge',
                        'EndpointID': 'test-endpoint-id',
                        'MacAddress': '02:42:ac:11:00:02'
                    }
                }
            },
            'Mounts': []
        }
        
        # Set up the Docker client mock
        self.docker_client.containers.get.return_value = self.mock_container
        
        # Patch the Docker client
        self.docker_patcher = patch('docker.from_env', return_value=self.docker_client)
        self.mock_docker = self.docker_patcher.start()
        
        # Import the module after patching
        global manage_container_lifecycle, ContainerLifecycleRequest, ContainerAction
        from dockermcp.tools.containers.container_lifecycle import (
            manage_container_lifecycle,
            ContainerLifecycleRequest,
            ContainerAction
        )
    
    def tearDown(self):
        """Clean up after each test."""
        self.docker_patcher.stop()
    
    async def test_start_container(self):
        """Test starting a container."""
        # Test 1: Basic start container
        request = ContainerLifecycleRequest(
            container_id=TEST_CONTAINER_ID,
            action=ContainerAction.START
        )
        
        response = await manage_container_lifecycle(request)
        
        self.assertIsInstance(response, dict)
        self.assertEqual(response["action"], "start")
        self.assertEqual(response["container_id"], TEST_CONTAINER_ID)
        self.assertTrue(response["success"])
        self.mock_container.start.assert_called_once()
        self.docker_client.containers.get.assert_called_once_with(TEST_CONTAINER_ID)
        
        # Test 2: Start already running container
        self.mock_container.start.reset_mock()
        self.mock_container.attrs['State']['Running'] = True
        
        response = await manage_container_lifecycle(request)
        self.assertTrue(response["success"])
        self.mock_container.start.assert_not_called()
        
        # Test 3: Start with custom timeout
        self.mock_container.start.reset_mock()
        self.mock_container.attrs['State']['Running'] = False
        
        request = ContainerLifecycleRequest(
            container_id=TEST_CONTAINER_ID,
            action=ContainerAction.START,
            timeout=30
        )
        
        await manage_container_lifecycle(request)
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
        # Test with container not found
        self.docker_client.containers.get.side_effect = docker.errors.NotFound("No such container")
        request = ContainerLifecycleRequest(
            container_id="nonexistent-container",
            action=ContainerAction.START
        )
        
        with self.assertRaises(ToolError) as context:
            await manage_container_lifecycle(request)
        self.assertIn("not found", str(context.exception).lower())
        
        # Test with API error
        self.docker_client.containers.get.side_effect = docker.errors.APIError("API error")
        with self.assertRaises(ToolError) as context:
            await manage_container_lifecycle(request)
        self.assertIn("API error", str(context.exception))
    
    async def test_container_in_abnormal_state(self):
        """Test handling of containers in various abnormal states."""
        # Test with paused container
        self.mock_container.attrs['State']['Paused'] = True
        request = ContainerLifecycleRequest(
            container_id=TEST_CONTAINER_ID,
            action=ContainerAction.START
        )
        
        response = await manage_container_lifecycle(request)
        self.assertTrue(response["success"])
        self.mock_container.unpause.assert_called_once()
        
        # Test with dead container
        self.mock_container.unpause.reset_mock()
        self.mock_container.attrs['State']['Dead'] = True
        
        with self.assertRaises(ToolError) as context:
            await manage_container_lifecycle(request)
        self.assertIn("dead", str(context.exception).lower())
    
    async def test_force_remove_container(self):
        """Test force removal of a running container."""
        # Test force remove on running container
        self.mock_container.attrs['State']['Running'] = True
        
        request = ContainerLifecycleRequest(
            container_id=TEST_CONTAINER_ID,
            action=ContainerAction.REMOVE,
            force=True
        )
        
        response = await manage_container_lifecycle(request)
        self.assertTrue(response["success"])
        self.mock_container.remove.assert_called_once_with(force=True)
    
    async def test_restart_policies(self):
        """Test container restart with different policies."""
        # Test with default policy (no restart)
        request = ContainerLifecycleRequest(
            container_id=TEST_CONTAINER_ID,
            action=ContainerAction.RESTART
        )
        
        response = await manage_container_lifecycle(request)
        self.assertTrue(response["success"])
        self.mock_container.restart.assert_called_once_with(timeout=10)  # Default timeout
        
        # Test with custom timeout
        self.mock_container.restart.reset_mock()
        request = ContainerLifecycleRequest(
            container_id=TEST_CONTAINER_ID,
            action=ContainerAction.RESTART,
            timeout=5
        )
        
        await manage_container_lifecycle(request)
        self.mock_container.restart.assert_called_once_with(timeout=5)
    
    async def test_invalid_parameters(self):
        """Test validation of request parameters."""
        # Test missing required field
        with self.assertRaises(ValidationError):
            ContainerLifecycleRequest(container_id="test")  # Missing action
            
        # Test invalid action
        with self.assertRaises(ValidationError):
            ContainerLifecycleRequest(
                container_id="test",
                action="invalid-action"
            )
            
        # Test invalid timeout
        with self.assertRaises(ValidationError):
            ContainerLifecycleRequest(
                container_id="test",
                action=ContainerAction.START,
                timeout=-1  # Invalid timeout
            )
    
    async def test_concurrent_operations(self):
        """Test handling of concurrent operations on the same container."""
        # Simulate a slow operation
        async def slow_start():
            await asyncio.sleep(0.1)
            return {"status": "started"}
            
        self.mock_container.start = AsyncMock(side_effect=slow_start)
        
        # Start multiple operations concurrently
        tasks = []
        for _ in range(3):
            request = ContainerLifecycleRequest(
                container_id=TEST_CONTAINER_ID,
                action=ContainerAction.START
            )
            tasks.append(manage_container_lifecycle(request))
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        self.assertEqual(len(responses), 3)
        for response in responses:
            self.assertTrue(response["success"])
        
        # Container start should only be called once due to operation deduplication
        self.mock_container.start.assert_called_once()

# Helper function to run async tests
if __name__ == "__main__":
    unittest.main()
