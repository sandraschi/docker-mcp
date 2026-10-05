"""Monitoring and alerting: poll container states and raise threshold alerts

Polls list_containers a few times, prints a one-line summary per poll, reports containers that
changed state between polls, and prints ALERT lines when a threshold is crossed. Read-only: it
never changes anything, so the dry-run switch does not matter here.

Tune it with environment variables: EXAMPLE_POLLS (default 3), EXAMPLE_INTERVAL seconds (default 2),
EXAMPLE_MAX_EXITED (default 3), EXAMPLE_MAX_TOTAL (default 50).

    python examples/monitoring_and_alerting.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from fastmcp import Client

URL = os.environ.get("DOCKER_MCP_URL", "http://127.0.0.1:10807/mcp")
POLLS = int(os.environ.get("EXAMPLE_POLLS", "3"))
INTERVAL = float(os.environ.get("EXAMPLE_INTERVAL", "2"))
MAX_EXITED = int(os.environ.get("EXAMPLE_MAX_EXITED", "3"))
MAX_TOTAL = int(os.environ.get("EXAMPLE_MAX_TOTAL", "50"))


async def call(client: Client, tool: str, **arguments: Any) -> dict[str, Any]:
    """Call one docker-mcp tool and return its result as a dict (errors come back as dicts too)."""
    result = await client.call_tool(tool, arguments, raise_on_error=False)
    if isinstance(result.data, dict):
        return result.data
    text = next((getattr(c, "text", "") for c in result.content), "")
    return {"status": "error" if result.is_error else "success", "message": text or str(result.data)}


def state_of(container: dict[str, Any]) -> str:
    text = str(container.get("state") or container.get("status") or "").lower()
    for word in ("running", "restarting", "paused", "exited", "created", "dead"):
        if word in text:
            return word
    return text or "unknown"


def alerts_for(states: dict[str, str]) -> list[str]:
    counts: dict[str, int] = {}
    for state in states.values():
        counts[state] = counts.get(state, 0) + 1
    alerts = []
    if counts.get("exited", 0) > MAX_EXITED:
        alerts.append(f"{counts['exited']} exited containers (limit {MAX_EXITED})")
    if len(states) > MAX_TOTAL:
        alerts.append(f"{len(states)} containers in total (limit {MAX_TOTAL})")
    alerts += [f"{name} is restarting" for name, state in sorted(states.items()) if state == "restarting"]
    return alerts


async def run(client: Client) -> int:
    print(f"docker-mcp at {URL}  ({POLLS} polls, {INTERVAL}s apart)")
    status = await call(client, "get_docker_status_tool")
    if not status.get("docker_available"):
        print(f"ALERT: Docker is not available: {status.get('error', 'unknown error')}")
        return 2

    previous: dict[str, str] = {}
    alerted = False
    for poll in range(1, POLLS + 1):
        data = await call(client, "list_containers", params={"all_states": True})
        if data.get("status") != "success":
            print(f"poll {poll}: ALERT: list_containers failed: {data.get('error') or data.get('message')}")
            return 1
        states = {str(c.get("name")): state_of(c) for c in data.get("containers", [])}
        running = sum(1 for s in states.values() if s == "running")
        print(f"poll {poll}: {len(states)} containers, {running} running")
        for name, state in sorted(states.items()):
            if poll > 1 and previous.get(name) != state:
                print(f"  changed: {name} {previous.get(name, 'new')} -> {state}")
        for alert in alerts_for(states):
            print(f"  ALERT: {alert}")
            alerted = True
        previous = states
        if poll < POLLS:
            await asyncio.sleep(INTERVAL)
    print("\nDone." + (" Alerts were raised." if alerted else " No alerts."))
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
