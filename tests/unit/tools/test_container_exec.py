"""
Test suite for container execution tools.
"""

from unittest.mock import MagicMock, patch

import docker
import pytest

from dockermcp.tools.containers.container_exec import execute_in_container


@pytest.fixture
def docker_mock():
    """Mock Docker client with a low-level exec API."""
    client = MagicMock(spec=docker.DockerClient)
    container = MagicMock()
    client.containers.get.return_value = container
    api = MagicMock()
    container.client.api = api
    api.exec_create.return_value = {"Id": "exec-123"}
    api.exec_start.return_value = (b"Command output\nMultiple lines\n", b"")
    api.exec_inspect.return_value = {"ExitCode": 0}
    with patch("docker.from_env", return_value=client):
        yield client, container, api


@pytest.mark.asyncio
async def test_execute_command(docker_mock):
    """Test executing a command in a container."""
    _client, _container, api = docker_mock

    response = await execute_in_container(
        container_id="test-container",
        command="ls -la",
        workdir="/app",
        environment={"VAR1": "value1"},
        user="root",
        privileged=False,
        tty=False,
    )

    assert response.status == "success"
    assert response.exit_code == 0
    assert "Command output" in response.output or ""
    assert response.container_id == "test-container"

    api.exec_create.assert_called_once()
    _args, kwargs = api.exec_create.call_args
    assert kwargs["cmd"] == ["ls", "-la"]
    assert kwargs["workdir"] == "/app"


@pytest.mark.asyncio
async def test_execute_command_with_streaming(docker_mock):
    """Test executing a command with streaming mode."""
    _client, _container, _api = docker_mock

    response = await execute_in_container(
        container_id="test-container", command="tail -f /var/log/app.log", stream=True
    )

    assert response.status == "success"
    assert response.exec_id == "exec-123"
    assert "streaming" in response.message.lower()


@pytest.mark.asyncio
async def test_execute_command_with_error_exit_code(docker_mock):
    """Test handling of non-zero exit codes."""
    _client, _container, api = docker_mock
    api.exec_inspect.return_value = {"ExitCode": 1}
    api.exec_start.return_value = (b"", b"command not found")

    response = await execute_in_container(container_id="test-container", command="invalid-command")

    assert response.status == "error"
    assert "exit code 1" in response.error.lower()


@pytest.mark.asyncio
async def test_container_not_found(docker_mock):
    """Test handling of non-existent container."""
    from docker.errors import NotFound

    client, _container, _api = docker_mock
    client.containers.get.side_effect = NotFound("Container not found")

    response = await execute_in_container(container_id="nonexistent-container", command="echo test")

    assert response.status == "error"
    assert "not found" in response.error.lower()
