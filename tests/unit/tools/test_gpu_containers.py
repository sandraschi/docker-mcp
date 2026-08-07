"""
Test suite for GPU container tools.
"""

from unittest.mock import MagicMock, patch

import pytest

from dockermcp.tools.gpu.gpu_containers import GPUContainerManager


@pytest.fixture
def manager():
    """GPUContainerManager with a mocked docker client."""
    client = MagicMock()
    return GPUContainerManager(docker_client=client), client


def test_create_device_request_all_gpus(manager):
    """All GPUs requested -> Count -1, no DeviceIDs."""
    mgr, _client = manager

    req = mgr._create_device_request(gpu_ids=["all"])

    assert req["Count"] == -1
    assert "DeviceIDs" not in req
    assert req["Capabilities"] == [["gpu"]]


def test_create_device_request_specific_gpus(manager):
    """Specific GPUs requested -> DeviceIDs list."""
    mgr, _client = manager

    req = mgr._create_device_request(gpu_ids=[0, 1, 2])

    assert req["DeviceIDs"] == ["0", "1", "2"]


def test_create_device_request_count(manager):
    """Explicit count -> Count set, no DeviceIDs."""
    mgr, _client = manager

    req = mgr._create_device_request(count=2)

    assert req["Count"] == 2
    assert "DeviceIDs" not in req


def test_create_gpu_container_config(manager):
    """Config includes device request, runtime, and env."""
    mgr, _client = manager

    config = mgr.create_gpu_container_config(gpu_ids=[0], runtime="nvidia")

    assert config.runtime == "nvidia"
    assert config.device_requests[0]["DeviceIDs"] == ["0"]
    assert config.environment.get("NVIDIA_VISIBLE_DEVICES") == "0"


def test_get_container_gpu_info(manager):
    """GPU info reads container labels/environment."""
    mgr, client = manager
    container = MagicMock()
    container.attrs = {
        "Config": {"Env": ["NVIDIA_VISIBLE_DEVICES=0", "NVIDIA_DRIVER_CAPABILITIES=compute"]},
        "HostConfig": {"Runtime": "nvidia"},
    }
    client.containers.get.return_value = container

    info = mgr.get_container_gpu_info("gpu-container")

    assert info is not None
    assert isinstance(info, dict)
    client.containers.get.assert_called_once_with("gpu-container")
