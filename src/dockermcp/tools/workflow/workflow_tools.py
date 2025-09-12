"""
Workflow management tools for Docker MCP.

This module provides FastMCP 2.11.3 compatible tools for managing Docker workflows.
"""
from dockermcp.logging_config import logger, configure_logging
configure_logging()

import asyncio
import uuid
from typing import Dict, Any, List, Optional

# FastMCP 2.12+ import pattern
from fastmcp.tools import tool
from fastmcp.exceptions import ToolException

# Set tool availability flag
TOOL_AVAILABLE = True
logger.debug("FastMCP Tool imported from fastmcp.tools")
from dockermcp.core.workflow import WorkflowManager
from dockermcp.tools.workflow.workflow_models import (
    WorkflowStatus, WorkflowStep, WorkflowDefinition, WorkflowInstance,
    WorkflowExecution, WorkflowResponse, CreateWorkflowRequest,
    ExecuteWorkflowRequest, WorkflowStatusResponse, WorkflowListResponse
)

# Initialize workflow manager
workflow_mgr = WorkflowManager()

@tool(
    name="create_workflow",
    description="Create a new workflow definition"
)
async def create_workflow(
    request: CreateWorkflowRequest
) -> Dict[str, Any]:
    """Create a new workflow definition."""
    try:
        workflow_id = str(uuid.uuid4())
        workflow = WorkflowDefinition(
            id=workflow_id,
            name=request.name,
            description=request.description,
            steps=request.steps,
            env=request.env,
            timeout=request.timeout,
            max_retries=request.max_retries
        )
        
        await workflow_mgr.save_workflow(workflow)
        
        return WorkflowResponse(
            success=True,
            message=f"Workflow '{request.name}' created successfully",
            workflow_id=workflow_id
        ).dict()
    except Exception as e:
        return WorkflowResponse(
            success=False,
            message=f"Failed to create workflow: {str(e)}",
            error=str(e)
        ).dict()

@tool(
    name="execute_workflow",
    description="Execute a workflow with the given parameters",
    output_schema=WorkflowResponse
)
async def execute_workflow(
    request: ExecuteWorkflowRequest
) -> Dict[str, Any]:
    """Execute a workflow with the given parameters."""
    try:
        instance_id = str(uuid.uuid4())
        workflow = await workflow_mgr.get_workflow(request.workflow_id)
        
        if not workflow:
            return WorkflowResponse(
                success=False,
                message=f"Workflow '{request.workflow_id}' not found",
                error="Workflow not found"
            ).dict()
        
        instance = WorkflowInstance(
            id=instance_id,
            workflow_id=workflow.id,
            status=WorkflowStatus.PENDING,
            parameters=request.parameters or {}
        )
        
        if request.async_exec:
            # Start workflow execution in background
            asyncio.create_task(_execute_workflow(workflow, instance, request))
            
            return WorkflowResponse(
                success=True,
                message=f"Workflow execution started with ID: {instance_id}",
                workflow_id=workflow.id,
                instance_id=instance_id,
                status=WorkflowStatus.RUNNING
            ).dict()
        else:
            # Execute workflow synchronously
            result = await _execute_workflow(workflow, instance, request)
            return result
            
    except Exception as e:
        return WorkflowResponse(
            success=False,
            message=f"Failed to execute workflow: {str(e)}",
            error=str(e)
        ).dict()

async def _execute_workflow(
    workflow: WorkflowDefinition,
    instance: WorkflowInstance,
    request: ExecuteWorkflowRequest
) -> Dict[str, Any]:
    """Internal function to execute a workflow."""
    try:
        # Save the instance before starting
        instance.status = WorkflowStatus.RUNNING
        instance.started_at = instance.started_at or datetime.utcnow()
        await workflow_mgr.save_instance(instance)
        
        # Execute each step in order, respecting dependencies
        executions = []
        completed_steps = set()
        
        while len(completed_steps) < len(workflow.steps):
            # Find steps that can be executed (all dependencies met)
            for step in workflow.steps:
                if step.id in completed_steps:
                    continue
                    
                # Check if all dependencies are met
                deps_met = all(dep in completed_steps 
                             for dep in (step.depends_on or []))
                
                if deps_met:
                    # Execute the step
                    execution = await _execute_step(workflow, instance, step)
                    executions.append(execution)
                    
                    if execution.status == WorkflowStatus.COMPLETED:
                        completed_steps.add(step.id)
                    else:
                        # Handle step failure based on retry policy
                        if execution.retry_count < workflow.max_retries:
                            # Retry the step
                            execution.retry_count += 1
                            execution = await _execute_step(workflow, instance, step, execution.retry_count)
                            executions.append(execution)
                            
                            if execution.status == WorkflowStatus.COMPLETED:
                                completed_steps.add(step.id)
                            else:
                                # Max retries reached, fail the workflow
                                instance.status = WorkflowStatus.FAILED
                                instance.completed_at = datetime.utcnow()
                                instance.error = f"Step '{step.id}' failed after {workflow.max_retries} retries"
                                await workflow_mgr.save_instance(instance)
                                
                                return WorkflowResponse(
                                    success=False,
                                    message="Workflow execution failed",
                                    workflow_id=workflow.id,
                                    instance_id=instance.id,
                                    status=WorkflowStatus.FAILED,
                                    error=instance.error
                                ).dict()
                        else:
                            # No retries left, fail the workflow
                            instance.status = WorkflowStatus.FAILED
                            instance.completed_at = datetime.utcnow()
                            instance.error = f"Step '{step.id}' failed with no retries left"
                            await workflow_mgr.save_instance(instance)
                            
                            return WorkflowResponse(
                                success=False,
                                message="Workflow execution failed",
                                workflow_id=workflow.id,
                                instance_id=instance.id,
                                status=WorkflowStatus.FAILED,
                                error=instance.error
                            ).dict()
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.1)
        
        # All steps completed successfully
        instance.status = WorkflowStatus.COMPLETED
        instance.completed_at = datetime.utcnow()
        await workflow_mgr.save_instance(instance)
        
        return WorkflowResponse(
            success=True,
            message="Workflow execution completed successfully",
            workflow_id=workflow.id,
            instance_id=instance.id,
            status=WorkflowStatus.COMPLETED
        ).dict()
        
    except Exception as e:
        instance.status = WorkflowStatus.FAILED
        instance.completed_at = datetime.utcnow()
        instance.error = str(e)
        await workflow_mgr.save_instance(instance)
        
        return WorkflowResponse(
            success=False,
            message="Workflow execution failed",
            workflow_id=workflow.id,
            instance_id=instance.id,
            status=WorkflowStatus.FAILED,
            error=str(e)
        ).dict()

