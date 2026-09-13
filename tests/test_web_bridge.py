"""Smoke tests for FastAPI web bridge (fleet /logs + health)."""

from fastapi.testclient import TestClient

from server import web_app


def test_health():
    client = TestClient(web_app)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["service"] == "docker-mcp"


def test_logs_endpoints():
    client = TestClient(web_app)
    r = client.get("/api/logs", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    assert "total" in body


def test_capabilities_pages():
    client = TestClient(web_app)
    r = client.get("/api/capabilities")
    assert r.status_code == 200
    pages = r.json()["pages"]
    for key in ("volumes", "networks", "compose", "images", "containers"):
        assert pages[key] is True


def test_tools_are_named_objects():
    client = TestClient(web_app)
    r = client.get("/api/tools")
    assert r.status_code == 200
    body = r.json()
    assert "count" in body
    assert isinstance(body["tools"], list)
    if body["tools"]:
        assert "name" in body["tools"][0]
        assert "parameters" in body["tools"][0]


def test_tool_get_and_invoke_status():
    client = TestClient(web_app)
    detail = client.get("/api/tools/get_docker_status_tool")
    assert detail.status_code == 200
    assert detail.json()["tool"]["name"] == "get_docker_status_tool"
    invoked = client.post("/api/tools/get_docker_status_tool", json={"arguments": {}})
    assert invoked.status_code == 200
    body = invoked.json()
    assert body["success"] is True
    assert "result" in body


def test_diagnostics_registered():
    client = TestClient(web_app)
    r = client.get("/api/v1/diagnostics")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "docker" in body
    assert isinstance(body["tools"]["total"], int)
