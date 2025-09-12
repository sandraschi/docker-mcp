"""
Workflow management models for Docker MCP.

This module contains Pydantic models for workflow management operations.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, AnyUrl, validator

class WorkflowStatus(str, Enum):
    """Status of a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ServiceHealth(str, Enum):
    """Health status of a service."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    UNKNOWN = "unknown"

class ServiceDefinition(BaseModel):
    """Definition of a service in a workflow."""
    name: str = Field(..., description="Name of the service")
    image: str = Field(..., description="Docker image to use")
    command: Optional[Union[str, List[str]]] = Field(
        None,
        description="Command to run in the container"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
    ports: Dict[str, str] = Field(
        default_factory=dict,
        description="Port mappings (host:container)"
    )
    volumes: Dict[str, str] = Field(
        default_factory=dict,
        description="Volume mappings (host:container)"
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description="Services this service depends on"
    )
    healthcheck: Optional[Dict[str, Any]] = Field(
        None,
        description="Health check configuration"
    )
    restart_policy: str = Field(
        "no",
        description="Restart policy (no, on-failure, always, unless-stopped)"
    )
    mem_limit: Optional[Union[int, str]] = Field(
        None,
        description="Memory limit (e.g., '1g', 1073741824)"
    )
    cpus: Optional[float] = Field(
        None,
        description="CPU limit in CPU units (e.g., 0.5 for half a CPU)"
    )

class WorkflowDefinition(BaseModel):
    """Definition of a workflow."""
    name: str = Field(..., description="Name of the workflow")
    version: str = Field("1.0", description="Workflow version")
    services: Dict[str, ServiceDefinition] = Field(
        ...,
        description="Services in the workflow"
    )
    networks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Networks to create"
    )
    volumes: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Volumes to create"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Global environment variables"
    )

class WorkflowState(BaseModel):
    """Runtime state of a workflow."""
    workflow_id: str = Field(..., description="Unique ID of the workflow")
    name: str = Field(..., description="Name of the workflow")
    status: WorkflowStatus = Field(
        WorkflowStatus.PENDING,
        description="Current status of the workflow"
    )
    start_time: Optional[datetime] = Field(
        None,
        description="When the workflow started"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="When the workflow ended"
    )
    services: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="State of each service"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if the workflow failed"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the workflow was created"
    )

# Request and Response Models for API Endpoints
class CreateWorkflowRequest(BaseModel):
    """Request model for creating a workflow."""
    workflow_definition: WorkflowDefinition = Field(
        ...,
        description="Workflow definition"
    )
    workflow_id: Optional[str] = Field(
        None,
        description="Optional workflow ID (generated if not provided)"
    )

class CreateWorkflowResponse(BaseModel):
    """Response model for creating a workflow."""
    workflow_id: str = Field(..., description="ID of the created workflow")
    name: str = Field(..., description="Name of the workflow")
    status: WorkflowStatus = Field(..., description="Initial status of the workflow")
    created_at: datetime = Field(..., description="When the workflow was created")
    message: str = Field(..., description="Status message")

class StartWorkflowRequest(BaseModel):
    """Request model for starting a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow to start")
    timeout: int = Field(
        300,
        ge=1,
        le=3600,
        description="Timeout in seconds"
    )

class StartWorkflowResponse(BaseModel):
    """Response model for starting a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow")
    status: WorkflowStatus = Field(..., description="Current status of the workflow")
    start_time: datetime = Field(..., description="When the workflow started")
    message: str = Field(..., description="Status message")

class StopWorkflowRequest(BaseModel):
    """Request model for stopping a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow to stop")
    force: bool = Field(
        False,
        description="Whether to force stop the workflow"
    )

class StopWorkflowResponse(BaseModel):
    """Response model for stopping a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow")
    status: WorkflowStatus = Field(..., description="Current status of the workflow")
    end_time: datetime = Field(..., description="When the workflow was stopped")
    message: str = Field(..., description="Status message")

class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    workflow_id: str = Field(..., description="ID of the workflow")
    name: str = Field(..., description="Name of the workflow")
    status: WorkflowStatus = Field(..., description="Current status of the workflow")
    start_time: Optional[datetime] = Field(None, description="When the workflow started")
    end_time: Optional[datetime] = Field(None, description="When the workflow ended")
    services: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Status of each service in the workflow"
    )
    error: Optional[str] = Field(None, description="Error message if the workflow failed")

class ListWorkflowsRequest(BaseModel):
    """Request model for listing workflows."""
    status: str = Field(
        "all",
        description="Filter workflows by status (all, running, completed, failed, cancelled)"
    )
    limit: int = Field(
        50,
        ge=1,
        le=1000,
        description="Maximum number of workflows to return"
    )
    offset: int = Field(
        0,
        ge=0,
        description="Number of workflows to skip"
    )

class WorkflowSummary(BaseModel):
    """Summary of a workflow for listing."""
    workflow_id: str = Field(..., description="ID of the workflow")
    name: str = Field(..., description="Name of the workflow")
    status: WorkflowStatus = Field(..., description="Current status of the workflow")
    created_at: datetime = Field(..., description="When the workflow was created")
    start_time: Optional[datetime] = Field(None, description="When the workflow started")
    end_time: Optional[datetime] = Field(None, description="When the workflow ended")
    service_count: int = Field(..., description="Number of services in the workflow")

class ListWorkflowsResponse(BaseModel):
    """Response model for listing workflows."""
    workflows: List[WorkflowSummary] = Field(..., description="List of workflows")
    total: int = Field(..., description="Total number of workflows")
    limit: int = Field(..., description="Maximum number of workflows per page")
    offset: int = Field(..., description="Number of workflows skipped")
    message: str = Field(..., description="Status message")
