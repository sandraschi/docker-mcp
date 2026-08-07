"""
Test suite for container logs tools.
"""

from unittest.mock import MagicMock, patch

import docker
import pytest
from pydantic import ValidationError

from dockermcp.tools.containers.container_logs import ContainerLogsRequest, get_container_logs


@pytest.fixture
def docker_mock():
    """Mock Docker client with container.logs returning two lines."""
    client = MagicMock(spec=docker.DockerClient)
    container = MagicMock()
    client.containers.get.return_value = container
    container.logs.return_value = b"2023-01-01T00:00:00Z Log line 1\n2023-01-01T00:00:01Z Log line 2\n"
    with patch("docker.from_env", return_value=client):
        yield client, container


@pytest.mark.asyncio
async def test_get_container_logs(docker_mock):
    """Test retrieving container logs."""
    _client, container = docker_mock

    request = ContainerLogsRequest(
        container_id="test-container", tail="100", since="1h", until="now", timestamps=True, follow=False
    )

    response = await get_container_logs(request)

    assert response.status == "success"
    assert response.container_id == "test-container"
    assert len(response.logs) == 2
    assert "Log line 1" in response.logs[0]["line"]
    container.logs.assert_called_once()
    kwargs = container.logs.call_args.kwargs
    assert kwargs["tail"] == "100"
    assert kwargs["timestamps"] is True
    assert kwargs["stream"] is False


@pytest.mark.asyncio
async def test_container_not_found(docker_mock):
    """Test handling of non-existent container."""
    from docker.errors import NotFound

    client, _container = docker_mock
    client.containers.get.side_effect = NotFound("Container not found")

    response = await get_container_logs(ContainerLogsRequest(container_id="nonexistent-container"))

    assert response.status == "error"
    assert "not found" in response.error.lower()


def test_request_validation():
    """Test validation of request parameters."""
    with pytest.raises(ValidationError):
        ContainerLogsRequest(tail="100")  # missing container_id

    with pytest.raises(ValidationError):
        ContainerLogsRequest(container_id="test-container", tail=-1)  # tail must be a string

    request = ContainerLogsRequest(container_id="test-container", tail="50", since="2h", timestamps=True)
    assert request.container_id == "test-container"
    assert request.tail == "50"
    assert request.timestamps is True
