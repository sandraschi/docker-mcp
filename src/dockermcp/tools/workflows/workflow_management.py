"""
Docker Workflow Management for FastMCP 2.12+

This module provides tools for managing Docker workflows including:
- Multi-container application orchestration
- Service dependency management
- Health checks and monitoring
- Automated deployment workflows
"""
from __future__ import annotations

import time
from datetime import datetime

import docker
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

from dockermcp.logging_config import logger

# Initialize FastMCP instance
mcp = FastMCP("Workflow Management Tools")

# Import models from models.py to avoid circular imports
from .models import (  # noqa: E402
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    ListWorkflowsRequest,
    ListWorkflowsResponse,
    StartWorkflowRequest,
    StartWorkflowResponse,
    StopWorkflowRequest,
    StopWorkflowResponse,
    WorkflowDefinition,
    WorkflowState,
    WorkflowStatus,
    WorkflowStatusResponse,
    WorkflowSummary,
)


class WorkflowManager:
    """Manages Docker workflows."""

    def __init__(self, docker_client: docker.DockerClient | None = None):
        """Initialize the WorkflowManager."""
        try:
            if docker_client:
                self.client = docker_client
            else:
                from ....dockermcp import docker_available
                from ....dockermcp import docker_client as global_client
                if docker_available:
                    self.client = global_client
                else:
                    self.client = docker.from_env()
        except Exception:
            self.client = None

        self.workflows: dict[str, WorkflowState] = {}

    def create_workflow(
        self,
        workflow_definition: WorkflowDefinition,
        workflow_id: str | None = None
    ) -> WorkflowState:
        """Create a new workflow.

        Args:
            workflow_definition: WorkflowDefinition containing workflow definition
            workflow_id: Optional workflow ID

        Returns:
            WorkflowState: The created workflow state

        Raises:
            ToolError: If workflow creation fails
        """
        try:
            # Generate a workflow ID if not provided
            if not workflow_id:
                workflow_id = f"workflow_{int(time.time())}"

            # Create workflow state
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                name=workflow_definition.name,
                status=WorkflowStatus.PENDING,
                created_at=datetime.utcnow()
            )

            # Store workflow state
            self.workflows[workflow_id] = workflow_state

            logger.info(f"Created workflow {workflow_id} ({workflow_definition.name})")
            return workflow_state

        except Exception as e:
            error_msg = f"Failed to create workflow: {e!s}"
            logger.error(error_msg, exc_info=True)
            raise ToolError(error_msg) from e

    async def start_workflow(
        self,
        workflow_id: str,
        timeout: int
    ) -> WorkflowState:
        """Start a workflow.

        Args:
            workflow_id: ID of the workflow to start
            timeout: Timeout in seconds

        Returns:
            WorkflowState: The updated workflow state

        Raises:
            ToolError: If workflow start fails
        """
        try:
            # Get workflow state
            if workflow_id not in self.workflows:
                raise ValueError(f"Workflow {workflow_id} not found")

            workflow_state = self.workflows[workflow_id]

            # Update workflow state
            workflow_state.status = WorkflowStatus.RUNNING
            workflow_state.start_time = datetime.utcnow()
            workflow_state.end_time = None
            workflow_state.error = None

            logger.info(f"Started workflow {workflow_id} with timeout {timeout}s")
            return workflow_state

        except Exception as e:
            error_msg = f"Failed to start workflow {workflow_id}: {e!s}"
            logger.error(error_msg, exc_info=True)

            # Update workflow state with error
            if workflow_id in self.workflows:
                self.workflows[workflow_id].status = WorkflowStatus.FAILED
                self.workflows[workflow_id].error = str(e)

            raise ToolError(error_msg) from e

    async def stop_workflow(
        self,
        workflow_id: str,
        force: bool
    ) -> WorkflowState:
        """Stop a running workflow.

        Args:
            workflow_id: ID of the workflow to stop
            force: Force flag

        Returns:
            WorkflowState: The updated workflow state

        Raises:
            ToolError: If workflow stop fails
        """
        try:
            # Get workflow state
            if workflow_id not in self.workflows:
                raise ValueError(f"Workflow {workflow_id} not found")

            workflow_state = self.workflows[workflow_id]

            # Update workflow state
            workflow_state.status = WorkflowStatus.CANCELLED if force else WorkflowStatus.COMPLETED
            workflow_state.end_time = datetime.utcnow()

            logger.info(f"Stopped workflow {workflow_id} (force={force})")
            return workflow_state

        except Exception as e:
            error_msg = f"Failed to stop workflow {workflow_id}: {e!s}"
            logger.error(error_msg, exc_info=True)
            raise ToolError(error_msg) from e

    def get_workflow(
        self,
        workflow_id: str
    ) -> WorkflowState:
        """Get the status of a workflow.

        Args:
            workflow_id: ID of the workflow

        Returns:
            WorkflowState: The current workflow state

        Raises:
            ToolError: If workflow status retrieval fails
        """
        try:
            if workflow_id not in self.workflows:
                raise ValueError(f"Workflow {workflow_id} not found")

            return self.workflows[workflow_id]

        except Exception as e:
            error_msg = f"Failed to get status for workflow {workflow_id}: {e!s}"
            logger.error(error_msg, exc_info=True)
            raise ToolError(error_msg) from e

