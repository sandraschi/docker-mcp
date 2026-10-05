"""Backend for the webapp Examples page.

Two things live here:

* ``/api/examples`` - list, read and run the scripts in the repo's ``examples/`` directory.
  Only plain ``name.py`` files that exist in that directory can be run (allow-list, no paths).
* ``/api/examples/sandbox/containers`` - a create / read / update / delete demo on containers
  carrying the ``docker-mcp.example=1`` label. update and delete refuse any container without
  that label, so the demo can never touch your real containers.

Every mutating call takes ``dry_run`` (default **true**): it returns the steps it would take and
never talks to Docker. The web UI exposes this as a switch that defaults to on.
"""

from __future__ import annotations

import ast
import asyncio
import os
import re
import subprocess  # nosec B404 - runs allow-listed repo scripts only, argv list, no shell
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from docker.errors import ImageNotFound, NotFound
from fastapi import Body, FastAPI, HTTPException, Query, Request

from .web_queries import require_client

EXAMPLE_LABEL = "docker-mcp.example"
EXAMPLES_DIR = Path(os.environ.get("DOCKER_MCP_EXAMPLES_DIR") or Path(__file__).resolve().parents[2] / "examples")
RUN_TIMEOUT_S = 120
MAX_OUTPUT_CHARS = 64_000

_EXAMPLE_NAME = re.compile(r"^[a-z0-9_]+\.py$")
_CONTAINER_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$")
_RESTART_POLICIES = ("no", "on-failure", "unless-stopped", "always")
_running: set[str] = set()


# --- examples/ scripts --------------------------------------------------------


def list_examples(directory: Path | None = None) -> list[dict[str, Any]]:
    directory = directory or EXAMPLES_DIR
    rows: list[dict[str, Any]] = []
    if not directory.is_dir():
        return rows
    for path in sorted(directory.glob("*.py")):
        if not _EXAMPLE_NAME.match(path.name):
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        doc = _docstring(source)
        first, _, rest = doc.partition("\n")
        rows.append(
            {
                "name": path.name,
                "title": first.strip() or path.stem.replace("_", " ").title(),
                "description": rest.strip(),
                "lines": source.count("\n") + 1,
                "size": path.stat().st_size,
            }
        )
    return rows


def _docstring(source: str) -> str:
    try:
        return ast.get_docstring(ast.parse(source)) or ""
    except SyntaxError:
        return ""


def _example_path(name: str, directory: Path | None = None) -> Path:
    path = (directory or EXAMPLES_DIR) / name
    if not _EXAMPLE_NAME.match(name) or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Unknown example: {name}")
    return path


