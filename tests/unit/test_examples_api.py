"""Tests for the Examples page backend: script runner allow-list and the labelled-sandbox CRUD demo."""

from __future__ import annotations

import sys
import textwrap
from types import SimpleNamespace

import pytest
from docker.errors import ImageNotFound, NotFound
from fastapi.testclient import TestClient

sys.path.insert(0, "src")

from docker_mcp import examples_api as ex
from server import web_app

LABEL = ex.EXAMPLE_LABEL


# --- fake docker client ---------------------------------------------------------------


class FakeContainer:
    def __init__(self, cid: str, name: str, labels: dict[str, str] | None = None, status: str = "running"):
        self.id = cid * 64 if len(cid) == 1 else cid
        self.name = "/" + name
        self.labels = labels or {}
        self.status = status
        self.image = SimpleNamespace(tags=["alpine:latest"])
        self.attrs = {"Created": "2026-10-05T00:00:00Z", "Config": {"Image": "alpine:latest"}, "HostConfig": {}}
        self.removed = False
        self.calls: list[str] = []

    def reload(self) -> None:
        pass

    def rename(self, new: str) -> None:
        self.calls.append(f"rename:{new}")
        self.name = "/" + new

    def update(self, **kwargs) -> None:
        self.calls.append(f"update:{kwargs['restart_policy']['Name']}")
        self.attrs["HostConfig"] = {"RestartPolicy": kwargs["restart_policy"]}

    def remove(self, force: bool = False) -> None:
        self.calls.append(f"remove:{force}")
        self.removed = True


class FakeClient:
    def __init__(self, containers: list[FakeContainer] | None = None, have_image: bool = True):
        self._containers = containers or []
        self.have_image = have_image
        self.pulled: list[tuple[str, str]] = []
        self.ran: list[dict] = []
        self.containers = SimpleNamespace(get=self._get, list=self._list, run=self._run)
        self.images = SimpleNamespace(get=self._image_get, pull=self._pull)

    def _get(self, cid: str) -> FakeContainer:
        for c in self._containers:
            if c.id.startswith(cid) or c.name.lstrip("/") == cid:
                return c
        raise NotFound("no such container")

    def _list(self, all: bool = False, filters: dict | None = None) -> list[FakeContainer]:
        want = (filters or {}).get("label")
        if want:
            key, _, val = want.partition("=")
            return [c for c in self._containers if c.labels.get(key) == val]
        return list(self._containers)

    def _run(self, image, command, **kwargs) -> FakeContainer:
        self.ran.append({"image": image, "command": command, **kwargs})
        c = FakeContainer("c", kwargs["name"], kwargs["labels"])
        self._containers.append(c)
        return c

    def _image_get(self, ref: str):
        if not self.have_image:
            raise ImageNotFound("missing")
        return object()

    def _pull(self, repo: str, tag: str = "latest") -> None:
        self.pulled.append((repo, tag))
        self.have_image = True


@pytest.fixture
def client():
    return TestClient(web_app)


@pytest.fixture
def fake(monkeypatch):
    f = FakeClient([FakeContainer("a", "demo-one", {LABEL: "1"}), FakeContainer("b", "my-prod-db", {"app": "db"})])
    monkeypatch.setattr(ex, "require_client", lambda: f)
    return f


# --- scripts: listing, allow-list, running ----------------------------------------------


def test_list_examples_reads_docstring_title_and_skips_odd_names(tmp_path):
    (tmp_path / "good_one.py").write_text('"""Good Title\n\nLonger text."""\nprint(1)\n')
    (tmp_path / "Bad-Name.py").write_text("print(1)\n")
    (tmp_path / "notes.txt").write_text("x")
    rows = ex.list_examples(tmp_path)
    assert [r["name"] for r in rows] == ["good_one.py"]
    assert rows[0]["title"] == "Good Title"
    assert rows[0]["description"] == "Longer text."


def test_run_example_captures_output_exit_code_and_env(tmp_path):
    script = tmp_path / "ex" / "show_env.py"
    script.parent.mkdir()
    script.write_text(
        textwrap.dedent(
            """
            import os, sys
            print("dry=" + os.environ["DOCKER_MCP_EXAMPLE_DRY_RUN"], os.environ["DOCKER_MCP_URL"])
            print("oops", file=sys.stderr)
            sys.exit(3)
            """
        )
    )
    out = ex.run_example(script, dry_run=True, mcp_url="http://127.0.0.1:1/mcp")
    assert out["exit_code"] == 3
    assert out["stdout"].strip() == "dry=1 http://127.0.0.1:1/mcp"
    assert "oops" in out["stderr"]
    assert out["timed_out"] is False
    assert ex.run_example(script, dry_run=False, mcp_url="u")["stdout"].startswith("dry=0")


def test_run_example_times_out(tmp_path):
    script = tmp_path / "ex" / "slow.py"
    script.parent.mkdir()
    script.write_text("import time\nprint('start', flush=True)\ntime.sleep(30)\n")
    out = ex.run_example(script, dry_run=True, mcp_url="u", timeout=1)
    assert out["timed_out"] is True
    assert out["exit_code"] == -1
    assert "timed out" in out["stderr"]


def test_api_lists_real_examples(client):
    body = client.get("/api/examples").json()
    names = {e["name"] for e in body["examples"]}
    assert {"basic_usage.py", "advanced_workflow.py", "monitoring_and_alerting.py", "gpu_example.py"} <= names
    assert all(e["title"] for e in body["examples"])