# Global workflow manager instance
workflow_manager = WorkflowManager()

# Parameter models for workflow tools
class CreateWorkflowParams(CreateWorkflowRequest):
    """Parameters for creating a workflow."""
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

@mcp.tool
async def create_workflow(params: CreateWorkflowParams) -> CreateWorkflowResponse:
    """
    Create a new workflow with the given definition.

    This function creates a new workflow that can manage multiple Docker containers
    as a cohesive application. The workflow definition includes services, networks,
    volumes, and environment variables.

    Args:
        params: CreateWorkflowRequest containing workflow definition and optional ID

    Returns:
        CreateWorkflowResponse with workflow ID and status

    Example:
        >>> await create_workflow(CreateWorkflowRequest(
        ...     workflow_definition=WorkflowDefinition(
        ...         name="web-app",
        ...         services={
        ...             "web": ServiceDefinition(
        ...                 name="web",
        ...                 image="nginx:latest",
        ...                 ports={"80": "8080"},
        ...                 environment={"DEBUG": "true"}
        ...             ),
        ...             "db": ServiceDefinition(
        ...                 name="db",
        ...                 image="postgres:13",
        ...                 environment={"POSTGRES_PASSWORD": "example"},
        ...                 volumes={"db_data": "/var/lib/postgresql/data"}
        ...             )
        ...         },
        ...         volumes={"db_data": {}}
        ...     )
        ... ))
        {
            "workflow_id": "workflow_1234567890",
            "name": "web-app",
            "status": "pending",
            "created_at": "2023-01-01T12:00:00Z",
            "message": "Workflow created successfully"
        }
    """
    try:
        # Create the workflow
        workflow_id = workflow_manager.create_workflow(
            workflow_definition=params.workflow_definition,
            workflow_id=params.workflow_id
        )

        # Return success response
        return CreateWorkflowResponse(
            workflow_id=workflow_id.workflow_id,
            name=workflow_id.name,
            status=workflow_id.status,
            created_at=workflow_id.created_at,
            message="Workflow created successfully"
        )

    except Exception as e:
        error_msg = f"Failed to create workflow: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

class StartWorkflowParams(StartWorkflowRequest):
    """Parameters for starting a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "timeout": 300
            }
        }
    )

@mcp.tool
async def start_workflow(params: StartWorkflowParams) -> StartWorkflowResponse:
    """
    Start a workflow with the given ID.

    This function initiates the execution of a workflow, starting all associated
    services in the correct order based on their dependencies.

    Args:
        params: StartWorkflowRequest containing workflow ID and timeout

    Returns:
        StartWorkflowResponse with workflow status and start time

    Example:
        >>> await start_workflow(StartWorkflowRequest(
        ...     workflow_id="workflow_1234567890",
        ...     timeout=300
        ... ))
        {
            "workflow_id": "workflow_1234567890",
            "status": "running",
            "start_time": "2023-01-01T12:00:00Z",
            "message": "Workflow started successfully"
        }
    """
    try:
        # Start the workflow
        workflow_state = await workflow_manager.start_workflow(
            workflow_id=params.workflow_id,
            timeout=params.timeout
        )

        # Return success response
        return StartWorkflowResponse(
            workflow_id=workflow_state.workflow_id,
            status=workflow_state.status,
            start_time=workflow_state.start_time or datetime.utcnow(),
            message="Workflow started successfully"
        )
    except Exception as e:
        error_msg = f"Failed to start workflow: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

class StopWorkflowParams(StopWorkflowRequest):
    """Parameters for stopping a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "force": False
            }
        }
    )

@mcp.tool
async def stop_workflow(
    params: StopWorkflowParams
) -> StopWorkflowResponse:
    """
    Stop a running workflow.

    This function stops a workflow with the given ID, optionally forcing it to stop.

    Args:
        params: StopWorkflowRequest containing workflow ID and force flag

    Returns:
        StopWorkflowResponse with workflow status and stop time

    Example:
        >>> await stop_workflow(StopWorkflowRequest(
        ...     workflow_id="workflow_1234567890",
        ...     force=True
        ... ))
        {
            "workflow_id": "workflow_1234567890",
            "status": "cancelled",
            "end_time": "2023-01-01T12:05:00Z",
            "message": "Workflow stopped successfully"
        }
    """
    try:
        # Stop the workflow
        workflow_state = await workflow_manager.stop_workflow(
            workflow_id=params.workflow_id,
            force=params.force
        )

        # Return success response
        return StopWorkflowResponse(
            workflow_id=workflow_state.workflow_id,
            status=workflow_state.status,
            end_time=workflow_state.end_time or datetime.utcnow(),
            message="Workflow stopped successfully"
        )

    except Exception as e:
        error_msg = f"Failed to stop workflow: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

