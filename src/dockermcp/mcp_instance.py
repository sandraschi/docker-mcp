"""
FastMCP Singleton Instance

This module provides a single, shared FastMCP instance for the entire application.
This is the ONLY place where FastMCP should be initialized.
"""
import json
import logging
import threading
import traceback
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import FastMCPError

from . import __version__

# Set up logging
logger = logging.getLogger(__name__)

# Thread-safe singleton pattern
class FastMCPSingleton:
    _instance: Optional['FastMCPSingleton'] = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls) -> 'FastMCPSingleton':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize the FastMCP instance with proper error handling."""
        if not self._initialized:
            try:
                logger.info("Initializing FastMCP instance...")
                
                # Initialize FastMCP with minimal settings
                self.mcp = FastMCP(
                    name="docker-mcp",
                    version=__version__
                )
                
                # Patch the message handler to handle custom protocol versions
                self._patch_message_handler()
                
                logger.info(f"FastMCP instance initialized: {self.mcp.name} v{self.mcp.version}")
                self._initialized = True
                
            except Exception as e:
                logger.error(f"Failed to initialize FastMCP: {str(e)}")
                logger.debug(f"Error details: {traceback.format_exc()}")
                raise
    
    def _patch_message_handler(self) -> None:
        """Patch the message handler to support custom protocol versions."""
        try:
            if not hasattr(self.mcp, '_server'):
                logger.warning("FastMCP server instance not found, skipping message handler patch")
                return
                
            server = self.mcp._server
            original_handler = getattr(server, '_handle_message', None)
            
            if not callable(original_handler):
                logger.warning("Could not find original message handler, skipping patch")
                return
            
            async def patched_handler(transport: Any, message: str) -> Optional[str]:
                """Handle messages with custom protocol versions."""
                try:
                    # Parse the incoming message
                    try:
                        msg_dict = json.loads(message)
                        
                        # Check if this is a JSON-RPC message with a custom version
                        if (isinstance(msg_dict, dict) and 
                            'jsonrpc' in msg_dict and 
                            msg_dict.get('jsonrpc') != '2.0'):
                            
                            custom_version = msg_dict['jsonrpc']
                            logger.debug(f"Handling custom protocol version: {custom_version}")
                            
                            # Process with standard version
                            msg_dict['jsonrpc'] = '2.0'
                            response = await original_handler(transport, json.dumps(msg_dict))
                            
                            # Restore custom version in response if needed
                            if response:
                                try:
                                    resp_dict = json.loads(response)
                                    if isinstance(resp_dict, dict):
                                        resp_dict['jsonrpc'] = custom_version
                                        return json.dumps(resp_dict)
                                except json.JSONDecodeError:
                                    pass
                            return response
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Received invalid JSON message: {message[:100]}...")
                    
                    # Standard message handling
                    return await original_handler(transport, message)
                    
                except Exception as e:
                    logger.error(f"Error in message handler: {str(e)}")
                    logger.debug(f"Error details: {traceback.format_exc()}")
                    raise
            
            # Replace the message handler
            server._handle_message = patched_handler
            logger.debug("Successfully patched FastMCP message handler")
            
        except Exception as e:
            logger.error(f"Failed to patch message handler: {str(e)}")
            logger.debug(f"Error details: {traceback.format_exc()}")

# Create the singleton instance
_singleton: FastMCPSingleton = FastMCPSingleton()

def get_mcp() -> FastMCP:
    """
    Get the shared FastMCP instance.
    This is the ONLY way to access the FastMCP instance in the application.
    
    Returns:
        FastMCP: The singleton FastMCP instance
        
    Raises:
        RuntimeError: If the FastMCP instance failed to initialize
    """
    if not _singleton._initialized:
        raise RuntimeError("FastMCP instance failed to initialize")
    return _singleton.mcp

# For backward compatibility
mcp = get_mcp()
