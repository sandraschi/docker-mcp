"""Register fleet SOTA surface: prompts, prefab tools, MCP resources."""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

logger = logging.getLogger(__name__)

SKILLS_MD = """# Docker-MCP skills (fleet 2026)

## When to use
- Container lifecycle, images, networks, volumes, compose workflows
- Docker Desktop hang detection, daemon recovery, graceful restart
- Multi-step orchestration: prefer `agentic_container_workflow` when the client supports sampling

## Workflows
1. **Health first**: `docker_desktop_status` or `docker_desktop_status_card`
2. **Inventory**: `list_containers` or `docker_containers_card`
3. **Recovery**: `docker_daemon_recover` only when status shows hung/unresponsive daemon
4. **Agentic**: `agentic_container_workflow` for natural-language multi-step deploy/scale tasks

## Ports (local webapp)
- Frontend Vite: 10806
- API bridge: 10807
"""


def register_fleet_surface(mcp) -> None:
    """Attach prompts, prefab tools, and resources to the singleton MCP instance."""

    @mcp.prompt()
    def docker_deploy_stack(
        stack_name: Annotated[str, Field(description="Name of the stack to deploy")] = "app",
    ) -> str:
        """Prompt template for deploying a multi-container stack."""
        return (
            f"Deploy Docker stack '{stack_name}': list images, create networks/volumes as needed, "
            "start containers in dependency order, verify health, and summarize ports and status."
        )

    @mcp.prompt()
    def docker_daemon_health_check() -> str:
        """Prompt template for Docker Desktop / daemon diagnostics."""
        return (
            "Check Docker daemon health with docker_desktop_status. If hung, use docker_daemon_recover "
            "then docker_daemon_restart. Report recent containers, images, and resource limits."
        )

    @mcp.resource("resource://docker-mcp/skills")
    def docker_mcp_skills() -> str:
        return SKILLS_MD

    @mcp.resource("resource://docker-mcp/capabilities")
    def docker_mcp_capabilities() -> str:
        return (
            "docker-mcp: FastMCP 3.3+, sampling (Ollama/LM Studio), agentic_container_workflow, "
            "prefab cards, MCP prompts, webapp /logs + LLM glom-on. Transports: stdio, HTTP."
        )

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def docker_containers_card(
        all_states: Annotated[bool, Field(description="Include stopped containers")] = True,
    ):
        """List containers as a Prefab card (fleet list/status surface)."""
        from dockermcp.prefabs import build_containers_card
        from dockermcp.tools.containers.list_containers import (
            ListContainersParams,
            list_containers,
        )

        result = await list_containers(ListContainersParams(all_states=all_states))
        return build_containers_card(result if isinstance(result, dict) else {})

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def docker_desktop_status_card(
        autofix: Annotated[bool, Field(description="Attempt auto-fix if daemon is hung")] = False,
    ):
        """Docker Desktop / daemon status as a Prefab card."""
        from dockermcp.prefabs import build_desktop_status_card
        from dockermcp.tools.desktop.desktop_status import docker_desktop_status

        result = await docker_desktop_status(autofix=autofix)
        payload = result.model_dump() if hasattr(result, "model_dump") else result
        return build_desktop_status_card(payload if isinstance(payload, dict) else {})

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def docker_system_info_card():
        """Engine system info as a Prefab card."""
        from dockermcp.prefabs import build_system_info_card
        from dockermcp.tools.system.system_management import (
            SystemInfoRequest,
            get_system_info,
        )

        result = await get_system_info(
            SystemInfoRequest(include_disk_usage=True, include_swarm_info=False)
        )
        payload = result.model_dump() if hasattr(result, "model_dump") else result
        return build_system_info_card(payload if isinstance(payload, dict) else {})

    logger.info("Fleet surface registered: prompts, resources, prefab tools")