class GetWorkflowStatusParams(BaseModel):
    """Parameters for getting workflow status.

    Attributes:
        workflow_id: The unique identifier of the workflow to get status for.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123"
            },
            "title": "GetWorkflowStatusParams",
            "description": "Parameters for retrieving the status of a workflow"
        }
    )

    workflow_id: str = Field(
        ...,
        description="Unique identifier of the workflow",
        min_length=1,
        pattern=r"^[a-zA-Z0-9_-]+$",
        json_schema_extra={
            "examples": ["workflow_123", "my-workflow-1"],
            "description": "ID of the workflow to get status for"
        }
    )

@mcp.tool
async def get_workflow_status(params: GetWorkflowStatusParams) -> WorkflowStatusResponse:
    """
    Get the status of a workflow.

    This function retrieves the current status of a workflow, including the status
    of all its services and any error information.

    Args:
        params: GetWorkflowStatusParams containing workflow ID

    Returns:
        WorkflowStatusResponse with detailed status information

    Example:
        >>> await get_workflow_status("workflow_1234567890")
        {
            "workflow_id": "workflow_1234567890",
            "name": "web-app",
            "status": "running",
            "start_time": "2023-01-01T12:00:00Z",
            "end_time": null,
            "services": {
                "web": {
                    "status": "running",
                    "health": "healthy"
                },
                "db": {
                    "status": "running",
                    "health": "healthy"
                }
            },
            "error": null
        }
    """
    try:
        # Get the workflow status
        workflow = workflow_manager.get_workflow(params.workflow_id)

        # Convert to response model
        return WorkflowStatusResponse(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            status=workflow.status,
            start_time=workflow.start_time,
            end_time=workflow.end_time,
            services=workflow.services,
            error=workflow.error
        )

    except Exception as e:
        error_msg = f"Failed to get status for workflow {params.workflow_id}: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e

class ListWorkflowsParams(ListWorkflowsRequest):
    """Parameters for listing workflows."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "running",
                "limit": 10,
                "offset": 0
            }
        }
    )

@mcp.tool
async def list_workflows(
    params: ListWorkflowsParams
) -> ListWorkflowsResponse:
    """
    List all workflows with optional filtering and pagination.

    This function retrieves a paginated list of workflows, optionally filtered by status.
    The response includes metadata about the total number of workflows and pagination details.

    Args:
        params: ListWorkflowsRequest containing filter and pagination parameters

    Returns:
        ListWorkflowsResponse with list of workflows and metadata

    Example:
        >>> await list_workflows(ListWorkflowsRequest(
        ...     status="running",
        ...     limit=10,
        ...     offset=0
        ... ))
        {
            "workflows": [
                {
                    "workflow_id": "workflow_1234567890",
                    "name": "web-app",
                    "status": "running",
                    "created_at": "2023-01-01T12:00:00Z",
                    "start_time": "2023-01-01T12:00:00Z",
                    "end_time": null,
                    "service_count": 2
                }
            ],
            "total": 1,
            "limit": 10,
            "offset": 0,
            "status_filter": "running",
            "message": "Found 1 workflow(s)"
        }
    """
    try:
        # Filter workflows by status
        filtered_workflows = []
        for workflow in workflow_manager.workflows.values():
            if params.status == 'all' or workflow.status.value == params.status:
                filtered_workflows.append(WorkflowSummary(
                    workflow_id=workflow.workflow_id,
                    name=workflow.name,
                    status=workflow.status,
                    created_at=workflow.created_at,
                    start_time=workflow.start_time,
                    end_time=workflow.end_time,
                    service_count=len(workflow.services) if workflow.services else 0
                ))

        # Apply pagination
        total = len(filtered_workflows)
        paginated_workflows = filtered_workflows[params.offset:params.offset + params.limit]

        # Return paginated results
        return ListWorkflowsResponse(
            workflows=paginated_workflows,
            total=total,
            limit=params.limit,
            offset=params.offset,
            status_filter=params.status.lower(),
            message=f"Found {total} workflow(s)"
        )

    except Exception as e:
        error_msg = f"Failed to list workflows: {e!s}"
        logger.error(error_msg, exc_info=True)
        raise ToolError(error_msg) from e
