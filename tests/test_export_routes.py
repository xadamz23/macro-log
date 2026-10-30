import io
import zipfile
from datetime import timedelta

from app.services.entries import create_entry
from app.services.macros import Macros
from app.services.profile import ProfileData, save_profile
from tests.conftest import TODAY


def test_export_page(client):
    r = client.get("/export")
    assert r.status_code == 200
    assert 'action="/export/download"' in r.text
    assert 'name="range" value="all" checked' in r.text
    assert "About me" in r.text


def test_export_page_hides_tip_when_profile_set(client, db):
    save_profile(db, ProfileData(goal="lean_bulk"))
    assert "About me" not in client.get("/export").text


def test_menu_links_export(client):
    assert 'href="/export"' in client.get("/").text


def test_download_zip(client, db):
    create_entry(db, day=TODAY - timedelta(days=2), macros=Macros(2000, 150, 70, 200))
    r = client.get("/export/download", params={"range": "90"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"] == 'attachment; filename="macro-log-2026-10-13.zip"'
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = sorted(zf.namelist())
        daily = zf.read("macro-log-2026-10-13/daily.csv").decode()
    assert names == [f"macro-log-2026-10-13/{n}" for n in ("daily.csv", "entries.csv", "prompt.md", "targets.csv")]
    assert len(daily.strip().splitlines()) == 1 + 90


def test_download_invalid_range(client):
    assert client.get("/export/download", params={"range": "7"}).status_code == 422
