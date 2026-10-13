import re
from datetime import timedelta

import pytest

from app.config import Settings
from app.deps import get_today
from app.forms import parse_macro_form
from app.main import create_app
from app.services.entries import list_entries
from app.services.targets import resolve_targets
from tests.conftest import TODAY


def test_today_sheet_posts_still_land_on_new_day_after_midnight(app, client, db):
    """An open Today page must not keep logging to the day it was rendered on."""
    assert 'data-url="/log-sheet?day="' in client.get("/").text
    sheet = client.get("/log-sheet?day=").text
    posted_day = re.search(r'name="day" value="([^"]*)"', sheet).group(1)

    tomorrow = TODAY + timedelta(days=1)
    app.dependency_overrides[get_today] = lambda: tomorrow
    client.post("/entries", data={"day": posted_day, "protein": "10"})
    assert len(list_entries(db, tomorrow)) == 1
    assert list_entries(db, TODAY) == []


def test_past_day_sheet_keeps_explicit_day(client):
    assert 'data-url="/log-sheet?day=2026-10-10"' in client.get("/day/2026-10-10").text
    assert 'name="day" value="2026-10-10"' in client.get("/log-sheet?day=2026-10-10").text


def test_csrf_trusts_sec_fetch_site_over_rewritten_host(client):
    headers = {"Sec-Fetch-Site": "same-origin", "Origin": "https://macros.example.com"}
    assert client.post("/entries", data={"protein": "10"}, headers=headers).status_code == 200


def test_targets_require_protein_fat_carbs(client, db):
    r = client.post("/settings/targets", data={"protein": "150", "fat": "", "carbs": "", "calories": "2000"})
    assert r.status_code == 422
    assert "Required" in r.text
    assert resolve_targets(db, TODAY) is None


@pytest.mark.parametrize("raw", ["1,500", "12,500", "1,2,3"])
def test_thousands_separator_comma_rejected(raw):
    form = parse_macro_form({"protein": "1", "fat": "1", "carbs": "1", "calories": raw})
    assert "calories" in form.errors


def test_half_configured_access_fails_fast(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'x.db'}",
                        cf_access_team_domain="team.cloudflareaccess.com", cf_access_aud=None)
    with pytest.raises(ValueError, match="CF_ACCESS"):
        create_app(settings)
