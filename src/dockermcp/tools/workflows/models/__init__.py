"""
Workflow Models Package

This package contains all the data models for the workflow system.
"""
from .base import BaseModel, BaseModelConfig
from .requests import (
    CreateWorkflowRequest,
    ListWorkflowsRequest,
    StartWorkflowRequest,
    StopWorkflowRequest,
    WorkflowRequest,
)
from .responses import (
    CreateWorkflowResponse,
    ErrorResponse,
    StartWorkflowResponse,
    StopWorkflowResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowSummary,
)
from .service import ServiceDefinition, ServiceHealth
from .workflow import WorkflowDefinition, WorkflowState, WorkflowStatus

# Aliases for workflow_management imports
WorkflowStatusResponse = WorkflowResponse
ListWorkflowsResponse = WorkflowListResponse

__all__ = [
    'BaseModel',
    'BaseModelConfig',
    'CreateWorkflowRequest',
    'CreateWorkflowResponse',
    'ErrorResponse',
    'ListWorkflowsRequest',
    'ListWorkflowsResponse',
    'ServiceDefinition',
    'ServiceHealth',
    'StartWorkflowRequest',
    'StartWorkflowResponse',
    'StopWorkflowRequest',
    'StopWorkflowResponse',
    'WorkflowDefinition',
    'WorkflowListResponse',
    'WorkflowRequest',
    'WorkflowResponse',
    'WorkflowState',
    'WorkflowStatus',
    'WorkflowStatusResponse',
    'WorkflowSummary',
]
