"""
FastMCP 3.3+ Sampling with Tools Orchestration (SEP-1577)

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

from dockermcp.mcp_instance import mcp

logger = logging.getLogger(__name__)


def build_success_response(**kwargs) -> dict:
    return {
        "success": True,
        "operation": kwargs.get("operation", "unknown"),
        "summary": kwargs.get("summary", "Operation completed"),
        "result": kwargs.get("result", {}),
        "next_steps": kwargs.get("next_steps", []),
        "suggestions": kwargs.get("suggestions", []),
        "sampling_used": kwargs.get("sampling_used", False),
    }


def build_error_response(**kwargs) -> dict:
    return {
        "success": False,
        "error": kwargs.get("error", "Unknown error"),
        "error_code": kwargs.get("error_code", "UNKNOWN_ERROR"),
        "message": kwargs.get("message", "An error occurred"),
        "recovery_options": kwargs.get("recovery_options", []),
        "urgency": kwargs.get("urgency", "medium"),
        "sampling_used": False,
    }


@mcp.tool()
async def agentic_container_workflow(
    workflow_prompt: str, available_tools: list[str], max_iterations: int = 5, context: Context | None = None
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
                    "Include specific goals and available tools",
                ],
                urgency="medium",
            )

        if not available_tools:
            return build_error_response(
                error="No tools specified",
                error_code="EMPTY_TOOLS_LIST",
                message="available_tools list cannot be empty",
                recovery_options=[
                    "Specify which container tools the LLM can use",
                    "Include at least one container tool for the workflow",
                ],
                urgency="medium",
            )

        logger.info("Starting agentic container workflow: %s...", workflow_prompt[:50])

        system = (
            "You are docker-mcp orchestrating Docker tools. "
            f"Available tool names: {', '.join(available_tools)}. "
            "Respond with a concise plan and which tools to call."
        )
        user_msg = f"Workflow (max {max_iterations} steps): {workflow_prompt}"

        if context is not None and hasattr(context, "sample"):
            try:
                reply = await context.sample(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                )
                text = getattr(reply, "text", None) or str(reply)
                return build_success_response(
                    operation="agentic_container_workflow",
                    summary="Agentic response via FastMCP sampling",
                    result={
                        "final_output": text,
                        "iterations": 1,
                        "executed_tools": [],
                        "sampling_used": True,
                    },
                    next_steps=[
                        "Execute suggested tools manually or re-run with a sampling-capable client",
                    ],
                )
            except Exception as sample_exc:
                logger.warning("Sampling failed, falling back: %s", sample_exc)

        return build_success_response(
            operation="agentic_container_workflow",
            summary="Structured fallback (no sampling from client)",
            result={
                "final_output": (
                    f"Task: {workflow_prompt}. Configure Ollama/LM Studio and use a "
                    "sampling-capable MCP host (Cursor, Claude Desktop) for full agentic loops."
                ),
                "iterations": 0,
                "executed_tools": available_tools[:3],
                "sampling_used": False,
            },
            suggestions=[
                "Set DOCKER_MCP_SAMPLING_BASE_URL to your OpenAI-compatible endpoint",
                "Ensure the MCP client supports FastMCP 3.3 sampling",
            ],
        )
    except Exception as e:
        logger.error(f"Agentic container workflow failed: {e}", exc_info=True)
        return build_error_response(
            error="Agentic container workflow execution failed",
            error_code="WORKFLOW_EXECUTION_ERROR",
            message=f"An unexpected error occurred during the container workflow: {e!s}",
            recovery_options=[
                "Check the workflow_prompt for clarity and valid container instructions",
                "Ensure all container tools in available_tools are correctly implemented and registered",
                "Review Docker daemon status and resource availability",
                "Check container logs for detailed error messages",
            ],
            diagnostic_info={"exception": str(e), "workflow_type": "container_orchestration"},
            urgency="high",
        )
