"""
Docker Workflow Management for FastMCP 2.12+

This module provides tools for managing Docker workflows including:
- Multi-container application orchestration
- Service dependency management
- Health checks and monitoring
- Automated deployment workflows
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal, Callable, Awaitable

import docker
from docker.errors import (
    DockerException, APIError, NotFound, 
    ImageNotFound, ContainerError, InvalidArgument
)
from fastmcp.tools.tool import Tool
from pydantic import BaseModel, Field, validator, HttpUrl, AnyUrl, ByteSize

from dockermcp.logging_config import logger

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
        description="List of service names this service depends on"
    )
    healthcheck: Optional[Dict[str, Any]] = Field(
        None,
        description="Health check configuration"
    )
    restart_policy: str = Field(
        "no",
        description="Restart policy (no, on-failure, always, unless-stopped)"
    )
    deploy: Dict[str, Any] = Field(
        default_factory=dict,
        description="Deployment configuration"
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

class WorkflowManager:
    """Manages Docker workflows."""
    
    def __init__(self):
        self.client = docker.from_env()
        self.workflows: Dict[str, WorkflowState] = {}
    
    async def create_workflow(
        self,
        workflow_def: Union[Dict[str, Any], WorkflowDefinition],
        workflow_id: Optional[str] = None
    ) -> WorkflowState:
        """Create a new workflow.
        
        Args:
            workflow_def: Workflow definition
            workflow_id: Optional workflow ID (generated if not provided)
            
        Returns:
            Workflow state
        """
        if isinstance(workflow_def, dict):
            workflow_def = WorkflowDefinition(**workflow_def)
        
        workflow_id = workflow_id or f"workflow_{int(time.time())}"
        
        workflow = WorkflowState(
            workflow_id=workflow_id,
            name=workflow_def.name,
            status=WorkflowStatus.PENDING
        )
        
        self.workflows[workflow_id] = workflow
        return workflow
    
    async def start_workflow(
        self,
        workflow_id: str,
        timeout: int = 300
    ) -> WorkflowState:
        """Start a workflow.
        
        Args:
            workflow_id: ID of the workflow to start
            timeout: Timeout in seconds
            
        Returns:
            Updated workflow state
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING
        workflow.start_time = datetime.utcnow()
        workflow.error = None
        
        try:
            # Here you would implement the actual workflow execution
            # This is a simplified example
            await asyncio.sleep(1)  # Simulate work
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.end_time = datetime.utcnow()
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)
            workflow.end_time = datetime.utcnow()
            logger.error(f"Workflow {workflow_id} failed: {str(e)}", exc_info=True)
        
        return workflow
    
    async def stop_workflow(
        self,
        workflow_id: str,
        force: bool = False
    ) -> WorkflowState:
        """Stop a running workflow.
        
        Args:
            workflow_id: ID of the workflow to stop
            force: Whether to force stop the workflow
            
        Returns:
            Updated workflow state
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.RUNNING:
            return workflow
        
        try:
            # Here you would implement the actual workflow stopping logic
            # This is a simplified example
            await asyncio.sleep(0.5)  # Simulate work
            
            workflow.status = WorkflowStatus.CANCELLED
            workflow.end_time = datetime.utcnow()
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = f"Failed to stop workflow: {str(e)}"
            workflow.end_time = datetime.utcnow()
            logger.error(f"Failed to stop workflow {workflow_id}: {str(e)}", exc_info=True)
        
        return workflow
    
    async def get_workflow_status(
        self,
        workflow_id: str
    ) -> WorkflowState:
        """Get the status of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow state
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        return self.workflows[workflow_id]

# Global workflow manager instance
workflow_manager = WorkflowManager()

