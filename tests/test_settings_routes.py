from datetime import date

from app.services.app_settings import get_timezone
from app.services.entries import create_entry
from app.services.macros import Macros
from app.services.targets import resolve_targets, set_targets
from tests.conftest import TODAY


def test_settings_page_prefills_current_targets(client, db):
    set_targets(db, date(2026, 10, 1), Macros(2000, 150, 70, 200))
    r = client.get("/settings")
    assert r.status_code == 200
    assert 'value="2000"' in r.text
    assert "America/Chicago" in r.text


def test_save_targets_applies_from_today(client, db):
    r = client.post("/settings/targets", data={"protein": "180", "fat": "80", "carbs": "260", "calories": ""})
    assert r.status_code == 200
    assert "Saved" in r.text
    assert resolve_targets(db, TODAY) == Macros(2480, 180, 80, 260)


def test_saving_targets_keeps_past_day_targets(client, db):
    set_targets(db, date(2026, 10, 1), Macros(2000, 150, 70, 200))
    create_entry(db, day=date(2026, 10, 5), macros=Macros(1000))
    client.post("/settings/targets", data={"protein": "180", "fat": "80", "carbs": "260", "calories": "2500"})
    client.post("/settings/targets", data={"protein": "185", "fat": "80", "carbs": "260", "calories": "2520"})
    assert "/ 2000 kcal" in client.get("/day/2026-10-05").text
    assert "/ 2520 kcal" in client.get("/").text


def test_invalid_targets_422(client, db):
    r = client.post("/settings/targets", data={"protein": "abc"})
    assert r.status_code == 422
    assert "Must be a number" in r.text
    assert resolve_targets(db, TODAY) is None


def test_timezone_save_and_reject(client, db):
    assert client.post("/settings/timezone", data={"timezone": "Europe/London"}).status_code == 200
    assert get_timezone(db, "UTC") == "Europe/London"
    r = client.post("/settings/timezone", data={"timezone": "Mars/Olympus"})
    assert r.status_code == 422
    assert "Unknown timezone" in r.text
