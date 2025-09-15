@echo off
echo Starting MCPJam Inspector for Docker MCP...
echo Server: http://localhost:8720
echo.
set PYTHONPATH=.
npx @mcpjam/inspector@latest --port 8720 --config mcp_config.json
