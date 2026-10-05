"""Advanced workflow: a labelled network + volume stack with guaranteed cleanup

Builds a tiny "stack" (one network, one volume), shows label-filtered listing, then tears it down in
reverse order inside a finally block - so a failure half-way still cleans up what was created.
Everything it creates carries the label docker-mcp.example=1.

Safe by default (dry run): the create/remove steps are only printed. Set DOCKER_MCP_EXAMPLE_DRY_RUN=0
to run them for real.

    python examples/advanced_workflow.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any

from fastmcp import Client

URL = os.environ.get("DOCKER_MCP_URL", "http://127.0.0.1:10807/mcp")
DRY_RUN = os.environ.get("DOCKER_MCP_EXAMPLE_DRY_RUN", "1") != "0"
LABELS = {"docker-mcp.example": "1"}


async def call(client: Client, tool: str, **arguments: Any) -> dict[str, Any]:
    """Call one docker-mcp tool and return its result as a dict (errors come back as dicts too)."""
    result = await client.call_tool(tool, arguments, raise_on_error=False)
    if isinstance(result.data, dict):
        return result.data
    text = next((getattr(c, "text", "") for c in result.content), "")
    return {"status": "error" if result.is_error else "success", "message": text or str(result.data)}


def succeeded(data: dict[str, Any]) -> bool:
    return data.get("status") == "success" or data.get("success") is True


async def run(client: Client) -> int:
    print(f"docker-mcp at {URL}  (dry run: {DRY_RUN})")
    status = await call(client, "get_docker_status_tool")
    if not status.get("docker_available"):
        print(f"Docker is not available: {status.get('error', 'unknown error')}")
        print("Start Docker Desktop and run this example again.")
        return 2

    stack = f"docker-mcp-example-{int(time.time())}"
    plan = [
        ("create_network", {"params": {"name": stack, "labels": LABELS}}),
        ("create_volume", {"name": stack, "labels": LABELS}),
    ]
    if DRY_RUN:
        print(f"\nStack {stack!r} - planned steps:")
        for tool, args in plan:
            print(f"  [dry-run] would call {tool}({args})")
        print(f"  [dry-run] would list volumes labelled {LABELS}, then remove the volume and the network")
        print("\nDone (nothing was changed).")
        return 0

    print(f"\nStack {stack!r}")
    created: list[str] = []
    failed = False
    try:
        for tool, args in plan:
            data = await call(client, tool, **args)
            print(f"  {tool}: {data.get('status', data.get('success'))}")
            if not succeeded(data):
                print(f"    {data.get('error') or data.get('message')}")
                failed = True
                break
            created.append(tool)

        if not failed:
            volumes = (await call(client, "list_volumes", labels=LABELS)).get("volumes", [])
            print(f"  volumes labelled {LABELS}: {len(volumes)}")
    finally:
        print("\nCleanup:")
        for tool in reversed(created):
            if tool == "create_volume":
                data = await call(client, "remove_volume", name=stack, force=True)
                print(f"  remove_volume: {data.get('status')}")
            else:
                data = await call(client, "remove_network", network_id=stack, force=True)
                print(f"  remove_network: {data.get('status')}")
    return 1 if failed else 0


async def _cli() -> int:
    try:
        async with Client(URL) as client:
            return await run(client)
    except Exception as exc:  # connection refused, protocol error, ...
        print(f"Cannot reach docker-mcp at {URL}: {exc}")
        return 3


if __name__ == "__main__":
    sys.exit(asyncio.run(_cli()))
