"""
Workflow-related models.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field

from .base import BaseModel
from .service import ServiceDefinition


class WorkflowStatus(StrEnum):
    """Possible statuses of a workflow."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    PAUSED = "paused"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"

    @classmethod
    def is_terminal(cls, status: "WorkflowStatus") -> bool:
        """Check if a status is terminal (no further state changes)."""
        return status in (cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.PAUSED, cls.TIMED_OUT, cls.SKIPPED)


class WorkflowDefinition(BaseModel):
    """Definition of a workflow."""

    name: str = Field(..., min_length=1, max_length=255, description="Name of the workflow")
    description: str | None = Field(None, description="Description of the workflow")
    services: list[ServiceDefinition] = Field(..., min_length=1, description="Services that make up this workflow")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Input parameters for the workflow")
    tags: list[str] = Field(default_factory=list, description="Tags for categorizing the workflow")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "web-app",
                "description": "Deploy a web application with a database",
                "services": [
                    {"name": "web", "image": "nginx:alpine", "ports": ["80:80"]},
                    {"name": "db", "image": "postgres:13", "environment": {"POSTGRES_PASSWORD": "example"}},
                ],
                "tags": ["web", "database"],
            }
        }
    )


class WorkflowState(BaseModel):
    """Runtime state of a workflow."""

    workflow_id: str = Field(..., description="ID of the workflow")
    status: WorkflowStatus = Field(default=WorkflowStatus.CREATED, description="Current status of the workflow")
    start_time: datetime | None = Field(None, description="When the workflow execution started")
    end_time: datetime | None = Field(None, description="When the workflow execution completed")
    error: dict[str, Any] | None = Field(None, description="Error details if the workflow failed")

    def is_running(self) -> bool:
        """Check if the workflow is currently running."""
        return self.status == WorkflowStatus.RUNNING

    def is_completed(self) -> bool:
        """Check if the workflow has completed successfully."""
        return self.status == WorkflowStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if the workflow has failed."""
        return self.status == WorkflowStatus.FAILED

    def is_cancelled(self) -> bool:
        """Check if the workflow was cancelled."""
        return self.status == WorkflowStatus.CANCELLED

    def get_duration(self) -> float | None:
        """Get the duration of the workflow in seconds."""
        if not self.start_time:
            return None

        end_time = self.end_time or datetime.now(UTC)
        return (end_time - self.start_time).total_seconds()
