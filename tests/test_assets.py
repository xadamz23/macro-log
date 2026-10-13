import os
import re

from app import assets as assets_module
from app.assets import AssetHasher, assets


def _write(path, content, mtime_ns):
    path.write_bytes(content)
    os.utime(path, ns=(mtime_ns, mtime_ns))


def test_digest_changes_only_when_content_changes(tmp_path):
    css = tmp_path / "app.css"
    _write(css, b"body{}", 1_000_000_000)
    hasher = AssetHasher(tmp_path)
    first = hasher.digest("app.css")
    assert re.fullmatch(r"[0-9a-f]{10}", first)

    _write(css, b"body{}", 2_000_000_000)          # touched, same bytes
    assert hasher.digest("app.css") == first

    _write(css, b"body{color:red}", 3_000_000_000)  # edited
    assert hasher.digest("app.css") != first


def test_url_includes_digest(tmp_path):
    (tmp_path / "js").mkdir()
    (tmp_path / "js" / "app.js").write_bytes(b"1")
    hasher = AssetHasher(tmp_path)
    assert hasher.url("js/app.js") == f"/static/js/app.js?v={hasher.digest('js/app.js')}"


def test_version_changes_when_any_asset_changes(tmp_path):
    _write(tmp_path / "a.css", b"a", 1_000_000_000)
    _write(tmp_path / "b.js", b"b", 1_000_000_000)
    hasher = AssetHasher(tmp_path)
    before = hasher.version()
    _write(tmp_path / "b.js", b"bb", 2_000_000_000)
    assert hasher.version() != before


def test_pages_reference_hashed_assets(client):
    html = client.get("/").text
    for path in ("css/app.css", "js/app.js", "vendor/htmx.min.js", "vendor/alpine.min.js",
                 "vendor/chart.umd.js", "icons/apple-touch-icon.png"):
        assert f'"{assets.url(path)}"' in html
    assert f'href="/manifest.webmanifest?v={assets.version()}"' in html


def test_matching_version_is_immutable(client):
    r = client.get(assets.url("css/app.css"))
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_missing_or_stale_version_must_revalidate(client):
    assert client.get("/static/css/app.css").headers["cache-control"] == "no-cache"
    assert client.get("/static/css/app.css?v=0000000000").headers["cache-control"] == "no-cache"


def test_not_modified_keeps_cache_header(client):
    url = assets.url("css/app.css")
    etag = client.get(url).headers["etag"]
    r = client.get(url, headers={"If-None-Match": etag})
    assert r.status_code == 304
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_manifest_icons_are_hashed(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/manifest+json")
    assert r.headers["cache-control"] == "no-cache"
    srcs = [icon["src"] for icon in r.json()["icons"]]
    assert srcs == [assets.url("icons/icon-192.png"), assets.url("icons/icon-512.png")]


def test_service_worker_precaches_hashed_urls_and_versions_cache(client, monkeypatch):
    body = client.get("/sw.js").text
    assert f'"{assets.url("css/app.css")}"' in body
    assert f'"{assets.url("vendor/htmx.min.js")}"' in body

    monkeypatch.setattr(assets_module.assets, "version", lambda: "abc123def0")
    assert 'const CACHE = "macro-log-abc123def0";' in client.get("/sw.js").text
