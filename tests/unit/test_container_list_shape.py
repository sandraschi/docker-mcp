from dockermcp.tools.containers.list_containers import created_iso, format_ports


def test_format_ports_list_api_shape():
    attrs = {
        "Ports": [
            {"IP": "127.0.0.1", "PrivatePort": 80, "PublicPort": 8080, "Type": "tcp"},
            {"PrivatePort": 443, "Type": "tcp"},
        ]
    }
    ports = format_ports(attrs)
    assert "127.0.0.1:8080->80/tcp" in ports
    assert "443/tcp" in ports


def test_format_ports_inspect_shape():
    attrs = {
        "NetworkSettings": {
            "Ports": {
                "80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}],
                "443/tcp": None,
            }
        }
    }
    ports = format_ports(attrs)
    assert "127.0.0.1:8080->80/tcp" in ports
    assert "443/tcp" in ports


def test_created_iso_from_unix():
    stamp = created_iso(0)
    assert stamp.startswith("1970-01-01")


def test_created_iso_passthrough():
    assert created_iso("2024-01-02T03:04:05Z") == "2024-01-02T03:04:05Z"
    assert created_iso(None) == ""
