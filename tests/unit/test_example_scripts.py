"""Behavioural tests for the scripts in examples/, run against an in-memory stub MCP server.

The stub records every tool call and returns canned docker-mcp style payloads, so the success paths
(dry run never mutates, create -> inspect -> remove ordering, cleanup after a failure) are exercised
without a Docker daemon.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastmcp import Client, FastMCP

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
MUTATING = {"create_volume", "remove_volume", "create_network", "remove_network", "create_gpu_container"}


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"example_{name}", EXAMPLES / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stub:
    """Canned docker-mcp server. `fail` maps tool name -> True to make that tool return an error payload."""

    def __init__(self, *, docker_up: bool = True, containers=None, gpus=None):
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail: dict[str, bool] = {}
        self.docker_up = docker_up
        self.container_snapshots = list(containers or [[]])
        self.gpus = gpus or []
        self.server = FastMCP("stub")
        self._register()

    def _record(self, tool: str, args: dict[str, Any]) -> dict[str, Any] | None:
        self.calls.append((tool, args))
        if self.fail.get(tool):
            return {"status": "error", "error": f"{tool} failed on purpose"}
        return None

    def _register(self) -> None:
        s = self.server

        @s.tool
        def get_docker_status_tool() -> dict:
            self.calls.append(("get_docker_status_tool", {}))
            if not self.docker_up:
                return {"docker_available": False, "error": "daemon not running"}
            return {"docker_available": True, "version": "27.0", "api_version": "1.46"}

        @s.tool
        def list_containers(params: dict) -> dict:
            self.calls.append(("list_containers", {"params": params}))
            if self.fail.get("list_containers"):
                return {"status": "error", "error": "list failed on purpose"}
            snap = self.container_snapshots[
                min(sum(1 for c in self.calls if c[0] == "list_containers") - 1, len(self.container_snapshots) - 1)
            ]
            return {"status": "success", "containers": snap}

        @s.tool
        def list_images() -> dict:
            self.calls.append(("list_images", {}))
            return {"status": "success", "images": [{"repo_tags": ["alpine:latest"], "size": 8 * 1048576}]}

        @s.tool
        def create_volume(name: str, labels: dict | None = None) -> dict:
            return self._record("create_volume", {"name": name, "labels": labels}) or {
                "status": "success",
                "volume": {"name": name},
            }

        @s.tool
        def inspect_volume(name: str) -> dict:
            return self._record("inspect_volume", {"name": name}) or {
                "status": "success",
                "volume": {"name": name, "mountpoint": "/var/lib/docker/volumes/x/_data"},
            }

        @s.tool
        def remove_volume(name: str, force: bool = False) -> dict:
            return self._record("remove_volume", {"name": name, "force": force}) or {"status": "success", "name": name}

        @s.tool
        def create_network(params: dict) -> dict:
            return self._record("create_network", {"params": params}) or {"status": "success"}

        @s.tool
        def remove_network(network_id: str, force: bool = False) -> dict:
            return self._record("remove_network", {"network_id": network_id, "force": force}) or {"status": "success"}

        @s.tool
        def list_volumes(labels: dict | None = None) -> dict:
            self.calls.append(("list_volumes", {"labels": labels}))
            return {"status": "success", "volumes": [{"name": "v"}]}

        @s.tool
        def list_gpus(request: dict) -> dict:
            self.calls.append(("list_gpus", {"request": request}))
            return {"status": "success", "total_gpus": len(self.gpus), "gpus": self.gpus}

        @s.tool
        def get_gpu_info(request: dict) -> dict:
            self.calls.append(("get_gpu_info", {"request": request}))
            return {"status": "success", "gpu": {"id": request["gpu_id"], "name": "Fake RTX"}}

        @s.tool
        def create_gpu_container(image: str) -> dict:
            self.calls.append(("create_gpu_container", {"image": image}))
            return {"status": "success"}

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]


def run_example(module: ModuleType, stub: Stub) -> int:
    async def go() -> int:
        async with Client(stub.server) as client:
            return await module.run(client)

    return asyncio.run(go())


# --- basic_usage ----------------------------------------------------------------------------


def test_basic_dry_run_never_mutates(monkeypatch, capsys):
    mod = load("basic_usage")
    monkeypatch.setattr(mod, "DRY_RUN", True)
    stub = Stub()
    assert run_example(mod, stub) == 0
    assert not MUTATING & set(stub.names())
    out = capsys.readouterr().out
    assert "[dry-run] would call create_volume" in out
    assert "alpine:latest" in out


def test_basic_real_run_creates_inspects_then_removes_same_volume(monkeypatch):
    mod = load("basic_usage")
    monkeypatch.setattr(mod, "DRY_RUN", False)
    stub = Stub()
    assert run_example(mod, stub) == 0
    seq = [n for n in stub.names() if n in {"create_volume", "inspect_volume", "remove_volume"}]
    assert seq == ["create_volume", "inspect_volume", "remove_volume"]
    created = dict(stub.calls)["create_volume"]
    assert created["labels"] == {"docker-mcp.example": "1"}
    assert dict(stub.calls)["remove_volume"]["name"] == created["name"]


def test_basic_removes_volume_even_when_inspect_fails(monkeypatch):
    mod = load("basic_usage")
    monkeypatch.setattr(mod, "DRY_RUN", False)
    stub = Stub()
    stub.fail["inspect_volume"] = True
    run_example(mod, stub)
    assert "remove_volume" in stub.names()


def test_basic_create_failure_exits_1_and_removes_nothing(monkeypatch):
    mod = load("basic_usage")
    monkeypatch.setattr(mod, "DRY_RUN", False)
    stub = Stub()
    stub.fail["create_volume"] = True
    assert run_example(mod, stub) == 1
    assert "remove_volume" not in stub.names()


def test_basic_docker_down_exits_2_with_hint(monkeypatch, capsys):
    mod = load("basic_usage")
    monkeypatch.setattr(mod, "DRY_RUN", False)
    stub = Stub(docker_up=False)
    assert run_example(mod, stub) == 2
    assert stub.names() == ["get_docker_status_tool"]
    assert "Start Docker Desktop" in capsys.readouterr().out


# --- advanced_workflow ----------------------------------------------------------------------


def test_advanced_dry_run_only_prints_plan(monkeypatch, capsys):
    mod = load("advanced_workflow")
    monkeypatch.setattr(mod, "DRY_RUN", True)
    stub = Stub()
    assert run_example(mod, stub) == 0
    assert stub.names() == ["get_docker_status_tool"]
    assert "would call create_network" in capsys.readouterr().out


def test_advanced_real_run_cleans_up_in_reverse_order(monkeypatch):
    mod = load("advanced_workflow")
    monkeypatch.setattr(mod, "DRY_RUN", False)
    stub = Stub()
    assert run_example(mod, stub) == 0
    mut = [n for n in stub.names() if n in MUTATING]
    assert mut == ["create_network", "create_volume", "remove_volume", "remove_network"]
    calls = dict(stub.calls)
    assert calls["create_network"]["params"]["labels"] == {"docker-mcp.example": "1"}
    assert calls["remove_network"]["network_id"] == calls["create_network"]["params"]["name"]


def test_advanced_failure_midway_only_removes_what_was_created(monkeypatch):
    mod = load("advanced_workflow")
    monkeypatch.setattr(mod, "DRY_RUN", False)
    stub = Stub()
    stub.fail["create_volume"] = True
    assert run_example(mod, stub) == 1
    mut = [n for n in stub.names() if n in MUTATING]
    assert mut == ["create_network", "create_volume", "remove_network"]


# --- monitoring_and_alerting ---------------------------------------------------------------


def _states(*pairs):
    return [{"name": n, "status": s} for n, s in pairs]


def test_monitoring_reports_changes_and_alerts(monkeypatch, capsys):
    mod = load("monitoring_and_alerting")
    monkeypatch.setattr(mod, "POLLS", 2)
    monkeypatch.setattr(mod, "INTERVAL", 0)
    monkeypatch.setattr(mod, "MAX_EXITED", 1)
    first = _states(("web", "Up 2 hours (running)"), ("db", "running"), ("old1", "Exited (0)"))
    second = _states(("web", "running"), ("db", "Restarting (1)"), ("old1", "Exited (0)"), ("old2", "Exited (1)"))
    stub = Stub(containers=[first, second])
    assert run_example(mod, stub) == 0
    out = capsys.readouterr().out
    assert "changed: db running -> restarting" in out
    assert "changed: old2 new -> exited" in out
    assert "ALERT: 2 exited containers (limit 1)" in out
    assert "ALERT: db is restarting" in out
    assert "Alerts were raised" in out


def test_monitoring_quiet_when_healthy(monkeypatch, capsys):
    mod = load("monitoring_and_alerting")
    monkeypatch.setattr(mod, "POLLS", 2)
    monkeypatch.setattr(mod, "INTERVAL", 0)
    stub = Stub(containers=[_states(("web", "running"))])
    assert run_example(mod, stub) == 0
    assert "No alerts" in capsys.readouterr().out


def test_monitoring_list_failure_exits_1(monkeypatch):
    mod = load("monitoring_and_alerting")
    monkeypatch.setattr(mod, "POLLS", 2)
    stub = Stub()
    stub.fail["list_containers"] = True
    assert run_example(mod, stub) == 1


def test_monitoring_docker_down_exits_2(monkeypatch):
    mod = load("monitoring_and_alerting")
    assert run_example(mod, Stub(docker_up=False)) == 2


# --- gpu_example ------------------------------------------------------------------------------


def test_gpu_no_gpus_is_a_clean_exit(capsys):
    mod = load("gpu_example")
    stub = Stub(gpus=[])
    assert run_example(mod, stub) == 0
    assert "No GPUs found" in capsys.readouterr().out
    assert "get_gpu_info" not in stub.names()


def test_gpu_shows_container_call_but_never_executes_it(capsys):
    mod = load("gpu_example")
    stub = Stub(gpus=[{"id": "0", "name": "Fake RTX"}])
    assert run_example(mod, stub) == 0
    out = capsys.readouterr().out
    assert "Fake RTX" in out
    assert "would call create_gpu_container" in out
    assert "create_gpu_container" not in stub.names()


# --- every example is discoverable and documented ---------------------------------------------


@pytest.mark.parametrize("name", ["basic_usage", "advanced_workflow", "monitoring_and_alerting", "gpu_example"])
def test_examples_have_title_and_cli_entrypoint(name):
    source = (EXAMPLES / f"{name}.py").read_text(encoding="utf-8")
    assert source.startswith('"""') and "\n" in source.split('"""')[1]
    assert 'if __name__ == "__main__":' in source
    assert "MCPClient" not in source  # the fastmcp class that does not exist
