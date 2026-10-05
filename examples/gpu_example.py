"""GPU tools: list GPUs, inspect one, and see how a GPU container would be started

Calls the GPU tools through fastmcp.Client. The GPU queries are read-only. Creating a GPU container
is only printed, never executed, in both modes: docker-mcp has no tool to remove a container
afterwards (and create_gpu_container cannot label it), so this example will not leave one behind.

    python examples/gpu_example.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any

from fastmcp import Client

URL = os.environ.get("DOCKER_MCP_URL", "http://127.0.0.1:10807/mcp")


async def call(client: Client, tool: str, **arguments: Any) -> dict[str, Any]:
    """Call one docker-mcp tool and return its result as a dict (errors come back as dicts too)."""
    result = await client.call_tool(tool, arguments, raise_on_error=False)
    if isinstance(result.data, dict):
        return result.data
    text = next((getattr(c, "text", "") for c in result.content), "")
    return {"status": "error" if result.is_error else "success", "message": text or str(result.data)}


async def run(client: Client) -> int:
    print(f"docker-mcp at {URL}")
    status = await call(client, "get_docker_status_tool")
    if not status.get("docker_available"):
        print(f"Docker is not available: {status.get('error', 'unknown error')}")
        print("Start Docker Desktop and run this example again.")
        return 2

    print("\n1. Listing GPUs...")
    gpus = await call(client, "list_gpus", request={"detailed": True})
    if gpus.get("status") not in (None, "success"):
        print(f"  {gpus.get('error') or gpus.get('message')}")
        return 1
    rows = gpus.get("gpus", [])
    print(f"  {gpus.get('total_gpus', len(rows))} GPU(s)")
    for gpu in rows:
        print(f"  - {gpu.get('id')}: {gpu.get('name')}")
    if not rows:
        print("  No GPUs found - nothing more to show.")
        return 0

    print("\n2. Details for the first GPU...")
    first = str(rows[0].get("id", "0"))
    info = await call(client, "get_gpu_info", request={"gpu_id": first})
    print(json.dumps(info.get("gpu", info), indent=2, default=str)[:1500])

    print("\n3. Starting a GPU container (shown, not executed)")
    name = f"gpu-test-{int(time.time())}"
    call_args = {
        "image": "nvidia/cuda:12.4.1-base-ubuntu22.04",
        "command": "nvidia-smi",
        "gpu_ids": [first],
        "name": name,
    }
    print(f"  would call create_gpu_container({call_args})")
    print("  run it from the Tools page or your MCP client if you want a real one, then remove it yourself.")
    return 0


async def _cli() -> int:
    try:
        async with Client(URL) as client:
            return await run(client)
    except Exception as exc:  # connection refused, protocol error, ...
        print(f"Cannot reach docker-mcp at {URL}: {exc}")
        return 3


if __name__ == "__main__":
    sys.exit(asyncio.run(_cli()))
