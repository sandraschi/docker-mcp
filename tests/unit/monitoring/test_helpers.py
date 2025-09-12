"""Test helpers for monitoring stack tests."""
import pytest
from typing import Dict, Any
from unittest.mock import patch, MagicMock


def mock_docker_client():
    """Create a mock Docker client for testing."""
    mock_client = MagicMock()
    
    # Mock containers
    mock_container = MagicMock()
    mock_container.status = 'running'
    mock_container.labels = {'com.docker.compose.service': 'prometheus'}
    mock_container.ports = {'9090/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '9091'}]}
    
    mock_client.containers.list.return_value = [mock_container]
    return mock_client


@pytest.fixture
def monitoring_config() -> Dict[str, Any]:
    """Return a sample monitoring configuration."""
    return {
        'services': {
            'prometheus': {'ports': ['9091:9090']},
            'grafana': {'ports': ['3001:3000']},
            'loki': {'ports': ['3101:3100']},
            'cadvisor': {'ports': ['8082:8080']},
            'node-exporter': {'ports': ['9100:9100']},
            'promtail': {},
            'redis': {'ports': ['6379:6379']}
        }
    }
