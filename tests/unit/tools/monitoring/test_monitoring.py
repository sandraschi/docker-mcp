"""Unit tests for monitoring tools."""

import sys
from unittest.mock import MagicMock, patch

import pytest


# Mock the FastMCP Tool decorator
class MockTool:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, func):
        func._is_tool = True
        return func


# Mock the FastMCP package so tool modules can import it without a real instance.
# sys.modules mocks must be real module objects (with __path__) so submodule
# imports like `from fastmcp.server import create_proxy` resolve.
import types

_orig_modules = {k: sys.modules.get(k) for k in (
    "docker",
    "fastmcp",
    "fastmcp.server",
    "fastmcp.server.context",
    "fastmcp.exceptions",
    "fastmcp.tools",
    "fastmcp.tools.tool",
    "dockermcp.mcp_instance",
)}

_fastmcp = types.ModuleType("fastmcp")
_fastmcp.__path__ = []
_fastmcp.FastMCP = MagicMock()


def _tool_decorator(func=None, **kwargs):
    """Stand-in for @mcp.tool - returns the original callable (awaitable)."""

    def wrap(f):
        f._is_tool = True
        return f

    if func is not None:
        return wrap(func)
    return wrap


_fastmcp.tool = _tool_decorator
_fastmcp.Context = MagicMock()
sys.modules["fastmcp"] = _fastmcp

_fastmcp_server = types.ModuleType("fastmcp.server")
_fastmcp_server.__path__ = []
_fastmcp_server.create_proxy = MagicMock()

_fastmcp_server_context = types.ModuleType("fastmcp.server.context")
_fastmcp_server_context.Context = MagicMock()
sys.modules["fastmcp.server.context"] = _fastmcp_server_context
sys.modules["fastmcp.server"] = _fastmcp_server


class MockToolError(Exception):
    """Mock of fastmcp.exceptions.ToolError."""


_fastmcp_exceptions = types.ModuleType("fastmcp.exceptions")
_fastmcp_exceptions.ToolError = MockToolError
sys.modules["fastmcp.exceptions"] = _fastmcp_exceptions

_fastmcp_tools = types.ModuleType("fastmcp.tools")
_fastmcp_tool = types.ModuleType("fastmcp.tools.tool")
_fastmcp_tool.Tool = MockTool
sys.modules["fastmcp.tools"] = _fastmcp_tools
sys.modules["fastmcp.tools.tool"] = _fastmcp_tool

# Stub dockermcp.mcp_instance so @mcp.tool decorators return the original
# callable (awaitable) instead of MagicMock.
_mcp_instance_stub = types.ModuleType("dockermcp.mcp_instance")
_mcp_instance_stub.mcp = MagicMock()
_mcp_instance_stub.mcp.tool = _tool_decorator
_mcp_instance_stub.mcp.resource = _tool_decorator
_mcp_instance_stub.mcp.prompt = _tool_decorator
_mcp_instance_stub.get_mcp = lambda: _mcp_instance_stub.mcp
sys.modules["dockermcp.mcp_instance"] = _mcp_instance_stub

# Mock the docker module
sys.modules["docker"] = MagicMock()

# Now import the modules we want to test
from dockermcp.tools.monitoring import CommandResult, MonitoringManager, MonitoringStatusParams, start_monitoring
from dockermcp.tools.monitoring import monitoring_status as get_monitoring_status

# Restore the original modules for the rest of the test session
for _mod, _orig in _orig_modules.items():
    if _orig is not None:
        sys.modules[_mod] = _orig
    else:
        sys.modules.pop(_mod, None)

# Test data
TEST_ALERT_RULE = {"name": "HighCPUUsage", "condition": "avg(cpu_usage) > 80", "duration": "5m", "severity": "critical"}


@pytest.fixture
def mock_docker():
    """Fixture to mock docker client."""
    with patch("docker.from_env") as mock_docker:
        yield mock_docker


@pytest.fixture
def mock_subprocess():
    """Fixture to mock subprocess.run."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run


@pytest.fixture
def mock_path():
    """Fixture to mock path operations."""
    with patch("pathlib.Path") as mock_path:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.is_file.return_value = True
        yield mock_path


@pytest.mark.asyncio
async def test_start_monitoring():
    """Test starting the monitoring stack."""
    from dockermcp.tools.monitoring import CommandResult, MonitoringManager, StartMonitoringParams

    fake = CommandResult(status="success", returncode=0, stdout="Started", stderr="", command="docker compose up -d")

    with patch.object(MonitoringManager, "start_services", return_value=fake):
        result = await start_monitoring(StartMonitoringParams())

    assert result["status"] == "success"
    assert "started" in result["message"].lower()


@pytest.mark.asyncio
async def test_get_monitoring_status():
    """Test getting monitoring stack status."""
    # Mock the MonitoringManager.get_status method
    with patch.object(MonitoringManager, "run_command") as mock_run_cmd:
        # Setup the mock to return a successful response
        mock_run_cmd.return_value = CommandResult(
            status="success",
            returncode=0,
            stdout="monitoring_prometheus_1 Up 5 minutes 0.0.0.0:9090->9090/tcp\n"
            "monitoring_grafana_1 Up 5 minutes 0.0.0.0:3000->3000/tcp",
            stderr="",
            command="docker ps",
        )

        # Test the function
        result = await get_monitoring_status(MonitoringStatusParams())

        # Assertions
        assert result["status"] == "success"
        services = result.get("details", {}).get("services", [])
        assert len(services) > 0

        # Check if the services are parsed correctly
        service_names = [s["name"] for s in services if isinstance(s, dict)]
        assert "monitoring_prometheus_1" in service_names
        assert "monitoring_grafana_1" in service_names

        # Check the status of one of the services
        prometheus = next(
            (s for s in services if isinstance(s, dict) and s.get("name") == "monitoring_prometheus_1"), None
        )
        assert prometheus is not None
        assert "status" in prometheus


@pytest.mark.asyncio
async def test_monitoring_status_detailed():
    """Test getting detailed monitoring status."""
    # Mock the MonitoringManager.get_status to return detailed container info
    with patch.object(MonitoringManager, "run_command") as mock_run_cmd:
        mock_run_cmd.return_value = CommandResult(
            status="success",
            returncode=0,
            stdout="monitoring_prometheus_1|Up 5 minutes|0.0.0.0:9090->9090/tcp\n"
            "monitoring_grafana_1|Up 5 minutes (healthy)|0.0.0.0:3000->3000/tcp",
            stderr="",
            command="docker ps",
        )

        # Test the function with detailed=True
        result = await get_monitoring_status(MonitoringStatusParams(detailed=True))

        # Assertions
        assert result["status"] == "success"
        services = result.get("details", {}).get("services", [])
        assert len(services) > 0

        # Check if the service info is in the result
        service_found = any(
            isinstance(s, dict) and "monitoring_grafana_1" in s.get("name", "") for s in services
        )
        assert service_found, "Grafana service not found in results"

        # Check if raw output is included
        assert "raw_output" in result["details"]
        assert result["details"]["raw_output"] is not None


# Add more test cases for error scenarios and edge cases

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

