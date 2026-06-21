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
    BaseModelConfig,
    ErrorResponse,
    ListWorkflowsRequest,
    ServiceDefinition,
    ServiceHealth,
    WorkflowListResponse,
    WorkflowRequest,
    WorkflowResponse,
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
    "WORKFLOW_VALIDATOR",
    "BaseHealthCheck",
    # Models
    "BaseModelConfig",
    "CommandHealthCheck",
    "ConstraintError",
    "CustomHealthCheck",
    "DependencyError",
    "ErrorResponse",
    "HTTPHealthCheck",
    "HealthCheckResult",
    # Health Checks
    "HealthCheckType",
    "HealthChecker",
    # JSON-RPC
    "JSONRPCRequest",
    "JSONRPCResponse",
    "ListWorkflowsRequest",
    # RPC Handler
    "RPCHandler",
    "ResourceConstraintValidator",
    "ServiceDefinition",
    "ServiceDependencyValidator",
    "ServiceHealth",
    "TCPHealthCheck",
    # Validators
    "ValidationError",
    "WorkflowListResponse",
    "WorkflowRequest",
    "WorkflowResponse",
    "WorkflowStateValidator",
    "WorkflowStatus",
    "WorkflowValidator",
    "create_health_check",
    "create_jsonrpc_response",
    "handle_message",
    "health_check_from_service",
    "method",
]
