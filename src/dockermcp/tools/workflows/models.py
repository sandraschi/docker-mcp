"""
Workflow management models for Docker MCP.

This module contains Pydantic models for workflow management operations.
"""
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, AnyUrl, field_validator

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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "web",
                "image": "nginx:latest",
                "ports": {"80": "8080"},
                "environment": {"DEBUG": "true"}
            }
        }
    )
    
    name: str = Field(..., json_schema={"description": "Name of the service"})
    image: str = Field(..., json_schema={"description": "Docker image to use"})
    command: Optional[Union[str, List[str]]] = Field(
        default=None,
        json_schema={"description": "Command to run in the container"}
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        json_schema={"description": "Environment variables"}
    )
    ports: Dict[str, str] = Field(
        default_factory=dict,
        json_schema={"description": "Port mappings (host:container)"}
    )
    volumes: Dict[str, str] = Field(
        default_factory=dict,
        json_schema={"description": "Volume mappings (host:container)"}
    )
    depends_on: List[str] = Field(
        default_factory=list,
        json_schema={"description": "Services this service depends on"}
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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "web-app",
                "version": "1.0",
                "services": {
                    "web": {
                        "name": "web",
                        "image": "nginx:latest",
                        "ports": {"80": "8080"}
                    }
                }
            }
        }
    )
    
    name: str = Field(..., json_schema={"description": "Name of the workflow"})
    version: str = Field("1.0", json_schema={"description": "Workflow version"})
    services: Dict[str, ServiceDefinition] = Field(
        ...,
        json_schema={"description": "Services in the workflow"}
    )
    networks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        json_schema={"description": "Networks to create"}
    )
    volumes: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        json_schema={"description": "Volumes to create"}
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        json_schema={"description": "Global environment variables"}
    )

class WorkflowState(BaseModel):
    """Runtime state of a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "name": "web-app",
                "status": "running",
                "created_at": "2023-01-01T12:00:00Z"
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "Unique ID of the workflow"})
    name: str = Field(..., json_schema={"description": "Name of the workflow"})
    status: WorkflowStatus = Field(
        default=WorkflowStatus.PENDING,
        json_schema={"description": "Current status of the workflow"}
    )
    start_time: Optional[datetime] = Field(
        default=None,
        json_schema={"description": "When the workflow started"}
    )
    end_time: Optional[datetime] = Field(
        default=None,
        json_schema={"description": "When the workflow ended"}
    )
    services: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        json_schema={"description": "State of each service"}
    )
    error: Optional[str] = Field(
        default=None,
        json_schema={"description": "Error message if the workflow failed"}
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        json_schema={"description": "When the workflow was created"}
    )

# Request and Response Models for API Endpoints
class CreateWorkflowRequest(BaseModel):
    """Request model for creating a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_definition": {
                    "name": "web-app",
                    "services": {"web": {"image": "nginx:latest"}}
                }
            }
        }
    )
    
    workflow_definition: WorkflowDefinition = Field(
        ...,
        json_schema={"description": "Workflow definition"}
    )
    workflow_id: Optional[str] = Field(
        default=None,
        json_schema={"description": "Optional workflow ID (generated if not provided)"}
    )

class CreateWorkflowResponse(BaseModel):
    """Response model for creating a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "name": "web-app",
                "status": "pending",
                "created_at": "2023-01-01T12:00:00Z",
                "message": "Workflow created successfully"
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "ID of the created workflow"})
    name: str = Field(..., json_schema={"description": "Name of the workflow"})
    status: WorkflowStatus = Field(..., json_schema={"description": "Initial status of the workflow"})
    created_at: datetime = Field(..., json_schema={"description": "When the workflow was created"})
    message: str = Field(..., json_schema={"description": "Status message"})

class StartWorkflowRequest(BaseModel):
    """Request model for starting a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "timeout": 300
            }
        }
    )
    
    workflow_id: str = Field(
        ...,
        description="ID of the workflow to start",
        json_schema_extra={"example": "workflow_123"}
    )
    timeout: int = Field(
        default=300,
        description="Timeout in seconds",
        json_schema_extra={
            "description": "Timeout in seconds",
            "minimum": 1,
            "maximum": 3600
        }
    )

