from fastmcp import FastMCP
import os


def run_server(mcp: FastMCP, server_name: str = "mcp-server"):
    """Run MCP server in standard SOTA mode (dual transport)."""
    # Check for HTTP transport override
    if os.getenv("MCP_TRANSPORT") == "http":
        import uvicorn

        # This is usually handled in server.py main
        pass
    else:
        # Default to STDIO
        mcp.run()
