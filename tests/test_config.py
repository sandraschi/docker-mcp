"""Test configuration and fixtures for consistent test environments."""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables from .env if it exists
load_dotenv()


# Test configuration
class TestConfig:
    """Test configuration settings."""

    # Docker test settings
    TEST_CONTAINER_PREFIX = "test_dockermcp_"
    TEST_NETWORK_NAME = "test_dockermcp_network"
    TEST_IMAGE = "alpine:latest"  # Lightweight image for testing

    # Test timeouts (in seconds)
    CONTAINER_START_TIMEOUT = 30
    TEST_TIMEOUT = 60


# Environment variable helpers
def get_test_config() -> TestConfig:
    """Get test configuration with environment overrides."""
    config = TestConfig()

    # Allow environment overrides
    if "DOCKER_TEST_IMAGE" in os.environ:
        config.TEST_IMAGE = os.environ["DOCKER_TEST_IMAGE"]
    if "TEST_TIMEOUT" in os.environ:
        config.TEST_TIMEOUT = int(os.environ["TEST_TIMEOUT"])

    return config


# Common fixtures
@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Provide test configuration to tests."""
    return get_test_config()


# Skip tests that require Docker if not available
skip_if_no_docker = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS", "false").lower() == "true",
    reason="Docker tests are disabled by SKIP_DOCKER_TESTS environment variable",
)
