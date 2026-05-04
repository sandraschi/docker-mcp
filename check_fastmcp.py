import asyncio

from fastmcp import FastMCP

mcp = FastMCP("test")
@mcp.tool()
def my_tool():
    return "ok"

async def check():
    print(f"Tools list: {mcp.list_tools()}")
    # Check if list_tools is a method or property
    if callable(mcp.list_tools):
        print("list_tools is a method")
    else:
        print("list_tools is a property")

asyncio.run(check())
