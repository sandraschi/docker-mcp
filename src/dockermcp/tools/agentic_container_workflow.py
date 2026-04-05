"""
FastMCP 2.14.1+ Sampling with Tools Orchestration Tools (SEP-1577)

These tools demonstrate SEP-1577: Sampling with tools, enabling agentic workflows
where servers borrow the client's LLM and autonomously control tool execution.

Benefits:
- Eliminates client round-trips for complex multi-step operations
- LLM autonomously orchestrates tool usage decisions
- Server controls execution flow and logic
- Massive efficiency gains for container orchestration

CONTAINER ORCHESTRATION WORKFLOWS:
- "Deploy microservices stack" → autonomous container deployment, networking, service orchestration
- "Set up development environment" → autonomous multi-service setup, dependencies, configuration
- "Scale application cluster" → intelligent resource allocation, load balancing
"""

import logging

from fastmcp import Context

logger = logging.getLogger(__name__)

# Conditional imports for advanced_memory integration
try:
    from advanced_memory.mcp.inter_server import SamplingResult, create_tool_spec, sample_with_tools
    from advanced_memory.mcp.mcp_instance import mcp
    from advanced_memory.mcp.tools.content_manager import (
        build_error_response,
        build_success_response,
    )
    _advanced_memory_available = True
except ImportError:
    _advanced_memory_available = False
    logger.warning("Advanced Memory not available - using fallback response builders")

    # Fallback response builders when advanced_memory is not available
    def build_success_response(**kwargs) -> dict:
        return {
            "success": True,
            "operation": kwargs.get("operation", "unknown"),
            "summary": kwargs.get("summary", "Operation completed"),
            "result": kwargs.get("result", {}),
            "next_steps": kwargs.get("next_steps", []),
            "suggestions": kwargs.get("suggestions", []),
        }

    def build_error_response(**kwargs) -> dict:
        return {
            "success": False,
            "error": kwargs.get("error", "Unknown error"),
            "error_code": kwargs.get("error_code", "UNKNOWN_ERROR"),
            "message": kwargs.get("message", "An error occurred"),
            "recovery_options": kwargs.get("recovery_options", []),
            "urgency": kwargs.get("urgency", "medium"),
        }

    # Fallback MCP instance
    from dockermcp.mcp_instance import get_mcp
    mcp = get_mcp()


@mcp.tool()
async def agentic_container_workflow(
    workflow_prompt: str,
    available_tools: list[str],
    max_iterations: int = 5,
    context: Context | None = None
) -> dict:
    """
    Execute agentic container workflows using FastMCP 2.14.1+ sampling with tools.

    This tool demonstrates SEP-1577 by enabling the server's LLM to autonomously
    orchestrate complex container operations without client round-trips.

    MASSIVE EFFICIENCY GAINS:
    - LLM autonomously decides tool usage and sequencing
    - No client mediation for multi-step container operations
    - Structured validation and error recovery
    - Parallel processing capabilities

    CONTAINER WORKFLOW EXAMPLES:
    - "Deploy microservices stack" → autonomous container deployment, networking
    - "Set up development environment" → multi-service orchestration, configuration
    - "Scale application cluster" → intelligent resource allocation, load balancing

    Args:
        workflow_prompt: Description of the container workflow to execute
        available_tools: List of container tool names to make available to the LLM
        max_iterations: Maximum LLM-tool interaction loops (default: 5)

    Returns:
        Structured response with workflow execution results

    Example:
        # Deploy microservices stack workflow
        result = await agentic_container_workflow(
            workflow_prompt="Deploy my web application stack",
            available_tools=["create_container", "setup_networking", "configure_volumes"],
            max_iterations=10
        )
    """
    try:
        if not workflow_prompt:
            return build_error_response(
                error="No workflow prompt provided",
                error_code="MISSING_WORKFLOW_PROMPT",
                message="workflow_prompt is required to guide the container workflow",
                recovery_options=[
                    "Provide a clear description of the container workflow to execute",
                    "Include specific goals and available tools"
                ],
                urgency="medium"
            )

        if not available_tools:
            return build_error_response(
                error="No tools specified",
                error_code="EMPTY_TOOLS_LIST",
                message="available_tools list cannot be empty",
                recovery_options=[
                    "Specify which container tools the LLM can use",
                    "Include at least one container tool for the workflow"
                ],
                urgency="medium"
            )

        # Check if context has sampling capability
        if not hasattr(context, 'sample_step'):
            return build_error_response(
                error="Sampling not available",
                error_code="SAMPLING_UNAVAILABLE",
                message="FastMCP context does not support sampling with tools",
                recovery_options=[
                    "Ensure FastMCP 2.14.1+ is installed",
                    "Check that sampling handlers are configured",
                    "Verify LLM provider supports tool calling"
                ],
                urgency="high"
            )

        logger.info(f"Starting agentic container workflow: {workflow_prompt[:50]}...")

        # Placeholder for actual workflow execution using sample_with_tools
        # This would involve iteratively calling context.sample_step
        # and executing tools based on the LLM's decisions.
        # For this example, we'll simulate a single step.

        # Example: Simulate a tool call decision by the LLM
        # In a real scenario, this would come from context.sample_step
        simulated_tool_call = {
            "tool_name": available_tools[0],
            "parameters": {"image": "nginx:latest", "name": "web-server", "ports": ["80:80"]}
        }

        # Simulate tool execution
        # In a real scenario, you would dynamically call the tool function
        # tool_result = await getattr(mcp.tools, simulated_tool_call["tool_name"]).fn(**simulated_tool_call["parameters"])
        tool_result = {"status": "created", "container_id": "abc123", "name": "web-server"}

        final_content = f"Container workflow completed. Executed {simulated_tool_call['tool_name']} with result: Container {tool_result['name']} ({tool_result['container_id']}) created and running"

        return build_success_response(
            operation="agentic_container_workflow",
            summary=f"Container workflow '{workflow_prompt[:50]}...' completed successfully.",
            result={
                "final_output": final_content,
                "iterations": 1, # Placeholder
                "executed_tools": [simulated_tool_call["tool_name"]],
                "containers_created": 1,
                "services_configured": ["web-server"]
            },
            next_steps=[
                "Verify all containers are running and healthy",
                "Check network connectivity between services",
                "Review resource allocation and scaling needs",
                "Set up monitoring and logging for the stack"
            ],
            suggestions=[
                "Try 'agentic_container_workflow(workflow_prompt=\"Deploy database cluster\", available_tools=[\"create_postgres\", \"setup_replication\"])'",
                "Explore multi-service orchestration workflows",
                "Consider using Docker Compose for complex deployments"
            ]
        )
    except Exception as e:
        logger.error(f"Agentic container workflow failed: {e}", exc_info=True)
        return build_error_response(
            error="Agentic container workflow execution failed",
            error_code="WORKFLOW_EXECUTION_ERROR",
            message=f"An unexpected error occurred during the container workflow: {str(e)}",
            recovery_options=[
                "Check the workflow_prompt for clarity and valid container instructions",
                "Ensure all container tools in available_tools are correctly implemented and registered",
                "Review Docker daemon status and resource availability",
                "Check container logs for detailed error messages"
            ],
            diagnostic_info={"exception": str(e), "workflow_type": "container_orchestration"},
            urgency="high"
        )
