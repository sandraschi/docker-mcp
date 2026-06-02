"""Register MCP tools and fleet surface after FastMCP singleton exists."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register_all_tools(mcp=None) -> None:
    """Import tool modules (decorators) and fleet prompts/prefabs."""
    global _registered
    if _registered:
        return

    from dockermcp.fleet_surface import register_fleet_surface

    if mcp is None:
        from dockermcp.mcp_instance import get_mcp

        mcp = get_mcp()

    # Leaf imports only — avoid dockermcp.tools package __init__ (discover_tools side effects)
    import dockermcp.tools.agentic_container_workflow as _aw  # noqa: F401
    from dockermcp.tools.containers import list_containers as _lc  # noqa: F401
    from dockermcp.tools.desktop import (  # noqa: F401
        docker_daemon_recover,
        docker_daemon_restart,
        docker_desktop_status,
        docker_desktop_update,
    )
    from dockermcp.tools.docker_reconnect import register_tool as register_reconnect_tool
    from dockermcp.tools.docker_status import register_tool as register_status_tool
    from dockermcp.tools.gpu import gpu_management as _gpu  # noqa: F401
    from dockermcp.tools.images import image_management as _im  # noqa: F401
    from dockermcp.tools.networks import network_management as _nm  # noqa: F401
    from dockermcp.tools.system import system_management as _sm  # noqa: F401
    from dockermcp.tools.volumes import volume_management as _vm  # noqa: F401

    _ = [
        _aw,
        _lc,
        _im,
        _nm,
        _sm,
        _vm,
        _gpu,
        docker_desktop_status,
        docker_daemon_recover,
        docker_daemon_restart,
        docker_desktop_update,
        register_status_tool(),
        register_reconnect_tool(),
    ]

    register_fleet_surface(mcp)
    _registered = True
    logger.info("Docker MCP tools and fleet surface registered")
