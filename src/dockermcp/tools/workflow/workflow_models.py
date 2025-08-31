"""
Workflow models for Docker MCP.

This module contains Pydantic models for workflow-related requests and responses.
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, HttpUrl, ConfigDict
from datetime import datetime
from enum import Enum

class WorkflowStatus(str, Enum):
    """Workflow status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStep(BaseModel):
    """Model for a workflow step."""
    id: str = Field(..., description="Unique identifier for the step")
    name: str = Field(..., description="Name of the step")
    description: Optional[str] = Field(None, description="Step description")
    command: str = Field(..., description="Command to execute")
    args: Optional[Dict[str, Any]] = Field(None, description="Command arguments")
    depends_on: Optional[List[str]] = Field(None, description="Step dependencies")
    retry_count: int = Field(0, description="Number of retry attempts")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    working_dir: Optional[str] = Field(None, description="Working directory")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")

class WorkflowDefinition(BaseModel):
    """Model for a workflow definition."""
    id: str = Field(..., description="Unique identifier for the workflow")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: str = Field("1.0.0", description="Workflow version")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    steps: List[WorkflowStep] = Field(..., description="List of workflow steps")
    env: Optional[Dict[str, str]] = Field(None, description="Global environment variables")
    timeout: Optional[int] = Field(None, description="Global timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")

class WorkflowInstance(BaseModel):
    """Model for a workflow instance."""
    id: str = Field(..., description="Unique identifier for the instance")
    workflow_id: str = Field(..., description="Reference to workflow definition")
    status: WorkflowStatus = Field(WorkflowStatus.PENDING, description="Current status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    created_by: Optional[str] = Field(None, description="User who created the instance")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Runtime parameters")
    error: Optional[str] = Field(None, description="Error message if failed")

class WorkflowExecution(BaseModel):
    """Model for workflow execution details."""
    step_id: str = Field(..., description="Step identifier")
    status: WorkflowStatus = Field(WorkflowStatus.PENDING, description="Execution status")
    start_time: Optional[datetime] = Field(None, description="Start timestamp")
    end_time: Optional[datetime] = Field(None, description="End timestamp")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    output: Optional[Any] = Field(None, description="Execution output")
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retry attempts")

class WorkflowResponse(BaseModel):
    """Standard workflow operation response."""
    success: bool
    message: str
    workflow_id: Optional[str] = None
    instance_id: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CreateWorkflowRequest(BaseModel):
    """Request model for creating a workflow."""
    name: str = Field(..., description="Name of the workflow")
    description: Optional[str] = Field(None, description="Workflow description")
    steps: List[WorkflowStep] = Field(..., description="List of workflow steps")
    env: Optional[Dict[str, str]] = Field(None, description="Global environment variables")
    timeout: Optional[int] = Field(None, description="Global timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")

class ExecuteWorkflowRequest(BaseModel):
    """Request model for executing a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Runtime parameters")
    async_exec: bool = Field(True, description="Run asynchronously")
    timeout: Optional[int] = Field(None, description="Override workflow timeout")

class WorkflowStatusResponse(WorkflowResponse):
    """Response model for workflow status."""
    executions: List[WorkflowExecution] = Field(default_factory=list, description="Step executions")
    progress: float = Field(0.0, description="Completion percentage (0-100)")
    current_step: Optional[str] = Field(None, description="Current executing step ID")

class WorkflowListResponse(WorkflowResponse):
    """Response model for listing workflows."""
    workflows: List[Dict[str, Any]] = Field(default_factory=list, description="List of workflows")
    total: int = Field(0, description="Total number of workflows")
