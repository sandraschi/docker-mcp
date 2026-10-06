"""Stdio->daemon proxy probe: only a healthy docker-mcp daemon may be proxied to."""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docker_mcp import daemon_probe

INIT_OK = {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "docker-mcp"}}}


def _make_handler(health: dict | None, health_status: int, mcp_status: int):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence
            pass

        def _send(self, status: int, body: dict | None):
            payload = json.dumps(body or {}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/api/health":
                self._send(health_status, health)
            else:
                self._send(404, None)

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/mcp":
                self._send(mcp_status, INIT_OK if mcp_status == 200 else None)
            else:
                self._send(404, None)

    return Handler


@pytest.fixture
def serve():
    servers: list[HTTPServer] = []

    def start(health=None, health_status=200, mcp_status=200) -> str:
        srv = HTTPServer(("127.0.0.1", 0), _make_handler(health, health_status, mcp_status))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    yield start
    for s in servers:
        s.shutdown()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("DOCKER_MCP_NO_PROXY", raising=False)
    monkeypatch.delenv("DOCKER_MCP_API_URL", raising=False)


def test_healthy_daemon_is_found(serve, monkeypatch):
    base = serve(health={"status": "healthy", "service": "docker-mcp"})
    monkeypatch.setenv("DOCKER_MCP_API_URL", base)
    assert daemon_probe.find_daemon() == f"{base}/mcp"


def test_nothing_listening_means_no_daemon(monkeypatch):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    monkeypatch.setenv("DOCKER_MCP_API_URL", f"http://127.0.0.1:{port}")
    assert daemon_probe.find_daemon() is None


def test_hung_zombie_is_rejected_within_health_timeout(monkeypatch):
    """A process that holds the port, accepts connections and never answers."""
    zombie = socket.socket()
    zombie.bind(("127.0.0.1", 0))
    zombie.listen(5)
    monkeypatch.setenv("DOCKER_MCP_API_URL", f"http://127.0.0.1:{zombie.getsockname()[1]}")
    started = time.monotonic()
    try:
        assert daemon_probe.find_daemon() is None
    finally:
        zombie.close()
    assert time.monotonic() - started < daemon_probe.HEALTH_TIMEOUT_S + 2


def test_other_service_on_the_port_is_rejected(serve, monkeypatch):
    monkeypatch.setenv("DOCKER_MCP_API_URL", serve(health={"status": "healthy", "service": "something-else"}))
    assert daemon_probe.find_daemon() is None


def test_unhealthy_status_is_rejected(serve, monkeypatch):
    monkeypatch.setenv("DOCKER_MCP_API_URL", serve(health={"status": "degraded", "service": "docker-mcp"}))
    assert daemon_probe.find_daemon() is None


def test_health_500_is_rejected(serve, monkeypatch):
    monkeypatch.setenv("DOCKER_MCP_API_URL", serve(health=None, health_status=500))
    assert daemon_probe.find_daemon() is None


def test_healthy_but_mcp_mount_dead_is_rejected(serve, monkeypatch):
    """e.g. the bridge-only web app another stdio client started: /api/health yes, /mcp no."""
    monkeypatch.setenv(
        "DOCKER_MCP_API_URL", serve(health={"status": "healthy", "service": "docker-mcp"}, mcp_status=404)
    )
    assert daemon_probe.find_daemon() is None


def test_opt_out(serve, monkeypatch):
    monkeypatch.setenv("DOCKER_MCP_API_URL", serve(health={"status": "healthy", "service": "docker-mcp"}))
    monkeypatch.setenv("DOCKER_MCP_NO_PROXY", "1")
    assert daemon_probe.find_daemon() is None


def test_default_candidates_are_operator_then_dev():
    assert daemon_probe.candidate_bases() == ["http://127.0.0.1:11240", "http://127.0.0.1:10807"]
