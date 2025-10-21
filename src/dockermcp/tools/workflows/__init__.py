"""
Workflow management for Docker MCP.

This package provides models, validators, and handlers for managing workflows
in the Docker MCP system. It includes support for JSON-RPC 2.0 communication,
service health checks, and workflow state management.
"""

# Import key components to make them available at the package level
from .models import (
    # Base models
    BaseModel,
    BaseModelConfig,
    
    # Service models
    ServiceHealth,
    ServiceDefinition,
    
    # Workflow models
    WorkflowStatus,
    WorkflowDefinition,
    WorkflowState,
    
    # Request models
    WorkflowRequest,
    CreateWorkflowRequest,
    StartWorkflowRequest,
    StopWorkflowRequest,
    ListWorkflowsRequest,
    
    # Response models
    WorkflowResponse,
    CreateWorkflowResponse,
    StartWorkflowResponse,
    StopWorkflowResponse,
    WorkflowListResponse,
    ErrorResponse
)

from .validators import (
    ValidationError,
    DependencyError,
    ConstraintError,
    WorkflowValidator,
    ServiceDependencyValidator,
    ResourceConstraintValidator,
    WorkflowStateValidator,
    WORKFLOW_VALIDATOR
)

from .health_checks import (
    HealthCheckType,
    HealthCheckResult,
    BaseHealthCheck,
    CommandHealthCheck,
    HTTPHealthCheck,
    TCPHealthCheck,
    CustomHealthCheck,
    HealthChecker,
    create_health_check,
    health_check_from_service
)

from .jsonrpc import (
    JSONRPCRequest,
    JSONRPCResponse,
    create_jsonrpc_response
)

from .rpc_handler import (
    RPCHandler,
    handle_message,
    method
)

__all__ = [
    # Models
    'BaseModelConfig',
    'WorkflowStatus',
    'ServiceHealth',
    'ServiceDefinition',
    'WorkflowRequest',
    'WorkflowResponse',
    'ListWorkflowsRequest',
    'WorkflowListResponse',
    'ErrorResponse',
    
    # Validators
    'ValidationError',
    'DependencyError',
    'ConstraintError',
    'WorkflowValidator',
    'ServiceDependencyValidator',
    'ResourceConstraintValidator',
    'WorkflowStateValidator',
    'WORKFLOW_VALIDATOR',
    
    # Health Checks
    'HealthCheckType',
    'HealthCheckResult',
    'BaseHealthCheck',
    'CommandHealthCheck',
    'HTTPHealthCheck',
    'TCPHealthCheck',
    'CustomHealthCheck',
    'HealthChecker',
    'create_health_check',
    'health_check_from_service',
    
    # JSON-RPC
    'JSONRPCRequest',
    'JSONRPCResponse',
    'create_jsonrpc_response',
    
    # RPC Handler
    'RPCHandler',
    'handle_message',
    'method'
]