@pytest.mark.parametrize("bad", ["nope.py", "basic_usage.txt", "Basic_Usage.py"])
def test_source_and_run_reject_unknown_names(client, bad):
    assert client.get(f"/api/examples/{bad}/source").status_code == 404
    assert client.post(f"/api/examples/{bad}/run", json={}).status_code == 404


@pytest.mark.parametrize("bad", ["../server.py", r"..\server.py", "a/b.py", "/etc/passwd", "sub/../basic_usage.py"])
def test_example_path_rejects_traversal(bad):
    with pytest.raises(ex.HTTPException) as exc:
        ex._example_path(bad)
    assert exc.value.status_code == 404


@pytest.mark.parametrize("bad", ["..%2Fserver.py", "%2e%2e%2f%2e%2e%2fsetup.py"])
def test_encoded_traversal_never_runs_anything(client, bad):
    # the HTTP client collapses '..' before routing, so these never reach the run route (404/405, never 200)
    assert client.get(f"/api/examples/{bad}/source").status_code == 404
    assert client.post(f"/api/examples/{bad}/run", json={}).status_code in (404, 405)


def test_api_source_returns_file(client):
    body = client.get("/api/examples/basic_usage.py/source").json()
    assert body["name"] == "basic_usage.py"
    assert "import" in body["source"]


# --- sandbox CRUD ---------------------------------------------------------------------


def test_list_only_returns_labelled_containers(client, fake):
    body = client.get("/api/examples/sandbox/containers").json()
    assert [c["name"] for c in body["containers"]] == ["demo-one"]
    assert body["count"] == 1


def test_create_defaults_to_dry_run_and_never_touches_docker(client, fake):
    r = client.post("/api/examples/sandbox/containers", json={"name": "demo-two"})
    assert r.status_code == 201
    assert r.json()["dry_run"] is True
    assert fake.ran == [] and fake.pulled == []


def test_create_for_real_pulls_missing_image_and_labels(client, fake):
    fake.have_image = False
    r = client.post(
        "/api/examples/sandbox/containers",
        json={"name": "demo-two", "image": "alpine:3.20", "command": "sleep 5", "dry_run": False},
    )
    assert r.status_code == 201
    assert fake.pulled == [("alpine", "3.20")]
    assert fake.ran[0]["labels"] == {LABEL: "1"}
    assert fake.ran[0]["detach"] is True
    assert r.json()["container"]["name"] == "demo-two"


@pytest.mark.parametrize("name", ["", "-lead", "has space", "x" * 64, "a/b"])
def test_create_validates_name(client, fake, name):
    assert client.post("/api/examples/sandbox/containers", json={"name": name, "dry_run": False}).status_code == 400
    assert fake.ran == []


def test_update_renames_and_sets_policy(client, fake):
    r = client.put(
        "/api/examples/sandbox/containers/demo-one",
        json={"name": "renamed", "restart_policy": "always", "dry_run": False},
    )
    body = r.json()
    assert r.status_code == 200
    assert body["container"]["name"] == "renamed"
    assert body["container"]["restart_policy"] == "always"


def test_update_dry_run_changes_nothing(client, fake):
    r = client.put("/api/examples/sandbox/containers/demo-one", json={"name": "renamed"})
    assert r.json()["dry_run"] is True
    assert fake._containers[0].calls == []


def test_update_rejects_empty_and_bad_policy(client, fake):
    assert client.put("/api/examples/sandbox/containers/demo-one", json={}).status_code == 400
    bad = client.put("/api/examples/sandbox/containers/demo-one", json={"restart_policy": "sometimes"})
    assert bad.status_code == 400


def test_update_and_delete_refuse_unlabelled_containers(client, fake):
    prod = fake._containers[1]
    assert (
        client.put("/api/examples/sandbox/containers/my-prod-db", json={"name": "x", "dry_run": False}).status_code
        == 403
    )
    assert client.delete("/api/examples/sandbox/containers/my-prod-db?dry_run=false").status_code == 403
    assert prod.calls == [] and prod.removed is False


def test_delete_defaults_to_dry_run_then_removes(client, fake):
    demo = fake._containers[0]
    assert client.delete("/api/examples/sandbox/containers/demo-one").json()["dry_run"] is True
    assert demo.removed is False
    r = client.delete("/api/examples/sandbox/containers/demo-one?dry_run=false")
    assert r.status_code == 200 and r.json()["removed"] == "demo-one"
    assert demo.removed is True


def test_unknown_container_is_404(client, fake):
    assert client.delete("/api/examples/sandbox/containers/ghost?dry_run=false").status_code == 404


def test_create_dry_run_works_without_a_docker_daemon(client, monkeypatch):
    from docker_mcp.web_queries import DockerUnavailable

    def boom():
        raise DockerUnavailable("daemon not running")

    monkeypatch.setattr(ex, "require_client", boom)
    r = client.post("/api/examples/sandbox/containers", json={"name": "demo-two"})
    assert r.status_code == 201
    assert r.json()["dry_run"] is True
    # ...but a real create still needs the daemon
    assert (
        client.post("/api/examples/sandbox/containers", json={"name": "demo-two", "dry_run": False}).status_code == 503
    )


def test_docker_down_is_503_not_500(client, monkeypatch):
    from docker_mcp.web_queries import DockerUnavailable

    def boom():
        raise DockerUnavailable("daemon not running")

    monkeypatch.setattr(ex, "require_client", boom)
    assert client.get("/api/examples/sandbox/containers").status_code == 503