class StartWorkflowResponse(BaseModel):
    """Response model for starting a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "status": "running",
                "start_time": "2023-01-01T12:00:00Z",
                "message": "Workflow started successfully"
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "ID of the workflow"})
    status: WorkflowStatus = Field(..., json_schema={"description": "Current status of the workflow"})
    start_time: datetime = Field(..., json_schema={"description": "When the workflow started"})
    message: str = Field(..., json_schema={"description": "Status message"})

class StopWorkflowRequest(BaseModel):
    """Request model for stopping a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "force": False
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "ID of the workflow to stop"})
    force: bool = Field(
        default=False,
        json_schema={"description": "Whether to force stop the workflow"}
    )

class StopWorkflowResponse(BaseModel):
    """Response model for stopping a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "status": "stopped",
                "end_time": "2023-01-01T12:05:00Z",
                "message": "Workflow stopped successfully"
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "ID of the workflow"})
    status: WorkflowStatus = Field(..., json_schema={"description": "Current status of the workflow"})
    end_time: datetime = Field(..., json_schema={"description": "When the workflow was stopped"})
    message: str = Field(..., json_schema={"description": "Status message"})

class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "name": "web-app",
                "status": "running",
                "services": {"web": {"status": "running"}},
                "start_time": "2023-01-01T12:00:00Z"
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "ID of the workflow"})
    name: str = Field(..., json_schema={"description": "Name of the workflow"})
    status: WorkflowStatus = Field(..., json_schema={"description": "Current status of the workflow"})
    start_time: Optional[datetime] = Field(default=None, json_schema={"description": "When the workflow started"})
    end_time: Optional[datetime] = Field(default=None, json_schema={"description": "When the workflow ended"})
    services: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        json_schema={"description": "Status of each service in the workflow"}
    )
    error: Optional[str] = Field(default=None, json_schema={"description": "Error message if the workflow failed"})

class ListWorkflowsRequest(BaseModel):
    """Request model for listing workflows."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "running",
                "limit": 10,
                "offset": 0
            }
        }
    )
    
    status: str = Field(
        default="all",
        json_schema={
            "description": "Filter workflows by status (all, running, completed, failed, cancelled)",
            "enum": ["all", "running", "completed", "failed", "cancelled"]
        }
    )
    limit: int = Field(
        default=50,
        json_schema={
            "description": "Maximum number of workflows to return",
            "minimum": 1,
            "maximum": 1000
        }
    )
    offset: int = Field(
        default=0,
        json_schema={
            "description": "Number of workflows to skip",
            "minimum": 0
        }
    )

class WorkflowSummary(BaseModel):
    """Summary of a workflow for listing."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "name": "web-app",
                "status": "running",
                "created_at": "2023-01-01T12:00:00Z",
                "start_time": "2023-01-01T12:00:00Z",
                "service_count": 2
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "ID of the workflow"})
    name: str = Field(..., json_schema={"description": "Name of the workflow"})
    status: WorkflowStatus = Field(..., json_schema={"description": "Current status of the workflow"})
    created_at: datetime = Field(..., json_schema={"description": "When the workflow was created"})
    start_time: Optional[datetime] = Field(default=None, json_schema={"description": "When the workflow started"})
    end_time: Optional[datetime] = Field(default=None, json_schema={"description": "When the workflow ended"})
    service_count: int = Field(..., json_schema={"description": "Number of services in the workflow"})

class ListWorkflowsResponse(BaseModel):
    """Response model for listing workflows."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflows": [{
                    "workflow_id": "workflow_123",
                    "name": "web-app",
                    "status": "running",
                    "created_at": "2023-01-01T12:00:00Z"
                }],
                "total": 1,
                "limit": 10,
                "offset": 0,
                "message": "Found 1 workflow(s)"
            }
        }
    )
    
    workflows: List[WorkflowSummary] = Field(..., json_schema={"description": "List of workflows"})
    total: int = Field(..., json_schema={"description": "Total number of workflows"})
    limit: int = Field(..., json_schema={"description": "Maximum number of workflows per page"})
    offset: int = Field(..., json_schema={"description": "Number of workflows skipped"})
    message: str = Field(..., json_schema={"description": "Status message"})
