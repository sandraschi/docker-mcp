"""
Test suite for Docker network tools (prune, list, create).
"""

from unittest.mock import MagicMock, patch

import pytest

from dockermcp.tools.networks.network_tools import create_network, list_networks, prune_networks


@pytest.fixture
def mcp_docker_stub():
    """Stub dockermcp.mcp_instance.mcp with a docker_client mock."""
    from dockermcp.mcp_instance import mcp

    client = MagicMock()
    old = mcp.docker_client
    mcp.docker_client = client
    try:
        yield client
    finally:
        mcp.docker_client = old


def test_prune_networks_success(mcp_docker_stub):
    """Prune returns deleted networks + reclaimed space."""
    client = mcp_docker_stub
    client.networks.prune.return_value = {"NetworksDeleted": ["net1", "net2"], "SpaceReclaimed": 1024}

    response = prune_networks()

    assert response.status == "success"
    assert response.data["networks_deleted"] == ["net1", "net2"]
    assert response.data["space_reclaimed"] == 1024
    assert "2" in response.message


def test_prune_networks_no_networks(mcp_docker_stub):
    """Prune with nothing to delete."""
    client = mcp_docker_stub
    client.networks.prune.return_value = {"NetworksDeleted": [], "SpaceReclaimed": 0}

    response = prune_networks()

    assert response.status == "success"
    assert response.data["networks_deleted"] == []


def test_list_networks(mcp_docker_stub):
    """List returns network summaries."""
    client = mcp_docker_stub
    net = MagicMock()
    net.name = "bridge"
    net.id = "net-1"
    net.attrs = {"Name": "bridge", "Id": "net-1"}
    client.networks.list.return_value = [net]

    response = list_networks()

    assert response.status == "success"
    assert len(response.data) == 1


