"""
JSON-RPC request handler for the Docker MCP service.

This module provides a handler for processing JSON-RPC 2.0 messages
and dispatching them to the appropriate service methods.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from pydantic import ValidationError

from .jsonrpc import JSONRPCRequest, JSONRPCResponse, create_jsonrpc_response
from .models.base import BaseModel, BaseModelConfig

# Type variable for the handler function
T = TypeVar('T')

class RPCHandler:
    """Handler for JSON-RPC 2.0 messages."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the RPC handler.
        
        Args:
            logger: Optional logger instance for logging messages
        """
        self.logger = logger or logging.getLogger(__name__)
        self._methods: Dict[str, Callable[..., Any]] = {}
    
    def register_method(self, name: str, func: Callable[..., Any]) -> None:
        """Register a method that can be called via JSON-RPC.
        
        Args:
            name: The name of the method as it will be called in JSON-RPC
            func: The function to call when this method is invoked
        """
        self._methods[name] = func
        self.logger.debug("Registered method: %s", name)
    
    def method(self, name: Optional[str] = None):        
        """Decorator to register a method.
        
        Args:
            name: Optional name for the method (defaults to function name)
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            method_name = name or func.__name__
            self.register_method(method_name, func)
            return func
        return decorator
    
    async def handle_message(
        self,
        message: Union[str, bytes, Dict[str, Any], List[Dict[str, Any]]]
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Handle an incoming JSON-RPC message.
        
        Args:
            message: The JSON-RPC message to handle (can be a batch request)
            
        Returns:
            The JSON-RPC response or list of responses for batch requests
        """
        try:
            # Parse the message if it's a string or bytes
            if isinstance(message, (str, bytes)):
                try:
                    parsed = json.loads(message)
                except json.JSONDecodeError as e:
                    self.logger.error("Failed to parse JSON: %s", e)
                    return JSONRPCResponse.parse_error("Invalid JSON").model_dump(exclude_none=True)
            else:
                parsed = message
            
            # Handle batch requests
            if isinstance(parsed, list):
                if not parsed:  # Empty batch
                    return JSONRPCResponse.invalid_request("Empty batch").model_dump(exclude_none=True)
                
                # Process each request in the batch
                responses = []
                for request in parsed:
                    response = await self._handle_single_request(request)
                    if response is not None:  # Only include non-notification responses
                        responses.append(response)
                
                return [r.model_dump(exclude_none=True) for r in responses] if responses else ""
            
            # Handle single request
            response = await self._handle_single_request(parsed)
            return response.model_dump(exclude_none=True) if response is not None else ""
            
        except Exception as e:
            self.logger.exception("Error handling message")
            return JSONRPCResponse.internal_error(e).model_dump(exclude_none=True)
    
    async def _handle_single_request(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[JSONRPCResponse]:
        """Handle a single JSON-RPC request.
        
        Args:
            request_data: The parsed JSON-RPC request
            
        Returns:
            A JSON-RPC response, or None for notifications
        """
        # Parse and validate the request
        try:
            request = JSONRPCRequest[Any].model_validate(request_data)
        except ValidationError as e:
            self.logger.error("Invalid request: %s", e)
            return JSONRPCResponse.invalid_request(str(e))
        
        # Log the request
        self.logger.debug(
            "Processing request: method=%s, id=%s",
            request.method,
            request.id
        )
        
        # Handle notifications (no response needed)
        if request.is_notification():
            asyncio.create_task(self._execute_method(request, request.id))
            return None
        
        # Execute the method and return the response
        return await self._execute_method(request, request.id)
    
    async def _execute_method(
        self,
        request: JSONRPCRequest[Any],
        request_id: Optional[Union[str, int]] = None
    ) -> JSONRPCResponse:
        """Execute a method and return the response.
        
        Args:
            request: The JSON-RPC request
            request_id: The request ID (for error responses)
            
        Returns:
            A JSON-RPC response
        """
        # Check if the method exists
        if request.method not in self._methods:
            self.logger.error("Method not found: %s", request.method)
            return JSONRPCResponse.method_not_found(request.method, request_id)
        
        method = self._methods[request.method]
        
        try:
            # Call the method with the provided params
            if isinstance(request.params, dict):
                result = await self._call_method(method, **request.params)
            elif isinstance(request.params, list):
                result = await self._call_method(method, *request.params)
            else:
                result = await self._call_method(method)
            
            # Return the result
            return JSONRPCResponse.success(result, request_id)
            
        except ValidationError as e:
            self.logger.error("Validation error in %s: %s", request.method, e)
            return JSONRPCResponse.invalid_params(
                data={"errors": e.errors()},
                id=request_id
            )
        except Exception as e:
            self.logger.exception("Error executing method %s", request.method)
            return JSONRPCResponse.internal_error(e, request_id)
    
    async def _call_method(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call a method with the provided arguments."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)


# Global handler instance
handler = RPCHandler()

# Decorator for registering methods
method = handler.method

# Main entry point for handling messages
async def handle_message(message: Union[str, bytes, Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Handle a JSON-RPC message.
    
    This is the main entry point for the RPC handler.
    
    Args:
        message: The JSON-RPC message to handle
        
    Returns:
        The JSON-RPC response or list of responses for batch requests
    """
    return await handler.handle_message(message)