def run_example(path: Path, *, dry_run: bool, mcp_url: str, timeout: int = RUN_TIMEOUT_S) -> dict[str, Any]:
    """Run one example script in a subprocess and return its captured output."""
    env = {
        **os.environ,
        "DOCKER_MCP_URL": mcp_url,
        "DOCKER_MCP_EXAMPLE_DRY_RUN": "1" if dry_run else "0",
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    started = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(  # nosec B603 - argv list, path validated against the examples allow-list
            [sys.executable, "-u", str(path)],
            cwd=str(path.parent.parent),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        stdout = _as_text(exc.stdout)
        stderr = _as_text(exc.stderr) + f"\n[timed out after {timeout}s]"
    truncated = len(stdout) > MAX_OUTPUT_CHARS or len(stderr) > MAX_OUTPUT_CHARS
    return {
        "name": path.name,
        "dry_run": dry_run,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_s": round(time.monotonic() - started, 2),
        "stdout": stdout[:MAX_OUTPUT_CHARS],
        "stderr": stderr[:MAX_OUTPUT_CHARS],
        "truncated": truncated,
    }


def _as_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


# --- labelled-sandbox container CRUD -------------------------------------------


def container_view(container: Any) -> dict[str, Any]:
    attrs = container.attrs or {}
    config = attrs.get("Config") or {}
    host = attrs.get("HostConfig") or {}
    tags = list(getattr(container.image, "tags", None) or [])
    return {
        "id": container.id[:12],
        "name": container.name.lstrip("/"),
        "image": tags[0] if tags else config.get("Image", ""),
        "state": container.status,
        "created": attrs.get("Created", ""),
        "restart_policy": (host.get("RestartPolicy") or {}).get("Name") or "no",
        "labels": container.labels or {},
    }


def _get_container(client: Any, container_id: str) -> Any:
    # NotFound subclasses APIError; translate here so the 404 never depends on except-clause order upstream
    try:
        return client.containers.get(container_id)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=getattr(exc, "explanation", None) or str(exc)) from exc


def _require_example(container: Any) -> None:
    if (container.labels or {}).get(EXAMPLE_LABEL) != "1":
        raise HTTPException(
            status_code=403,
            detail=f"Refusing: {container.name.lstrip('/')} is not an example container ({EXAMPLE_LABEL}=1)",
        )


def _check_name(name: str) -> str:
    if not _CONTAINER_NAME.match(name or ""):
        raise ValueError("name must start with a letter or digit and use only letters, digits, '_', '.', '-'")
    return name


def sandbox_list(client: Any) -> dict[str, Any]:
    containers = client.containers.list(all=True, filters={"label": f"{EXAMPLE_LABEL}=1"})
    rows = [container_view(c) for c in containers]
    return {"status": "success", "containers": rows, "count": len(rows), "label": f"{EXAMPLE_LABEL}=1"}


def sandbox_create(client: Any, *, name: str, image: str, command: str, dry_run: bool) -> dict[str, Any]:
    _check_name(name)
    if not image.strip():
        raise ValueError("image is required")
    steps = [
        f"ensure image {image} is present (pull if missing)",
        f"run detached container {name!r}: {command or '<image default>'}",
        f"label it {EXAMPLE_LABEL}=1",
    ]
    if dry_run:
        return {"status": "dry_run", "dry_run": True, "would": steps}
    try:
        client.images.get(image)
    except ImageNotFound:
        repo, _, tag = image.partition(":")
        client.images.pull(repo, tag=tag or "latest")
    container = client.containers.run(
        image,
        command or None,
        name=name,
        detach=True,
        labels={EXAMPLE_LABEL: "1"},
    )
    container.reload()
    return {"status": "success", "dry_run": False, "container": container_view(container)}


def sandbox_update(
    client: Any, container_id: str, *, name: str | None, restart_policy: str | None, dry_run: bool
) -> dict[str, Any]:
    if name is None and restart_policy is None:
        raise ValueError("nothing to update: pass name and/or restart_policy")
    if name is not None:
        _check_name(name)
    if restart_policy is not None and restart_policy not in _RESTART_POLICIES:
        raise ValueError(f"restart_policy must be one of {', '.join(_RESTART_POLICIES)}")
    container = _get_container(client, container_id)
    _require_example(container)
    steps = []
    if name is not None:
        steps.append(f"rename {container.name.lstrip('/')!r} -> {name!r}")
    if restart_policy is not None:
        steps.append(f"set restart policy to {restart_policy!r}")
    if dry_run:
        return {"status": "dry_run", "dry_run": True, "would": steps}
    if name is not None:
        container.rename(name)
    if restart_policy is not None:
        container.update(restart_policy={"Name": restart_policy})
    container.reload()
    return {"status": "success", "dry_run": False, "container": container_view(container)}


def sandbox_delete(client: Any, container_id: str, *, dry_run: bool) -> dict[str, Any]:
    container = _get_container(client, container_id)
    _require_example(container)
    name = container.name.lstrip("/")
    if dry_run:
        return {"status": "dry_run", "dry_run": True, "would": [f"force-remove container {name!r}"]}
    container.remove(force=True)
    return {"status": "success", "dry_run": False, "removed": name}


# --- routes -----------------------------------------------------------------------


def register_examples_routes(app: FastAPI, in_thread: Callable[..., Awaitable[Any]]) -> None:
    """Attach the Examples endpoints. ``in_thread`` maps docker errors to HTTP statuses."""

    @app.get("/api/examples")
    async def api_examples():
        rows = await asyncio.to_thread(list_examples)
        return {"examples": rows, "count": len(rows), "directory": str(EXAMPLES_DIR), "timeout_s": RUN_TIMEOUT_S}

    @app.get("/api/examples/sandbox/containers")
    async def api_sandbox_list():
        return await in_thread(lambda: sandbox_list(require_client()))

    @app.post("/api/examples/sandbox/containers", status_code=201)
    async def api_sandbox_create(payload: dict = Body(default_factory=dict)):
        return await in_thread(
            lambda: sandbox_create(
                require_client(),
                name=str(payload.get("name", "")),
                image=str(payload.get("image") or "alpine:latest"),
                command=str(payload.get("command") if payload.get("command") is not None else "sleep 3600"),
                dry_run=bool(payload.get("dry_run", True)),
            )
        )

    @app.put("/api/examples/sandbox/containers/{container_id}")
    async def api_sandbox_update(container_id: str, payload: dict = Body(default_factory=dict)):
        return await in_thread(
            lambda: sandbox_update(
                require_client(),
                container_id,
                name=payload.get("name"),
                restart_policy=payload.get("restart_policy"),
                dry_run=bool(payload.get("dry_run", True)),
            )
        )

    @app.delete("/api/examples/sandbox/containers/{container_id}")
    async def api_sandbox_delete(container_id: str, dry_run: bool = Query(True)):
        return await in_thread(lambda: sandbox_delete(require_client(), container_id, dry_run=dry_run))

    @app.get("/api/examples/{name}/source")
    async def api_example_source(name: str):
        path = _example_path(name)
        source = await asyncio.to_thread(path.read_text, "utf-8", "replace")
        return {"name": name, "source": source, "docstring": _docstring(source)}

    @app.post("/api/examples/{name}/run")
    async def api_example_run(name: str, request: Request, payload: dict = Body(default_factory=dict)):
        path = _example_path(name)
        if name in _running:
            raise HTTPException(status_code=409, detail=f"{name} is already running")
        dry_run = bool(payload.get("dry_run", True))
        port = request.url.port or 80
        mcp_url = f"http://127.0.0.1:{port}/mcp"
        _running.add(name)
        try:
            return await asyncio.to_thread(run_example, path, dry_run=dry_run, mcp_url=mcp_url)
        finally:
            _running.discard(name)
