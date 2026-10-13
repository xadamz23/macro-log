import struct
from pathlib import Path

ICONS = Path("app/static/icons")


def test_manifest(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/manifest+json")
    data = r.json()
    assert data["display"] == "standalone" and data["start_url"] == "/"


def test_service_worker_served_at_root(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    assert r.headers["cache-control"] == "no-cache"


def test_base_links_manifest_with_credentials(client):
    html = client.get("/").text
    assert 'rel="manifest" href="/manifest.webmanifest?v=' in html
    assert 'crossorigin="use-credentials"' in html


def test_icons_are_pngs_of_right_size():
    for name, size in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        data = (ICONS / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", data[16:24]) == (size, size)
