#!/usr/bin/env python3
"""
Test script to verify JSON logging configuration.
"""
import json
import logging
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'levelname', 
                          'levelno', 'lineno', 'module', 'msecs', 'message', 'msg', 'name', 'pathname', 
                          'process', 'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'):
                if key not in log_record:  # Don't override existing fields
                    log_record[key] = value
        
        return json.dumps(log_record, default=str)

def setup_logging():
    """Set up JSON logging configuration."""
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
    """Test different log levels and structured logging."""
    logger = logging.getLogger("test_logger")
    
    # Test different log levels
    logger.debug("This is a debug message", extra={"key1": "value1"})
    logger.info("This is an info message", extra={"key2": 123})
    logger.warning("This is a warning", extra={"key3": [1, 2, 3]})
    
    try:
        # Generate an error with stack trace
        result = 1 / 0
    except Exception as e:
        logger.error("An error occurred", exc_info=True, extra={"key4": {"nested": "value"}})
    
    logger.critical("This is a critical message", extra={"key5": True})

if __name__ == "__main__":
    print("Testing JSON logging... (check stderr for JSON output)")
    setup_logging()
    test_logging()
    print("Test complete. Check the output above for JSON-formatted logs.")