@Tool(
    name="create_workflow",
    description="Create a new workflow",
    parameters={
        'type': 'object',
        'properties': {
            'workflow_definition': {
                'type': 'object',
                'description': 'Workflow definition (see docs for schema)'
            },
            'workflow_id': {
                'type': 'string',
                'default': None,
                'description': 'Optional workflow ID (generated if not provided)'
            }
        },
        'required': ['workflow_definition']
    }
)
async def create_workflow(
    workflow_definition: Dict[str, Any],
    workflow_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new workflow.
    
    This function creates a new workflow with the given definition.
    
    Args:
        workflow_definition: Workflow definition
        workflow_id: Optional workflow ID (generated if not provided)
        
    Returns:
        Dictionary with workflow information
        
    Example:
        >>> await create_workflow({
        ...     "name": "web-app",
        ...     "version": "1.0",
        ...     "services": {
        ...         "web": {
        ...             "image": "nginx:latest",
        ...             "ports": {"80": "8080"},
        ...             "environment": {"DEBUG": "true"}
        ...         },
        ...         "db": {
        ...             "image": "postgres:13",
        ...             "environment": {
        ...                 "POSTGRES_PASSWORD": "example"
        ...             },
        ...             "volumes": {"db_data": "/var/lib/postgresql/data"}
        ...         }
        ...     },
        ...     "volumes": {
        ...         "db_data": {}
        ...     }
        ... })
        {
            "status": "success",
            "workflow_id": "workflow_1234567890",
            "message": "Workflow created successfully"
        }
    """
    try:
        workflow = await workflow_manager.create_workflow(
            workflow_definition,
            workflow_id
        )
        
        return {
            'status': 'success',
            'workflow_id': workflow.workflow_id,
            'message': 'Workflow created successfully'
        }
        
    except Exception as e:
        error_msg = f"Failed to create workflow: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }

@Tool(
    name="start_workflow",
    description="Start a workflow",
    parameters={
        'type': 'object',
        'properties': {
            'workflow_id': {
                'type': 'string',
                'description': 'ID of the workflow to start'
            },
            'timeout': {
                'type': 'integer',
                'default': 300,
                'description': 'Timeout in seconds'
            }
        },
        'required': ['workflow_id']
    }
)
async def start_workflow(
    workflow_id: str,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Start a workflow.
    
    This function starts a workflow with the given ID.
    
    Args:
        workflow_id: ID of the workflow to start
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with workflow status
        
    Example:
        >>> await start_workflow("workflow_1234567890")
        {
            "status": "success",
            "workflow_id": "workflow_1234567890",
            "workflow_status": "running",
            "message": "Workflow started successfully"
        }
    """
    try:
        workflow = await workflow_manager.start_workflow(workflow_id, timeout)
        
        return {
            'status': 'success',
            'workflow_id': workflow.workflow_id,
            'workflow_status': workflow.status.value,
            'message': 'Workflow started successfully'
        }
        
    except Exception as e:
        error_msg = f"Failed to start workflow: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'workflow_id': workflow_id
        }

