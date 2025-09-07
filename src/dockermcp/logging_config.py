"""
Structured JSON logging configuration for Docker MCP.

This module provides a centralized logging configuration that ensures consistent
structured JSON logging across the entire application.
"""
import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the JSON formatter."""
        super().__init__(*args, **kwargs)
        self.datefmt = "%Y-%m-%dT%H:%M:%S%z"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string.
        
        Args:
            record: The log record to format.
            
        Returns:
            JSON string representation of the log record.
        """
        log_record: Dict[str, Any] = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
            'threadName': record.threadName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
            
        # Add stack trace if available
        if record.stack_info:
            log_record['stack'] = self.formatStack(record.stack_info)
            
        return json.dumps(log_record, ensure_ascii=False)

def configure_logging(level: int = logging.INFO, log_file: str = None) -> None:
    """Configure logging with JSON formatter.
    
    Args:
        level: Logging level to use (default: logging.INFO)
        log_file: Path to the log file. If not provided, logs will be written to 'logs/dockermcp.log'
    """
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    if not log_file:
        log_file = log_dir / 'dockermcp.log'
    
    # Remove all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    
    # Configure file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(JsonFormatter())
    
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    
    # Configure third-party loggers to be less verbose
    logging.getLogger('docker').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

# Configure logging when this module is imported
configure_logging()

# Create a module-level logger
logger = logging.getLogger(__name__)
