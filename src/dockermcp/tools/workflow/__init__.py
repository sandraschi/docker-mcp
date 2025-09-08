"""
Workflow tools for Docker MCP.

This module provides FastMCP 2.12+ compatible tools for workflow automation.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from fastmcp.tools import Tool
from fastmcp.exceptions import ToolError
from workflow_intel.stack_health import StackHealthChecker

# Import models
from .workflow_models import (
    WorkflowStatus,
    WorkflowStep,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowExecution,
    WorkflowResponse,
    CreateWorkflowRequest,
    ExecuteWorkflowRequest,
    WorkflowStatusResponse,
    WorkflowListResponse
)

# Import tools
from .workflow_tools import (
    create_workflow,
    execute_workflow,
    get_workflow_status,
    list_workflows,
    cancel_workflow
)

# Initialize workflow components
stack_health_checker = StackHealthChecker()

class CheckStackHealthResponse(BaseModel):
    """Response model for stack health checks."""
    success: bool
    message: str
    health_status: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@Tool(
    name="check_stack_health",
    description="Check the health of a Docker stack"
)
async def check_stack_health(stack_name: str) -> Dict[str, Any]:
    """
    Check the health of a Docker stack and its services.
    
    Args:
        stack_name: Name of the stack to check
        
    Returns:
        Dictionary with health status information
    """
    try:
        health_status = await stack_health_checker.check_stack(stack_name)
        return {
            "success": True,
            "message": f"Health check completed for stack '{stack_name}'",
            "health_status": health_status
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to check stack health: {str(e)}",
            "error": str(e)
        }

def get_tools() -> List[callable]:
    """
    Get all workflow management tools for registration with FastMCP 2.12+.
    
    Returns:
        List of @tool-decorated functions for all workflow operations
    """
    return [
        create_workflow,
        execute_workflow,
        get_workflow_status,
        list_workflows,
        cancel_workflow,
        check_stack_health
    ]

# Add get_tools to __all__
__all__.append('get_tools')
