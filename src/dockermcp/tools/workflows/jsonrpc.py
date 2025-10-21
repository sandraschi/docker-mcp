"""
JSON-RPC 2.0 models and utilities.

This module provides Pydantic models for handling JSON-RPC 2.0 messages
with proper validation and serialization.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Type, TypeVar, Union, Generic
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from .models.base import BaseModelConfig
from .models.responses import ErrorResponse

T = TypeVar('T')

class JSONRPCRequest(BaseModel, Generic[T]):
    """JSON-RPC 2.0 Request model.
    
    Attributes:
        jsonrpc: Must be exactly "2.0"
        method: The name of the method to be invoked
        params: The parameter values to be used during the invocation of the method
        id: An identifier established by the client that MUST contain a String, Number, or NULL
    """
    jsonrpc: Literal["2.0"] = Field("2.0", 
        description="Version of the JSON-RPC protocol. MUST be exactly '2.0'"
    )
    method: str = Field(
        ...,
        description="The name of the method to be invoked"
    )
    params: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None,
        description="The parameter values to be used during the invocation of the method"
    )
    id: Optional[Union[str, int, None]] = Field(
        default_factory=lambda: str(uuid4()),
        description="An identifier established by the client"
    )
    
    model_config = BaseModelConfig
    
    @classmethod
    def create(
        cls,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCRequest':
        """Create a new JSON-RPC request.
        
        Args:
            method: The name of the method to be invoked
            params: The parameter values for the method
            id: The request ID (auto-generated if not provided)
            
        Returns:
            A new JSONRPCRequest instance
        """
        return cls(
            method=method,
            params=params,
            id=id or str(uuid4())
        )
    
    @classmethod
    def notification(
        cls,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None
    ) -> 'JSONRPCRequest':
        """Create a new JSON-RPC notification (request without ID).
        
        Args:
            method: The name of the method to be invoked
            params: The parameter values for the method
            
        Returns:
            A new JSONRPCRequest instance with no ID
        """
        return cls(
            method=method,
            params=params,
            id=None
        )
    
    def is_notification(self) -> bool:
        """Check if this is a notification (no ID)."""
        return self.id is None


class JSONRPCResponse(BaseModel, Generic[T]):
    """JSON-RPC 2.0 Response model.
    
    Attributes:
        jsonrpc: Must be exactly "2.0"
        result: The result of the called method (on success)
        error: An error object (on failure)
        id: The request identifier that this response corresponds to
    """
    jsonrpc: Literal["2.0"] = Field("2.0",
        description="Version of the JSON-RPC protocol. MUST be exactly '2.0'"
    )
    result: Optional[T] = Field(
        None,
        description="The result of the called method (on success)"
    )
    error: Optional[Dict[str, Any]] = Field(
        None,
        description="An error object (on failure)"
    )
    id: Optional[Union[str, int, None]] = Field(
        None,
        description="The request identifier that this response corresponds to"
    )
    
    model_config = BaseModelConfig
    
    @classmethod
    def success(
        cls,
        result: T,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCResponse[T]':
        """Create a successful JSON-RPC response.
        
        Args:
            result: The result to include in the response
            id: The request ID this response corresponds to
            
        Returns:
            A new JSONRPCResponse instance with the result
        """
        return cls(
            result=result,
            id=id,
            error=None
        )
    
    @classmethod
    def error(
        cls,
        code: int,
        message: str,
        data: Optional[Any] = None,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCResponse[None]':
        """Create an error JSON-RPC response.
        
        Args:
            code: The error code
            message: A short description of the error
            data: Additional error information
            id: The request ID this error corresponds to
            
        Returns:
            A new JSONRPCResponse instance with the error
        """
        error = {
            "code": code,
            "message": message
        }
        
        if data is not None:
            error["data"] = data
            
        return cls(
            result=None,
            error=error,
            id=id
        )
    
    @classmethod
    def parse_error(
        cls,
        data: Optional[Any] = None,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCResponse[None]':
        """Create a parse error response."""
        return cls.error(
            code=-32700,
            message="Parse error",
            data=data,
            id=id
        )
    
    @classmethod
    def invalid_request(
        cls,
        data: Optional[Any] = None,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCResponse[None]':
        """Create an invalid request error response."""
        return cls.error(
            code=-32600,
            message="Invalid Request",
            data=data,
            id=id
        )
    
    @classmethod
    def method_not_found(
        cls,
        method: Optional[str] = None,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCResponse[None]':
        """Create a method not found error response."""
        return cls.error(
            code=-32601,
            message="Method not found",
            data={"method": method} if method else None,
            id=id
        )
    
    @classmethod
    def invalid_params(
        cls,
        data: Optional[Any] = None,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCResponse[None]':
        """Create an invalid params error response."""
        return cls.error(
            code=-32602,
            message="Invalid params",
            data=data,
            id=id
        )
    
    @classmethod
    def internal_error(
        cls,
        error: Optional[Exception] = None,
        id: Optional[Union[str, int, None]] = None
    ) -> 'JSONRPCResponse[None]':
        """Create an internal error response."""
        data = {
            "type": error.__class__.__name__ if error else None,
            "message": str(error) if error else None
        } if error else None
        
        return cls.error(
            code=-32603,
            message="Internal error",
            data=data,
            id=id
        )
    
    @model_validator(mode='after')
    def validate_result_or_error(self) -> 'JSONRPCResponse[T]':
        """Ensure either result or error is set, but not both."""
        if self.result is not None and self.error is not None:
            raise ValueError("Response cannot have both 'result' and 'error'")
        if self.result is None and self.error is None:
            raise ValueError("Response must have either 'result' or 'error'")
        return self


def create_jsonrpc_response(
    result: Optional[T] = None,
    error: Optional[Dict[str, Any]] = None,
    id: Optional[Union[str, int, None]] = None
) -> JSONRPCResponse[T]:
    """Create a JSON-RPC response.
    
    Args:
        result: The result to include in the response
        error: An error object to include in the response
        id: The request ID this response corresponds to
        
    Returns:
        A new JSONRPCResponse instance
        
    Raises:
        ValueError: If both result and error are provided or neither is provided
    """
    if result is not None and error is not None:
        raise ValueError("Cannot specify both result and error")
    if result is None and error is None:
        raise ValueError("Must specify either result or error")
        
    return JSONRPCResponse(
        result=result,
        error=error,
        id=id
    )
