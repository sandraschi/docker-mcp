"""Prefab-UI card builders for docker-mcp (fleet list/status/stats)."""

from __future__ import annotations

from prefab_ui.components import Badge, Card, Metric, Row


def build_containers_card(result: dict) -> Card:
    """Visual card for container inventory."""
    containers = result.get("containers") or result.get("data", {}).get("containers") or []
    if isinstance(result.get("data"), dict):
        containers = result["data"].get("containers", containers)

    rows = []
    for item in containers[:12]:
        rows.append(
            Row(
                children=[
                    Metric(label="Name", value=str(item.get("name", "—"))[:40]),
                    Metric(label="State", value=str(item.get("state", item.get("status", "—")))),
                    Metric(label="Image", value=str(item.get("image", "—"))[:36]),
                ]
            )
        )
    running = sum(1 for c in containers if str(c.get("state", c.get("status", ""))).lower() == "running")
    return Card(
        children=rows or [Metric(label="Containers", value="0")],
        title="Docker Containers",
        badges=[
            Badge(label=f"{len(containers)} total"),
            Badge(label=f"{running} running"),
        ],
    )


def build_desktop_status_card(result: dict) -> Card:
    """Visual card for Docker Desktop / daemon health."""
    data = result if isinstance(result, dict) else {}
    healthy = data.get("healthy", data.get("daemon_responsive", True))
    rows = [
        Row(
            children=[
                Metric(label="Daemon", value="OK" if healthy else "Degraded"),
                Metric(
                    label="Containers",
                    value=str(len(data.get("recent_containers", data.get("containers", [])))),
                ),
                Metric(
                    label="Images",
                    value=str(len(data.get("recent_images", data.get("images", [])))),
                ),
            ]
        )
    ]
    return Card(
        children=rows,
        title="Docker Desktop Status",
        badges=[Badge(label="Healthy" if healthy else "Check daemon")],
    )


def build_images_card(result: dict, limit: int = 12) -> Card:
    """Visual card for image inventory."""
    images = result.get("images") or result.get("data", {}).get("images") or []
    if isinstance(result.get("data"), dict):
        images = result["data"].get("images", images)

    rows = []
    for item in images[:limit]:
        tags = item.get("repo_tags") or item.get("RepoTags") or []
        tag_str = tags[0] if tags else item.get("id", "—")[:19]
        size = item.get("size", item.get("Size", 0))
        size_str = f"{size / 1024 / 1024:.0f}MB" if size > 0 else "—"
        rows.append(
            Row(
                children=[
                    Metric(label="Image", value=str(tag_str)[:48]),
                    Metric(label="Size", value=size_str),
                    Metric(label="ID", value=str(item.get("id", "—"))[:19]),
                ]
            )
        )
    return Card(
        children=rows or [Metric(label="Images", value="0")],
        title="Docker Images",
        badges=[Badge(label=f"{len(images)} total"), Badge(label=f"{sum(1 for i in images if i.get('repo_tags', i.get('RepoTags', [])))} tagged")],
    )


def build_system_info_card(result: dict) -> Card:
    """Visual card for engine system info."""
    info = result.get("system_info") or result.get("data", {}).get("system_info") or result
    mem = info.get("memory", {}) if isinstance(info, dict) else {}
    cpu = info.get("cpu", {}) if isinstance(info, dict) else {}
    rows = [
        Row(
            children=[
                Metric(label="Docker", value=str(info.get("docker_version", "—"))),
                Metric(label="CPUs", value=str(cpu.get("cores", info.get("NCPU", "—")))),
                Metric(
                    label="Memory",
                    value=str(mem.get("total_formatted", mem.get("total", "—"))),
                ),
            ]
        )
    ]
    return Card(children=rows, title="Docker Engine", badges=[Badge(label="System")])
