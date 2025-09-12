"""
Assorted utility functions and classes that don't fit into other modules.
"""
import json
import logging
from typing import Any, Dict, Optional

class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles common types."""
    def default(self, obj):
        if hasattr(obj, 'model_dump_json'):
            return json.loads(obj.model_dump_json())
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'total_seconds'):
            return obj.total_seconds()
        return super().default(obj)

def warn_with_log(message, category, filename, lineno, file=None, line=None):
    """Redirect warnings to the logger."""
    logger = logging.getLogger('dockermcp.server')
    logger.warning(f"{filename}:{lineno}: {category.__name__}: {message}")

class SafeFastMCP:
    """Wrapper for FastMCP with enhanced error handling.
    
    Note: This class is deprecated. Use the singleton instance from mcp_instance.py instead.
    """
    
    def __init__(self, *args, **kwargs):
        from dockermcp.mcp_instance import get_mcp
        logger = logging.getLogger('dockermcp.server')
        logger.warning("SafeFastMCP is deprecated. Use the singleton instance from mcp_instance.py instead.")
        self._mcp = get_mcp()  # Use the singleton instance
        
    async def _handle_message(self, message: str) -> str:
        """Handle incoming JSON-RPC messages with proper error handling."""
        from dockermcp.utils.json_utils import safe_json_dumps
        logger = logging.getLogger('dockermcp.server')
        
        try:
            # Create a log record with JSON disabled for RPC messages
            log_record = logging.LogRecord(
                name=__name__,
                level=logging.DEBUG,
                pathname=__file__,
                lineno=0,
                msg=f"Received message: {message[:200] + '...' if len(message) > 200 else message}",
                args=(),
                exc_info=None
            )
            log_record.disable_json = True  # Disable JSON formatting for RPC logs
            logger.handle(log_record)
            
            # Check for common issues
            if not message or not message.strip():
                logger.warning("Received empty message")
                return ''
                
            if message.startswith(('Warning:', 'Error:')):
                logger.warning(f"Received warning/error message: {message}")
                return ''
                
            # Clean and parse the message
            message = message.strip()
            
            # Skip empty messages or warnings
            if not message or message.startswith(('WARNING:', 'Warning:')):
                logger.warning(f"Skipping message: {message[:200]}...")
                return ''
                
            # Process the message normally
            return await self._mcp._handle_message(message)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}", exc_info=True)
            return safe_json_dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            })
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return safe_json_dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            })
    
    def tool(self, *args, **kwargs):
        """Register a tool with the underlying FastMCP instance."""
        return self._mcp.tool(*args, **kwargs)
    
    async def serve(self, *args, **kwargs):
        """Start serving requests."""
        return await self._mcp.serve(*args, **kwargs)
    
    @property
    def json_encoder(self):
        return self._mcp.json_encoder
    
    @json_encoder.setter
    def json_encoder(self, encoder):
        self._mcp.json_encoder = encoder
