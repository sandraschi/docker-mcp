"""
Test suite for container inspection tools.
"""

from unittest.mock import MagicMock, patch

import docker
import pytest

from dockermcp.tools.containers.container_inspect import ContainerInspectRequest, inspect_container


@pytest.fixture
def docker_mock():
    """Mock Docker client with a container exposing rich attrs."""
    client = MagicMock(spec=docker.DockerClient)
    container = MagicMock()
    container.attrs = {
        "Id": "abc123",
        "Name": "/test-container",
        "Created": "2026-01-01T00:00:00Z",
        "State": {"Status": "running", "Running": True, "Restarting": False, "ExitCode": 0},
        "Config": {"Image": "nginx:latest", "Labels": {}},
        "Image": "sha256:def456",
        "HostConfig": {},
        "NetworkSettings": {"Networks": {}},
    }
    container.logs.return_value = b"line1\nline2\n"
    container.id = "abc123"
    container.name = "/test-container"
    container.status = "running"
    container.image = MagicMock()
    container.image.tags = ["nginx:latest"]
    client.containers.get.return_value = container
    with patch("docker.from_env", return_value=client):
        yield client, container


@pytest.mark.asyncio
async def test_inspect_container_basic(docker_mock):
    """Test basic container inspection."""
    _client, container = docker_mock

    response = await inspect_container(ContainerInspectRequest(container_id="test-container"))

    assert response.status == "success"
    assert response.data.id == "abc123"
    assert response.data.name
    container.logs.assert_not_called()


@pytest.mark.asyncio
async def test_inspect_container_with_logs(docker_mock):
    """Test inspection including container logs."""
    _client, _container = docker_mock

    response = await inspect_container(
        ContainerInspectRequest(container_id="test-container", show_logs=True, log_tail=10)
    )

    assert response.status == "success"
    assert response.data.id == "abc123"


@pytest.mark.asyncio
async def test_inspect_container_not_found(docker_mock):
    """Test handling of a non-existent container."""
    from docker.errors import NotFound

    client, _container = docker_mock
    client.containers.get.side_effect = NotFound("Container not found")

    response = await inspect_container(ContainerInspectRequest(container_id="nonexistent"))

    assert response.status == "error"
    assert response.error == "container_not_found"
    assert "not found" in response.message.lower()
