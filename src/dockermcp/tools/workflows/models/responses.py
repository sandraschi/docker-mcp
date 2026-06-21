"""
Response models for workflow API endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field

from .base import BaseModel
from .workflow import WorkflowStatus


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    status_code: int = Field(500, ge=400, le=599, description="HTTP status code")
    request_id: UUID = Field(default_factory=uuid4, description="Request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "validation_error",
                "message": "Invalid input data",
                "details": {"field": "name", "issue": "required field"},
                "status_code": 400,
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2023-01-01T12:00:00Z",
            }
        }
    )

    @classmethod
    def from_exception(
        cls, error: Exception, status_code: int = 500, request_id: UUID | None = None, **kwargs: Any
    ) -> "ErrorResponse":
        """Create an ErrorResponse from an exception."""
        error_class = error.__class__.__name__
        return cls(
            error=error_class.lower(),
            message=str(error) or error_class,
            details={"type": error_class, **kwargs},
            status_code=status_code,
            request_id=request_id or uuid4(),
        )


class WorkflowResponse(BaseModel):
    """Base response model for workflow operations."""

    workflow_id: UUID = Field(..., description="Unique identifier for the workflow")
    status: WorkflowStatus = Field(..., description="Current status of the workflow")
    created_at: datetime = Field(..., description="When the workflow was created")
    updated_at: datetime = Field(..., description="When the workflow was last updated")
    created_by: str = Field(..., description="User or system that created the workflow")
    error: dict[str, Any] | None = Field(None, description="Error details if the operation failed")


class CreateWorkflowResponse(WorkflowResponse):
    """Response model for creating a workflow."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "web-app",
                "status": "created",
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "created_by": "user@example.com",
            }
        }
    )


class StartWorkflowResponse(WorkflowResponse):
    """Response model for starting a workflow."""

    execution_id: UUID = Field(..., description="ID of the workflow execution")
    started_at: datetime = Field(..., description="When the workflow was started")


class StopWorkflowResponse(WorkflowResponse):
    """Response model for stopping a workflow."""

    stopped_at: datetime = Field(..., description="When the workflow was stopped")
    force_stopped: bool = Field(False, description="Whether the workflow was force-stopped")


class WorkflowSummary(BaseModel):
    """Summary of a workflow for listing endpoints."""

    workflow_id: str = Field(..., description="Unique identifier for the workflow")
    name: str = Field(..., description="Name of the workflow")
    status: str = Field(..., description="Current status of the workflow")
    created_at: datetime = Field(..., description="When the workflow was created")
    service_count: int = Field(..., description="Number of services in the workflow")


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflows": [
                    {
                        "workflow_id": "workflow_123",
                        "name": "web-app",
                        "status": "running",
                        "created_at": "2023-01-01T12:00:00Z",
                    }
                ],
                "total": 1,
                "limit": 10,
                "offset": 0,
                "message": "Found 1 workflow(s)",
            }
        }
    )

    workflows: list[WorkflowSummary] = Field(..., description="List of workflows")
    total: int = Field(..., description="Total number of workflows")
    limit: int = Field(..., description="Maximum number of workflows per page")
    offset: int = Field(..., description="Number of workflows skipped")
    message: str = Field(..., description="Status message")