async def _execute_step(
    workflow: WorkflowDefinition,
    instance: WorkflowInstance,
    step: WorkflowStep,
    retry_count: int = 0
) -> WorkflowExecution:
    """Execute a single workflow step."""
    execution = WorkflowExecution(
        step_id=step.id,
        status=WorkflowStatus.RUNNING,
        start_time=datetime.utcnow(),
        retry_count=retry_count
    )
    
    try:
        # TODO: Implement actual step execution logic
        # This would involve calling the appropriate tool or function
        # based on the step.command and step.args
        
        # For now, simulate a successful execution
        await asyncio.sleep(1)  # Simulate work
        
        execution.status = WorkflowStatus.COMPLETED
        execution.end_time = datetime.utcnow()
        execution.duration = (execution.end_time - execution.start_time).total_seconds()
        execution.output = {"message": f"Step '{step.id}' completed successfully"}
        
    except Exception as e:
        execution.status = WorkflowStatus.FAILED
        execution.end_time = datetime.utcnow()
        execution.duration = (execution.end_time - execution.start_time).total_seconds()
        execution.error = str(e)
    
    return execution

@tool(
    name="get_workflow_status",
    description="Get the status of a workflow instance",
    output_schema=WorkflowStatusResponse
)
async def get_workflow_status(
    instance_id: str
) -> Dict[str, Any]:
    """Get the status of a workflow instance."""
    try:
        instance = await workflow_mgr.get_instance(instance_id)
        if not instance:
            return WorkflowResponse(
                success=False,
                message=f"Workflow instance '{instance_id}' not found",
                error="Instance not found"
            ).dict()
        
        # Get execution history for this instance
        executions = await workflow_mgr.get_executions(instance_id)
        
        # Calculate progress
        workflow = await workflow_mgr.get_workflow(instance.workflow_id)
        total_steps = len(workflow.steps) if workflow else 0
        completed_steps = len([e for e in executions 
                             if e.status == WorkflowStatus.COMPLETED])
        progress = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Get current step
        current_step = None
        if instance.status == WorkflowStatus.RUNNING:
            running_exec = next((e for e in executions 
                               if e.status == WorkflowStatus.RUNNING), None)
            if running_exec:
                current_step = running_exec.step_id
        
        return WorkflowStatusResponse(
            success=True,
            message="Workflow status retrieved",
            workflow_id=instance.workflow_id,
            instance_id=instance.id,
            status=instance.status,
            executions=[e.dict() for e in executions],
            progress=progress,
            current_step=current_step
        ).dict()
        
    except Exception as e:
        return WorkflowResponse(
            success=False,
            message=f"Failed to get workflow status: {str(e)}",
            error=str(e)
        ).dict()

@tool(
    name="list_workflows",
    description="List all available workflows",
    output_schema=WorkflowListResponse
)
async def list_workflows() -> Dict[str, Any]:
    """List all available workflows."""
    try:
        workflows = await workflow_mgr.list_workflows()
        
        return WorkflowListResponse(
            success=True,
            message=f"Found {len(workflows)} workflows",
            workflows=[w.dict() for w in workflows],
            total=len(workflows)
        ).dict()
        
    except Exception as e:
        return WorkflowResponse(
            success=False,
            message=f"Failed to list workflows: {str(e)}",
            error=str(e)
        ).dict()

@tool(
    name="cancel_workflow",
    description="Cancel a running workflow instance",
    output_schema=WorkflowResponse
)
async def cancel_workflow(
    instance_id: str
) -> Dict[str, Any]:
    """Cancel a running workflow instance."""
    try:
        instance = await workflow_mgr.get_instance(instance_id)
        if not instance:
            return WorkflowResponse(
                success=False,
                message=f"Workflow instance '{instance_id}' not found",
                error="Instance not found"
            ).dict()
        
        if instance.status != WorkflowStatus.RUNNING:
            return WorkflowResponse(
                success=False,
                message=f"Cannot cancel workflow in '{instance.status}' state",
                workflow_id=instance.workflow_id,
                instance_id=instance.id,
                status=instance.status
            ).dict()
        
        # TODO: Implement actual cancellation logic
        # This would involve stopping any running tasks for this instance
        
        instance.status = WorkflowStatus.CANCELLED
        instance.completed_at = datetime.utcnow()
        await workflow_mgr.save_instance(instance)
        
        return WorkflowResponse(
            success=True,
            message="Workflow cancelled successfully",
            workflow_id=instance.workflow_id,
            instance_id=instance.id,
            status=WorkflowStatus.CANCELLED
        ).dict()
        
    except Exception as e:
        return WorkflowResponse(
            success=False,
            message=f"Failed to cancel workflow: {str(e)}",
            error=str(e)
        ).dict()
