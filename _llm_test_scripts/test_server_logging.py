#!/usr/bin/env python3
"""
Test script to verify server logging configuration.
"""
import json
import logging
import sys
from datetime import UTC, datetime


def setup_logging():
    """Set up JSON logging configuration."""
    class JSONFormatter(logging.Formatter):
        """Custom JSON formatter for structured logging."""

        def format(self, record):
            log_record = {
                'timestamp': datetime.now(UTC).isoformat(),
                'level': record.levelname,
                'name': record.name,
                'message': record.getMessage(),
            }

            # Add exception info if present
            if record.exc_info:
                log_record['exception'] = self.formatException(record.exc_info)

            # Add extra attributes
            for key, value in record.__dict__.items():
                if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'levelname',
                              'levelno', 'lineno', 'module', 'msecs', 'message', 'msg', 'name', 'pathname',
                              'process', 'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'):
                    if key not in log_record:  # Don't override existing fields
                        if hasattr(value, 'isoformat'):
                            log_record[key] = value.isoformat()
                        else:
                            log_record[key] = value

            return json.dumps(log_record, default=str)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add a handler with our JSON formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

def test_logging():
    """Test logging with different levels and structured data."""
    logger = logging.getLogger("test")

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message", extra={"key1": "value1"})
    logger.warning("This is a warning", extra={"key2": [1, 2, 3]})

    try:
        # Generate an error with stack trace
        result = 1 / 0
    except Exception:
        logger.error("An error occurred", exc_info=True, extra={"key3": {"nested": "value"}})

    logger.critical("This is a critical message", extra={"key4": True})

if __name__ == "__main__":
    print("Testing server logging configuration...")
    setup_logging()
    test_logging()
    print("Test complete. Check the output above for JSON-formatted logs.")
