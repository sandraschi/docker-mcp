"""
Test suite for container lifecycle tools.
"""

from unittest.mock import MagicMock, patch

import docker
import pytest

from dockermcp.tools.containers.container_lifecycle import (
    ContainerLifecycleParams,
    manage_container_lifecycle,
)
from dockermcp.tools.containers.container_management import ContainerAction, ContainerRequest, manage_container


@pytest.fixture
def docker_mock():
    """Mock Docker client with a container."""
    client = MagicMock(spec=docker.DockerClient)
    container = MagicMock()
    container.name = "test-container"
    container.id = "abc123"
    client.containers.get.return_value = container
    with patch("docker.from_env", return_value=client):
        yield client, container


@pytest.mark.asyncio
async def test_start_container(docker_mock):
    """Test starting a container via the lifecycle module."""
    _client, container = docker_mock

    response = await manage_container_lifecycle(
        ContainerLifecycleParams(container_id="test-container", action="start")
    )

    assert response["success"] is True
    assert response["container_id"] == "test-container"
    container.start.assert_called_once()


@pytest.mark.asyncio
async def test_remove_container_force(docker_mock):
    """Test force-removing a container."""
    _client, container = docker_mock

    response = await manage_container_lifecycle(
        ContainerLifecycleParams(container_id="test-container", action="remove", force=True)
    )

    assert response["success"] is True
    container.remove.assert_called_once()
    args, kwargs = container.remove.call_args
    assert kwargs.get("force") is True


@pytest.mark.asyncio
async def test_dispatcher_routes_lifecycle(docker_mock):
    """The manage_container portmanteau routes lifecycle actions correctly."""
    _client, container = docker_mock

    response = await manage_container(
        ContainerRequest(action=ContainerAction.START, container_id="test-container", params={"wait": False})
    )

    assert response["success"] is True
    container.start.assert_called_once()


@pytest.mark.asyncio
async def test_container_not_found(docker_mock):
    """Test handling of a non-existent container."""
    from docker.errors import NotFound

    client, _container = docker_mock
    client.containers.get.side_effect = NotFound("Container not found")

    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError) as exc_info:
        await manage_container_lifecycle(
            ContainerLifecycleParams(container_id="nonexistent", action="start")
        )

    assert "not found" in str(exc_info.value).lower()
