"""
Pytest configuration and fixtures for Docker MCP tests.
"""
import os
import pytest
from unittest.mock import MagicMock, patch
import docker
import requests

# Default MCP server URL
DEFAULT_MCP_SERVER = "http://localhost:8000"

@pytest.fixture(scope="session")
def mcp_server_url():
    """Get the MCP server URL from environment or use default."""
    return os.environ.get("MCP_SERVER_URL", DEFAULT_MCP_SERVER)

def is_server_available(url):
    """Check if MCP server is available."""
    try:
        response = requests.get(f"{url}/health")
        return response.status_code == 200
    except requests.RequestException:
        return False

# Only use mocks if MOCK_MODE is set
if os.environ.get("MOCK_MODE", "0") == "1":
    @pytest.fixture(autouse=True)
    def mock_docker():
        """Fixture to mock the Docker client when in mock mode."""
        with patch('docker.from_env') as mock_from_env:
            mock_client = MagicMock(spec=docker.DockerClient)
            mock_from_env.return_value = mock_client
            
            # Set up default mocks
            mock_container = MagicMock()
            mock_client.containers.get.return_value = mock_container
            
            # Configure container attributes
            mock_container.attrs = {
                'Id': 'test-container-id',
                'Name': 'test-container',
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
                    'WorkingDir': '/app',
                    'Labels': {}
                },
                'NetworkSettings': {
                    'IPAddress': '172.17.0.2',
                    'Ports': {'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]},
                    'Networks': {
                        'bridge': {
                            'IPAMConfig': None,
                            'Links': None,
                            'Aliases': None,
                            'NetworkID': 'test-network',
                            'EndpointID': 'test-endpoint',
                            'Gateway': '172.17.0.1',
                            'IPAddress': '172.17.0.2',
                            'IPPrefixLen': 16,
                            'IPv6Gateway': '',
                            'GlobalIPv6Address': '',
                            'GlobalIPv6PrefixLen': 0,
                            'MacAddress': '02:42:ac:11:00:02'
                        }
                    }
                }
            }
            
            # Mock container logs
            mock_container.logs.return_value = b"2023-01-01T00:00:00Z Test log line 1\n2023-01-01T00:00:01Z Test log line 2\n"
            
            # Mock exec_run
            mock_exec = MagicMock()
            mock_exec.output = [b'stdout output\n', b'stderr output\n']
            mock_container.exec_run.return_value = mock_exec
            
            yield mock_client
else:
    @pytest.fixture(scope="session")
    def docker_client():
        """Fixture to provide a real Docker client."""
        client = docker.from_env()
        try:
            # Verify Docker is running
            client.ping()
            return client
        except Exception as e:
            pytest.skip(f"Docker is not available: {e}")

    @pytest.fixture(scope="session")
    def ensure_mcp_server(mcp_server_url):
        """Ensure MCP server is available before running tests."""
        if not is_server_available(mcp_server_url):
            pytest.skip(f"MCP server not available at {mcp_server_url}")
        return mcp_server_url
