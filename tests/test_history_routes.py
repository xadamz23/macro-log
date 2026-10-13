from datetime import date, timedelta

from app.services.entries import create_entry
from app.services.macros import Macros
from app.services.targets import set_targets
from tests.conftest import TODAY


def test_history_page(client, db):
    set_targets(db, date(2026, 10, 1), Macros(2000, 150, 70, 200))
    create_entry(db, day=date(2026, 10, 12), macros=Macros(1800, 140, 60, 180))
    r = client.get("/history")
    assert r.status_code == 200
    assert "7-day avg" in r.text and "1800" in r.text
    assert 'href="/day/2026-10-12"' in r.text
    assert "1800/2000" in r.text
    assert 'x-data="historyCharts(30)"' in r.text


def test_history_empty(client):
    assert "No days logged yet" in client.get("/history").text


def test_history_paging(client, db):
    for i in range(25):
        create_entry(db, day=TODAY - timedelta(days=i + 1), macros=Macros(1000))
    first = client.get("/history").text
    assert first.count('class="day-row"') == 20
    assert 'hx-trigger="revealed"' in first
    oldest_shown = TODAY - timedelta(days=20)
    more = client.get(f"/history/days?before={oldest_shown.isoformat()}").text
    assert more.count('class="day-row"') == 5
    assert 'hx-trigger="revealed"' not in more


def test_history_data(client, db):
    create_entry(db, day=TODAY, macros=Macros(500))
    data = client.get("/history/data?days=14").json()
    assert len(data["labels"]) == 14
    assert data["series"]["calories"][-1] == 500
    assert client.get("/history/data?days=3").status_code == 422
