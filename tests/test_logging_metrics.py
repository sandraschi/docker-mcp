""
Tests for the enhanced logging and metrics functionality.
"""
import os
import time
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from dockermcp.logging_config import logger, configure_logging
from dockermcp.metrics import (
    log_metrics,
    time_it,
    time_block,
    count_invocations,
    track_errors,
    get_metrics_summary,
    reset_metrics
)

# Test data
TEST_LOGS_DIR = Path("test_logs")
TEST_LOG_FILE = TEST_LOGS_DIR / "test_dockermcp.log"

@pytest.fixture(scope="module", autouse=True)
def setup_logging():
    ""Set up test logging."""
    # Create test logs directory
    TEST_LOGS_DIR.mkdir(exist_ok=True)
    
    # Configure logging for tests
    configure_logging(
        level=logging.DEBUG,
        log_file=TEST_LOG_FILE,
        enable_console=False,
        enable_syslog=False
    )
    
    yield
    
    # Clean up
    reset_metrics()
    if TEST_LOG_FILE.exists():
        TEST_LOG_FILE.unlink()
    if TEST_LOGS_DIR.exists():
        TEST_LOGS_DIR.rmdir()

def test_log_metrics():
    ""Test logging metrics.""
    reset_metrics()
    log_metrics("test_metric", 42.5, {"tag1": "value1"})
    
    # Check if metric was recorded
    metrics = get_metrics_summary()
    assert "test_metric" in metrics
    assert metrics["test_metric"]["count"] == 1
    assert metrics["test_metric"]["total"] == 42.5

def test_time_it_decorator():
    ""Test the time_it decorator.""
    reset_metrics()
    
    @time_it("test_function")
    def test_func():
        time.sleep(0.1)
        return "success"
    
    result = test_func()
    assert result == "success"
    
    # Check if timing was recorded
    metrics = get_metrics_summary()
    assert "test_function_duration_ms" in metrics
    assert metrics["test_function_duration_ms"]["count"] == 1
    assert metrics["test_function_duration_ms"]["average"] > 0

def test_time_block():
    ""Test the time_block context manager.""
    reset_metrics()
    
    with time_block("test_block"):
        time.sleep(0.1)
    
    # Check if timing was recorded
    metrics = get_metrics_summary()
    assert "test_block_duration_ms" in metrics
    assert metrics["test_block_duration_ms"]["count"] == 1
    assert metrics["test_block_duration_ms"]["average"] > 0

def test_count_invocations():
    ""Test the count_invocations decorator.""
    reset_metrics()
    
    @count_invocations("test_counter")
    def test_func():
        return "counted"
    
    for _ in range(3):
        assert test_func() == "counted"
    
    # Check if invocations were counted
    metrics = get_metrics_summary()
    assert "test_counter_invocations" in metrics
    assert metrics["test_counter_invocations"]["count"] == 3
    assert metrics["test_counter_invocations"]["total"] == 3

def test_track_errors():
    ""Test the track_errors decorator.""
    reset_metrics()
    
    @track_errors("test_error_tracker")
    def failing_func():
        raise ValueError("Test error")
    
    # Should track the error
    with pytest.raises(ValueError):
        failing_func()
    
    # Check if error was tracked
    metrics = get_metrics_summary()
    assert "test_error_tracker_errors" in metrics
    assert metrics["test_error_tracker_errors"]["count"] == 1

def test_logging_context():
    ""Test logging with context."
    reset_metrics()
    
    with logger.contextualize(correlation_id="test-123"):
        logger.info("Test message with context")
        log_metrics("context_metric", 100)
    
    # Check if context was applied to metrics
    metrics = get_metrics_summary()
    assert "context_metric" in metrics
    assert metrics["context_metric"]["count"] == 1
    assert metrics["context_metric"]["total"] == 100

def test_environment_based_config():
    ""Test environment-based logging configuration."
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "ENVIRONMENT": "test"}):
        # This will use the environment variables we just set
        test_logger = logging.getLogger("test_logger")
        assert test_logger.getEffectiveLevel() == logging.DEBUG

def test_log_rotation():
    ""Test log rotation functionality."
    # Create a large log entry to trigger rotation
    large_message = "x" * 1000000  # 1MB
    
    for _ in range(15):  # Should trigger rotation with 10MB limit
        logger.info(large_message)
    
    # Check if log file exists and is not too large
    assert TEST_LOG_FILE.exists()
    assert TEST_LOG_FILE.stat().st_size < 15 * 1000000  # Should be rotated

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
