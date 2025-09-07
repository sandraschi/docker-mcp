"""
Pytest configuration and fixtures for Docker MCP tests.
"""
import pytest
from unittest.mock import MagicMock, patch
import docker

@pytest.fixture(autouse=True)
def mock_docker():
    """Fixture to mock the Docker client."""
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
