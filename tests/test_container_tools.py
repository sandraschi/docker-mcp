"""
Test suite for Docker MCP container tools.

This module contains tests for the container management tools in the Docker MCP server.
"""
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastmcp import FastMCP
from pydantic import ValidationError
import docker

# Import the tools we want to test
from dockermcp.tools.containers import (
    manage_container_lifecycle,
    stream_container_logs,
    execute_in_container,
    ContainerLifecycleRequest,
    ContainerLogsRequest,
    ContainerExecRequest,
    ContainerLifecycleResponse,
    ContainerLogsResponse,
    ContainerExecResponse
)

class TestContainerTools(unittest.TestCase):
    """Test cases for container management tools."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mcp = FastMCP(
            name="Test MCP",
            version="1.0.0",
            description="Test MCP Server"
        )
        
        # Mock Docker client
        self.docker_client = MagicMock(spec=docker.DockerClient)
        self.docker_client.containers.get.return_value = MagicMock()
        
        # Patch the Docker client in the container tools
        self.docker_patcher = patch('docker.from_env', return_value=self.docker_client)
        self.docker_patcher.start()
    
    def tearDown(self):
        """Clean up after each test."""
        self.docker_patcher.stop()
    
    async def test_manage_container_lifecycle_start(self):
        """Test starting a container."""
        # Setup
        request = ContainerLifecycleRequest(
            container_id="test-container",
            action="start"
        )
        
        # Execute
        response = await manage_container_lifecycle(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertEqual(response["action"], "start")
        self.assertEqual(response["container_id"], "test-container")
        self.docker_client.containers.get.return_value.start.assert_called_once()
    
    async def test_manage_container_lifecycle_stop(self):
        """Test stopping a container."""
        # Setup
        request = ContainerLifecycleRequest(
            container_id="test-container",
            action="stop",
            timeout=10
        )
        
        # Execute
        response = await manage_container_lifecycle(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertEqual(response["action"], "stop")
        self.docker_client.containers.get.return_value.stop.assert_called_once_with(timeout=10)
    
    async def test_stream_container_logs(self):
        """Test streaming container logs."""
        # Setup
        mock_container = MagicMock()
        mock_container.logs.return_value = [b"log line 1\n", b"log line 2\n"]
        self.docker_client.containers.get.return_value = mock_container
        
        request = ContainerLogsRequest(
            container_id="test-container",
            follow=False,
            tail=10,
            timestamps=True
        )
        
        # Execute
        response = await stream_container_logs(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertTrue(response["success"])
        self.assertEqual(len(response["logs"]), 2)
        mock_container.logs.assert_called_once()
    
    async def test_execute_in_container(self):
        """Test executing a command in a container."""
        # Setup
        mock_exec = MagicMock()
        mock_exec_output = MagicMock()
        mock_exec_output.output = b"command output\n"
        mock_exec.start.return_value = (mock_exec_output, )
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = (0, b"command output\n", b"")
        
        self.docker_client.containers.get.return_value = mock_container
        
        request = ContainerExecRequest(
            container_id="test-container",
            command=["ls", "-la"],
            user="root",
            workdir="/app"
        )
        
        # Execute
        response = await execute_in_container(request)
        
        # Assert
        self.assertIsInstance(response, dict)
        self.assertTrue(response["success"])
        self.assertEqual(response["result"]["exit_code"], 0)
        self.assertEqual(response["result"]["stdout"], "command output\n")
        mock_container.exec_run.assert_called_once()
    
    def test_container_lifecycle_request_validation(self):
        """Test validation of container lifecycle requests."""
        # Valid request
        valid_request = ContainerLifecycleRequest(
            container_id="test-container",
            action="start"
        )
        self.assertEqual(valid_request.container_id, "test-container")
        
        # Invalid action
        with self.assertRaises(ValidationError):
            ContainerLifecycleRequest(
                container_id="test-container",
                action="invalid-action"
            )
    
    def test_container_logs_request_validation(self):
        """Test validation of container logs requests."""
        # Valid request
        valid_request = ContainerLogsRequest(
            container_id="test-container",
            follow=False,
            tail=100
        )
        self.assertEqual(valid_request.container_id, "test-container")
        
        # Invalid tail value
        with self.assertRaises(ValidationError):
            ContainerLogsRequest(
                container_id="test-container",
                tail=-1
            )
    
    def test_container_exec_request_validation(self):
        """Test validation of container exec requests."""
        # Valid request with string command
        valid_request_str = ContainerExecRequest(
            container_id="test-container",
            command="ls -la"
        )
        self.assertIsInstance(valid_request_str.command, list)
        
        # Valid request with list command
        valid_request_list = ContainerExecRequest(
            container_id="test-container",
            command=["ls", "-la"]
        )
        self.assertEqual(valid_request_list.command, ["ls", "-la"])
        
        # Missing command
        with self.assertRaises(ValidationError):
            ContainerExecRequest(
                container_id="test-container",
                command=""
            )

# Run the tests
if __name__ == "__main__":
    unittest.main()
