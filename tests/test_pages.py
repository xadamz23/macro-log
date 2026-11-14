from datetime import date

from app.services.entries import create_entry
from app.services.macros import Macros
from app.services.targets import set_targets
from tests.conftest import TODAY


def test_today_without_targets_shows_hint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Today" in r.text
    assert "set your targets" in r.text
    assert 'id="bars"' in r.text


def test_today_shows_progress_against_targets(client, db):
    set_targets(db, TODAY, Macros(2000, 150, 70, 200))
    create_entry(db, day=TODAY, macros=Macros(500, 40, 10, 50), name="Oats")
    r = client.get("/")
    assert "<strong>500</strong> / 2000 kcal" in r.text
    assert "1500 kcal left" in r.text
    assert "Oats" in r.text
    assert "set your targets" not in r.text


def test_over_target_is_marked(client, db):
    set_targets(db, TODAY, Macros(2000, 150, 70, 200))
    create_entry(db, day=TODAY, macros=Macros(2300, 40, 10, 50))
    r = client.get("/")
    assert "300 kcal over" in r.text
    assert "bar-calories over" in r.text


def test_past_day_page_shows_that_day(client, db):
    create_entry(db, day=date(2026, 10, 10), macros=Macros(700), name="Pasta")
    create_entry(db, day=TODAY, macros=Macros(100), name="Apple")
    r = client.get("/day/2026-10-10")
    assert r.status_code == 200
    day_list = r.text.split('id="log-sheet-body"')[0]
    assert "Pasta" in day_list and "Apple" not in day_list
    assert 'href="/day/2026-10-09"' in r.text
    assert 'href="/day/2026-10-11"' in r.text


def test_today_and_future_day_redirect_home(client):
    for path in ("/day/2026-10-13", "/day/2026-12-01"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/"


def test_static_assets_served(client):
    assert client.get("/static/css/app.css").status_code == 200
    assert client.get("/static/vendor/htmx.min.js").status_code == 200


def test_entries_listed_newest_first(client, db):
    from datetime import UTC, datetime

    create_entry(db, day=TODAY, macros=Macros(100), name="Breakfast", now=datetime(2026, 10, 13, 13, tzinfo=UTC))
    create_entry(db, day=TODAY, macros=Macros(100), name="Dinner", now=datetime(2026, 10, 14, 0, tzinfo=UTC))
    create_entry(db, day=TODAY, macros=Macros(100), name="Lunch", now=datetime(2026, 10, 13, 18, tzinfo=UTC))
    html = client.get("/").text
    assert html.index("Dinner") < html.index("Lunch") < html.index("Breakfast")


def test_day_header_has_date_jump(client):
    r = client.get("/")
    assert 'class="date-jump"' in r.text
    assert 'max="2026-10-13"' in r.text and 'value="2026-10-13"' in r.text
    r = client.get("/day/2026-10-01")
    assert 'value="2026-10-01"' in r.text and 'max="2026-10-13"' in r.text


def test_bottom_nav_has_weight_and_menu_has_settings(client):
    html = client.get("/").text
    bottom_nav = html.split('class="bottom-nav')[1]
    assert 'href="/weight"' in bottom_nav and 'href="/settings"' not in bottom_nav
    assert 'class="menu-wrap"' in html and 'href="/settings"' in html
    for path in ("/history", "/settings", "/settings/foods", "/weight"):
        assert 'class="menu-wrap"' in client.get(path).text


def test_today_nudges_until_weighed(client, db):
    from app.services.weight import save_weigh_in

    assert "No weigh-in yet today" in client.get("/").text
    assert "No weigh-in yet today" not in client.get("/day/2026-10-10").text
    save_weigh_in(db, TODAY, 180)
    assert "No weigh-in yet today" not in client.get("/").text


def test_desktop_sidebar_marks_current_page(client):
    r = client.get("/weight")
    assert 'class="side glass-strong desktop-only"' in r.text
    assert '<a href="/weight" class="side-link" aria-current="page">' in r.text
    assert 'href="/?log=1" class="btn accent log-cta"' in r.text
    # On Today the sidebar button opens the sheet in place instead.
    assert "$dispatch('open-log')\">" in client.get("/").text.split('class="btn accent log-cta"')[1][:40]


def test_day_page_week_strip_and_entry_totals(client, db):
    from datetime import timedelta

    set_targets(db, TODAY - timedelta(days=30), Macros(2000, 150, 70, 200))
    create_entry(db, day=TODAY, macros=Macros(500, 40, 10, 50), name="Oats")
    create_entry(db, day=TODAY, macros=Macros(1200, 60, 30, 100), name="Lunch")
    r = client.get("/")
    assert 'id="week-strip"' in r.text
    assert r.text.count('class="wk-day') == 7
    assert 'aria-current="date"' in r.text
    assert '<span class="ec-kcal">1,700</span>' in r.text  # desktop total row


def test_day_page_desktop_cards_stepper_and_share(client, db):
    from datetime import timedelta

    set_targets(db, TODAY - timedelta(days=30), Macros(2000, 150, 70, 200))
    create_entry(db, day=TODAY, macros=Macros(500, 40.5, 10, 50), name="Oats")
    r = client.get("/")
    kpis = r.text.split('id="day-kpis"')[1].split("</div>\n</div>")[0]
    assert kpis.count('class="card glass kpi') == 4
    assert '<span class="kpi-num">500</span> <small>/ 2,000 kcal</small>' in kpis
    assert '<span class="kpi-num">40.5</span>' in kpis
    assert "<strong>1,500 kcal</strong> left · 25%" in kpis
    # Today's pill is current and there is no next day.
    step = r.text.split('class="segmented glass day-step"')[1].split("</nav>")[0]
    assert 'class="accent" aria-current="date">Today' in step
    assert 'class="is-disabled"' in step
    assert 'class="card glass entries has-kcal-target" style="--kcal-target: 2000"' in r.text
    assert 'style="--kcal: 500"' in r.text


def test_past_day_stepper_links_forward(client, db):
    from datetime import timedelta

    r = client.get(f"/day/{(TODAY - timedelta(days=1)).isoformat()}")
    step = r.text.split('class="segmented glass day-step"')[1].split("</nav>")[0]
    assert 'aria-current="date">Today' not in step
    assert '<a href="/" aria-label="Next day">' in step
    assert "has-kcal-target" not in r.text  # no targets, no share bars
