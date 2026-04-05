"""
Workflow management for Docker MCP.

This package provides models, validators, and handlers for managing workflows
in the Docker MCP system. It includes support for JSON-RPC 2.0 communication,
service health checks, and workflow state management.
"""

# Import key components to make them available at the package level
from .health_checks import (
    BaseHealthCheck,
    CommandHealthCheck,
    CustomHealthCheck,
    HealthChecker,
    HealthCheckResult,
    HealthCheckType,
    HTTPHealthCheck,
    TCPHealthCheck,
    create_health_check,
    health_check_from_service,
)
from .jsonrpc import JSONRPCRequest, JSONRPCResponse, create_jsonrpc_response
from .models import (
    # Base models
    BaseModel,
    BaseModelConfig,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    ErrorResponse,
    ListWorkflowsRequest,
    ServiceDefinition,
    # Service models
    ServiceHealth,
    StartWorkflowRequest,
    StartWorkflowResponse,
    StopWorkflowRequest,
    StopWorkflowResponse,
    WorkflowDefinition,
    WorkflowListResponse,
    # Request models
    WorkflowRequest,
    # Response models
    WorkflowResponse,
    WorkflowState,
    # Workflow models
    WorkflowStatus,
)
from .rpc_handler import RPCHandler, handle_message, method
from .validators import (
    WORKFLOW_VALIDATOR,
    ConstraintError,
    DependencyError,
    ResourceConstraintValidator,
    ServiceDependencyValidator,
    ValidationError,
    WorkflowStateValidator,
    WorkflowValidator,
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

