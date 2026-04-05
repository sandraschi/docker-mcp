"""
Workflow Models Package

This package contains all the data models for the workflow system.
"""
from .base import BaseModel, BaseModelConfig
from .service import ServiceHealth, ServiceDefinition
from .workflow import WorkflowDefinition, WorkflowStatus, WorkflowState
from .requests import (
    WorkflowRequest,
    CreateWorkflowRequest,
    StartWorkflowRequest,
    StopWorkflowRequest,
    ListWorkflowsRequest
)
from .responses import (
    WorkflowResponse,
    CreateWorkflowResponse,
    StartWorkflowResponse,
    StopWorkflowResponse,
    WorkflowListResponse,
    WorkflowSummary,
    ErrorResponse,
)

# Aliases for workflow_management imports
WorkflowStatusResponse = WorkflowResponse
ListWorkflowsResponse = WorkflowListResponse

__all__ = [
    'BaseModel',
    'BaseModelConfig',
    'ServiceHealth',
    'ServiceDefinition',
    'WorkflowDefinition',
    'WorkflowStatus',
    'WorkflowState',
    'WorkflowRequest',
    'CreateWorkflowRequest',
    'StartWorkflowRequest',
    'StopWorkflowRequest',
    'ListWorkflowsRequest',
    'WorkflowResponse',
    'CreateWorkflowResponse',
    'StartWorkflowResponse',
    'StopWorkflowResponse',
    'WorkflowListResponse',
    'WorkflowSummary',
    'WorkflowStatusResponse',
    'ListWorkflowsResponse',
    'ErrorResponse',
]
