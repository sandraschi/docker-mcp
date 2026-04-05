"""
Request models for workflow API endpoints.
"""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field

from .base import BaseModel


class WorkflowRequest(BaseModel):
    """Base class for workflow-related API requests."""
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the request"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the request was created"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the request"
    )


class CreateWorkflowRequest(WorkflowRequest):
    """Request model for creating a new workflow."""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the workflow")
    description: str | None = Field(None, description="Description of the workflow")
    services: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of service definitions"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters for the workflow"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing the workflow"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "web-app",
                "description": "Deploy a web application",
                "services": [
                    {
                        "name": "web",
                        "image": "nginx:alpine",
                        "ports": ["80:80"]
                    }
                ],
                "tags": ["web", "deployment"]
            }
        }
    )


class StartWorkflowRequest(WorkflowRequest):
    """Request model for starting a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow to start")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime parameters for the workflow"
    )


class StopWorkflowRequest(WorkflowRequest):
    """Request model for stopping a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow to stop")
    force: bool = Field(
        False,
        description="Whether to force stop the workflow"
    )


class ListWorkflowsRequest(WorkflowRequest):
    """Request model for listing workflows."""
    limit: int = Field(
        100,
        ge=1,
        le=1000,
        description="Maximum number of workflows to return"
    )
    offset: int = Field(0, ge=0, description="Number of workflows to skip")
    status: str | None = Field(
        None,
        description="Filter workflows by status"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Filter workflows by tags"
    )
    sort_by: str = Field(
        "created_at",
        description="Field to sort by"
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order: 'asc' or 'desc'"
    )
