"""Stdio -> running-daemon proxy (fleet SOTA_REQUIREMENTS 2.3, "HTTP Daemon + Stdio Proxy").

Call ``proxy_if_daemon()`` first thing in a stdio entry point, *before* any Docker / tool
initialization. If a healthy docker-mcp HTTP backend is already running (the installed desktop app,
or a dev stack / service), this process becomes a thin stdio proxy to it: one instance, one
activity log, and the dashboard sees every call. Otherwise it returns False and the caller starts
a normal standalone stdio server.

Deliberately stricter than the fleet's reference probe (a single ``initialize`` POST), because a
proxy to a half-dead daemon is worse than no proxy. A candidate is used only if ALL hold:

1. ``GET /api/health`` answers 200 within 2 s with ``service == "docker-mcp"`` and
   ``status == "healthy"`` (rejects zombies that hold the port but do not answer, other apps on the
   port, and the bridge-only instance started by another stdio client);
2. ``POST /mcp`` ``initialize`` answers 200 within 3 s (rejects a backend whose MCP mount is dead).

Candidates, in order: ``DOCKER_MCP_API_URL`` (single override), the installed app's operator
backend ``127.0.0.1:11240``, the dev stack ``127.0.0.1:10807``. ``DOCKER_MCP_NO_PROXY=1`` disables
proxying. The probe runs once at startup: if the daemon dies mid-session, proxied calls fail until
it returns or the client restarts this process.
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

DEFAULT_BASES = ("http://127.0.0.1:11240", "http://127.0.0.1:10807")
HEALTH_TIMEOUT_S = 2.0
INIT_TIMEOUT_S = 3.0
_INIT_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "docker-mcp-probe", "version": "1"},
    },
}


def _log(msg: str) -> None:
    # stderr only: stdout is the MCP JSON-RPC channel
    print(f"docker-mcp: {msg}", file=sys.stderr, flush=True)


def candidate_bases() -> list[str]:
    if os.environ.get("DOCKER_MCP_NO_PROXY", "").lower() in ("1", "true", "yes"):
        return []
    override = os.environ.get("DOCKER_MCP_API_URL", "").strip().rstrip("/")
    return [override] if override else list(DEFAULT_BASES)


def _healthy(client: httpx.Client, base: str) -> bool:
    r = client.get(f"{base}/api/health", timeout=HEALTH_TIMEOUT_S)
    if r.status_code != 200:
        return False
    body = r.json()
    return body.get("service") == "docker-mcp" and body.get("status") == "healthy"


def _mcp_initializes(client: httpx.Client, base: str) -> bool:
    r = client.post(
        f"{base}/mcp",
        json=_INIT_BODY,
        headers={"Accept": "application/json, text/event-stream"},
        timeout=INIT_TIMEOUT_S,
    )
    return r.status_code == 200 and "jsonrpc" in r.text


def find_daemon() -> str | None:
    """Return the MCP URL of a healthy daemon, or None."""
    # trust_env=False: never route loopback probes through an HTTP(S)_PROXY from the environment
    with httpx.Client(trust_env=False) as client:
        for base in candidate_bases():
            try:
                if _healthy(client, base) and _mcp_initializes(client, base):
                    return f"{base}/mcp"
            except (httpx.HTTPError, ValueError):
                continue  # not listening / hung / not JSON: not a usable daemon
    return None


def proxy_if_daemon() -> bool:
    """Become a stdio proxy to a healthy running daemon. True if it ran (and has now exited)."""
    url = find_daemon()
    if url is None:
        return False
    from fastmcp.server import create_proxy

    _log(f"proxying stdio to running daemon at {url}")
    proxy = create_proxy(url, name="docker-mcp")
    asyncio.run(proxy.run_stdio_async(show_banner=False))
    return True
