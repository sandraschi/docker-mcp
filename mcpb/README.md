# schip-mcp-docker (MCPB Bundle)

FastMCP 3.3 server for comprehensive Docker operations

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "schip-mcp-docker": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "schip_mcp_docker"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **main_stdio**: main(stdio)
- **main_http**: main(http)
- **main_sse**: main(sse)
- **docker_containers_card**: docker_containers_card
- **docker_desktop_status_card**: docker_desktop_status_card
- **docker_system_info_card**: Engine system info as a Prefab card.
- **health**: health
- **get_dashboard**: Get dashboard overview with system info and container status
- **get_containers**: Get list of all containers
- **get_tools**: Get list of available MCP tools
- **list_containers**: list_containers
- **example_tool**: example_tool
- **agentic_container_workflow**: agentic_container_workflow
- **get_docker_status_tool**: get_docker_status_tool
- **docker_daemon_recover**: docker_daemon_recover
- **docker_daemon_restart**: docker_daemon_restart
- **docker_desktop_status**: docker_desktop_status
- **docker_desktop_update**: docker_desktop_update
- **list_gpus**: list_gpus
- **get_gpu_info**: get_gpu_info
- **monitor_gpu_usage**: monitor_gpu_usage
- **get_image_history**: get_image_history
- **list_volumes**: list_volumes
- **create_volume**: create_volume
- **remove_volume**: remove_volume
- **prune_volumes**: prune_volumes
- **capabilities**: capabilities
- **list_tools**: list_tools
- **llm_providers**: llm_providers
- **logs_query**: logs_query
- **logs_stats**: logs_stats
- **logs_export**: logs_export
- **logs_clear**: logs_clear
- **api_containers**: api_containers
- **api_system**: api_system
- **api_images**: api_images
- **api_dashboard**: api_dashboard
- **chat**: chat

## Requirements

- Python 3.12+
- uv