@Tool(
    name="stop_workflow",
    description="Stop a running workflow",
    parameters={
        'type': 'object',
        'properties': {
            'workflow_id': {
                'type': 'string',
                'description': 'ID of the workflow to stop'
            },
            'force': {
                'type': 'boolean',
                'default': False,
                'description': 'Whether to force stop the workflow'
            }
        },
        'required': ['workflow_id']
    }
)
async def stop_workflow(
    workflow_id: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Stop a running workflow.
    
    This function stops a running workflow with the given ID.
    
    Args:
        workflow_id: ID of the workflow to stop
        force: Whether to force stop the workflow
        
    Returns:
        Dictionary with workflow status
        
    Example:
        >>> await stop_workflow("workflow_1234567890")
        {
            "status": "success",
            "workflow_id": "workflow_1234567890",
            "workflow_status": "cancelled",
            "message": "Workflow stopped successfully"
        }
    """
    try:
        workflow = await workflow_manager.stop_workflow(workflow_id, force)
        
        return {
            'status': 'success',
            'workflow_id': workflow.workflow_id,
            'workflow_status': workflow.status.value,
            'message': 'Workflow stopped successfully'
        }
        
    except Exception as e:
        error_msg = f"Failed to stop workflow: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'workflow_id': workflow_id
        }

@Tool(
    name="get_workflow_status",
    description="Get the status of a workflow",
    parameters={
        'type': 'object',
        'properties': {
            'workflow_id': {
                'type': 'string',
                'description': 'ID of the workflow'
            }
        },
        'required': ['workflow_id']
    }
)
async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """
    Get the status of a workflow.
    
    This function retrieves the current status of a workflow.
    
    Args:
        workflow_id: ID of the workflow
        
    Returns:
        Dictionary with workflow status and details
        
    Example:
        >>> await get_workflow_status("workflow_1234567890")
        {
            "status": "success",
            "workflow_id": "workflow_1234567890",
            "workflow_status": "running",
            "start_time": "2023-01-01T12:00:00Z",
            "services": {
                "web": {
                    "status": "running",
                    "health": "healthy"
                },
                "db": {
                    "status": "running",
                    "health": "healthy"
                }
            }
        }
    """
    try:
        workflow = await workflow_manager.get_workflow_status(workflow_id)
        
        return {
            'status': 'success',
            'workflow_id': workflow.workflow_id,
            'workflow_status': workflow.status.value,
            'start_time': workflow.start_time.isoformat() if workflow.start_time else None,
            'end_time': workflow.end_time.isoformat() if workflow.end_time else None,
            'services': workflow.services,
            'error': workflow.error
        }
        
    except Exception as e:
        error_msg = f"Failed to get workflow status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg,
            'workflow_id': workflow_id
        }

@Tool(
    name="list_workflows",
    description="List all workflows",
    parameters={
        'type': 'object',
        'properties': {
            'status': {
                'type': 'string',
                'enum': ['all', 'running', 'completed', 'failed', 'cancelled'],
                'default': 'all',
                'description': 'Filter workflows by status'
            },
            'limit': {
                'type': 'integer',
                'default': 50,
                'description': 'Maximum number of workflows to return'
            },
            'offset': {
                'type': 'integer',
                'default': 0,
                'description': 'Number of workflows to skip'
            }
        }
    }
)
async def list_workflows(
    status: str = 'all',
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List all workflows.
    
    This function lists all workflows, optionally filtered by status.
    
    Args:
        status: Filter workflows by status
        limit: Maximum number of workflows to return
        offset: Number of workflows to skip
        
    Returns:
        Dictionary with list of workflows and metadata
        
    Example:
        >>> await list_workflows(status="running")
        {
            "status": "success",
            "workflows": [
                {
                    "workflow_id": "workflow_1234567890",
                    "name": "web-app",
                    "status": "running",
                    "start_time": "2023-01-01T12:00:00Z",
                    "services": ["web", "db"]
                }
            ],
            "total": 1,
            "offset": 0,
            "limit": 50
        }
    """
    try:
        # Filter workflows by status
        filtered_workflows = []
        for workflow in workflow_manager.workflows.values():
            if status == 'all' or workflow.status.value == status:
                filtered_workflows.append({
                    'workflow_id': workflow.workflow_id,
                    'name': workflow.name,
                    'status': workflow.status.value,
                    'start_time': workflow.start_time.isoformat() if workflow.start_time else None,
                    'end_time': workflow.end_time.isoformat() if workflow.end_time else None,
                    'services': list(workflow.services.keys()) if workflow.services else []
                })
        
        # Apply pagination
        total = len(filtered_workflows)
        paginated_workflows = filtered_workflows[offset:offset + limit]
        
        return {
            'status': 'success',
            'workflows': paginated_workflows,
            'total': total,
            'offset': offset,
            'limit': limit
        }
        
    except Exception as e:
        error_msg = f"Failed to list workflows: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'status': 'error',
            'error': error_msg
        }
