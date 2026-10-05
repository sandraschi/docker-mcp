"""Basic usage: Docker status, containers, images and a short-lived volume

Calls the real docker-mcp tools through fastmcp.Client: check the daemon, list containers and
images, then create -> inspect -> remove a labelled demo volume.

Safe by default (dry run): nothing is created or removed. Set DOCKER_MCP_EXAMPLE_DRY_RUN=0 to
really run the volume steps. The webapp Examples page does this for you with its Dry run switch.

    python examples/basic_usage.py
    DOCKER_MCP_URL=http://127.0.0.1:10807/mcp DOCKER_MCP_EXAMPLE_DRY_RUN=0 python examples/basic_usage.py
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


async def mutate(client: Client, tool: str, **arguments: Any) -> dict[str, Any]:
    """Like call(), but in dry-run mode it only prints what would happen."""
    if DRY_RUN:
        print(f"  [dry-run] would call {tool}({arguments})")
        return {"status": "dry_run"}
    return await call(client, tool, **arguments)


async def run(client: Client) -> int:
    print(f"docker-mcp at {URL}  (dry run: {DRY_RUN})")
    status = await call(client, "get_docker_status_tool")
    if not status.get("docker_available"):
        print(f"Docker is not available: {status.get('error', 'unknown error')}")
        print("Start Docker Desktop and run this example again.")
        return 2
    print(f"Docker {status.get('version')} (API {status.get('api_version')})")

    print("\n== Containers ==")
    containers = (await call(client, "list_containers", params={"all_states": True})).get("containers", [])
    print(f"{len(containers)} container(s)")
    for c in containers[:5]:
        print(f"  {c.get('name')}  {c.get('image')}  {c.get('status')}")

    print("\n== Images ==")
    images = (await call(client, "list_images")).get("images", [])
    print(f"{len(images)} image(s)")
    for image in images[:5]:
        tags = image.get("repo_tags") or ["<none>"]
        print(f"  {tags[0]}  {image.get('size', 0) / 1_048_576:.1f} MB")

    print("\n== Volume lifecycle (labelled demo volume) ==")
    name = f"docker-mcp-example-{int(time.time())}"
    created = await mutate(client, "create_volume", name=name, labels=LABELS)
    if DRY_RUN:
        print(f"  [dry-run] would then inspect_volume({name!r}) and remove_volume({name!r})")
    elif created.get("status") == "success":
        print(f"  created {name}")
        try:
            info = await call(client, "inspect_volume", name=name)
            print(f"  mountpoint: {info.get('volume', {}).get('mountpoint')}")
        finally:
            removed = await call(client, "remove_volume", name=name, force=True)
            print(f"  remove: {removed.get('status')}")
    else:
        print(f"  create failed: {created.get('error') or created.get('message')}")
        return 1
    print("\nDone.")
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
