from datetime import date

from sqlalchemy import func, select

from app.deps import get_macro_estimator
from app.models import Entry, QuickFood
from app.services.entries import create_entry, list_entries
from app.services.foods import create_quick_food
from app.services.macros import Macros
from tests.conftest import TODAY


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_create_entry_autofills_calories_and_returns_oob(client, db):
    r = client.post("/entries", data={"day": TODAY.isoformat(), "name": "Oats", "protein": "10", "fat": "5", "carbs": "40", "calories": ""})
    assert r.status_code == 200
    assert r.headers["HX-Trigger"] == "entry-logged"
    assert 'id="bars" class="card glass bars" hx-swap-oob="true"' in r.text
    assert 'id="entries" class="card glass entries" hx-swap-oob="true"' in r.text
    assert "Undo" in r.text
    [entry] = list_entries(db, TODAY)
    assert (entry.name, entry.calories) == ("Oats", 245)


def test_create_entry_invalid_returns_422_and_saves_nothing(client, db):
    r = client.post("/entries", data={"day": TODAY.isoformat(), "protein": "-3", "fat": "abc", "carbs": "1", "calories": ""})
    assert r.status_code == 422
    assert r.headers["HX-Retarget"] == "#entry-form"
    assert r.headers["HX-Reswap"] == "outerHTML"
    assert 'id="entry-form"' in r.text
    assert "Must be between 0 and 2000" in r.text
    assert "Must be a number" in r.text
    assert _count(db, Entry) == 0


def test_comma_decimal_from_phone_keyboard(client, db):
    client.post("/entries", data={"day": TODAY.isoformat(), "protein": "12,5", "fat": "", "carbs": "", "calories": ""})
    assert list_entries(db, TODAY)[0].protein == 12.5


def test_save_as_quick_food(client, db):
    client.post("/entries", data={"day": TODAY.isoformat(), "name": "Shake", "protein": "30", "fat": "2", "carbs": "5",
                                  "calories": "160", "save_quick": "on", "serving_label": "1 scoop"})
    food = db.scalar(select(QuickFood))
    assert (food.name, food.serving_label, food.calories) == ("Shake", "1 scoop", 160)
    assert list_entries(db, TODAY)[0].quick_food_id == food.id


def test_save_as_quick_food_requires_name(client, db):
    r = client.post("/entries", data={"day": TODAY.isoformat(), "protein": "30", "save_quick": "on"})
    assert r.status_code == 422
    assert "Name is required" in r.text
    assert _count(db, QuickFood) == 0


def test_future_day_is_clamped_to_today(client, db):
    client.post("/entries", data={"day": "2027-01-01", "protein": "10"})
    assert len(list_entries(db, TODAY)) == 1


def test_backfill_past_day(client, db):
    client.post("/entries", data={"day": "2026-10-10", "protein": "10"})
    assert len(list_entries(db, date(2026, 10, 10))) == 1


def test_log_quick_food_with_servings(client, db):
    food = create_quick_food(db, name="Yogurt", serving_label="170 g", macros=Macros(100, 17, 0.5, 6))
    r = client.post(f"/quick-foods/{food.id}/log", data={"day": TODAY.isoformat(), "servings": "2"})
    assert r.status_code == 200
    assert r.headers["HX-Trigger"] == "entry-logged"
    entry = list_entries(db, TODAY)[0]
    assert (entry.calories, entry.servings) == (200, 2)


def test_log_quick_food_errors(client, db):
    assert client.post("/quick-foods/999/log", data={"day": TODAY.isoformat()}).status_code == 404
    food = create_quick_food(db, name="Yogurt", serving_label="", macros=Macros(100))
    assert client.post(f"/quick-foods/{food.id}/log", data={"servings": "abc"}).status_code == 422


def test_log_sheet_lists_quick_foods_not_recent(client, db):
    create_quick_food(db, name="Yogurt", serving_label="", macros=Macros(100))
    create_entry(db, day=TODAY, macros=Macros(300, 30, 10, 20), name="Chicken bowl")
    r = client.get("/")
    assert r.status_code == 200
    assert "Yogurt" in _sheet(r.text) and "Chicken bowl" not in _sheet(r.text)
    assert '<div class="section-label">Recent</div>' not in r.text
    assert 'id="entry-form"' in r.text
    assert "Save as quick food" in r.text


def test_hide_recent_food_route(client, db):
    create_entry(db, day=TODAY, macros=Macros(300, 30, 10, 20), name="Chicken bowl")
    create_entry(db, day=TODAY, macros=Macros(150, 5, 5, 20), name="Granola bar")
    r = client.post("/recent-foods/hide", data={"day": TODAY.isoformat(), "name": "Chicken bowl",
                                                "calories": "300", "protein": "30.0", "fat": "10.0", "carbs": "20.0"})
    assert r.status_code == 200
    assert 'id="recent-foods"' in r.text
    assert "Granola bar" in r.text and "Chicken bowl" not in r.text
    assert f'"day": "{TODAY.isoformat()}"' in r.text
    assert client.post("/recent-foods/hide", data={"name": "", "calories": "300"}).status_code == 422


def test_log_sheet_orders_quick_foods_by_recent_use(client, db):
    create_quick_food(db, name="Apple", serving_label="", macros=Macros(100))
    yogurt = create_quick_food(db, name="Yogurt", serving_label="", macros=Macros(100))
    client.post(f"/quick-foods/{yogurt.id}/log", data={"day": TODAY.isoformat(), "servings": "1"})
    sheet = _sheet(client.get("/").text)
    assert sheet.index("Yogurt") < sheet.index("Apple")


def test_edit_update_delete_entry(client, db):
    entry = create_entry(db, day=TODAY, macros=Macros(100, 5, 5, 5), name="Snack")
    edit = client.get(f"/entries/{entry.id}/edit")
    assert edit.status_code == 200 and 'hx-put="/entries/' in edit.text

    r = client.put(f"/entries/{entry.id}", data={"name": "Apple", "protein": "0.5", "fat": "0.3", "carbs": "25", "calories": "95"})
    assert r.status_code == 200 and 'hx-swap-oob="true"' in r.text
    db.expire_all()
    assert list_entries(db, TODAY)[0].name == "Apple"

    bad = client.put(f"/entries/{entry.id}", data={"protein": "x"})
    assert bad.status_code == 422
    assert bad.headers["HX-Retarget"] == f"#entry-{entry.id}"

    assert client.get(f"/entries/{entry.id}/row").status_code == 200
    assert client.delete(f"/entries/{entry.id}").status_code == 200
    assert client.delete(f"/entries/{entry.id}").status_code == 404
    assert list_entries(db, TODAY) == []


def test_today_page_has_sheet(client):
    r = client.get("/?log=1")
    assert 'x-data="logSheet(true)"' in r.text
    assert 'id="log-sheet-body"' in r.text and 'id="entry-form"' in r.text


def test_closing_sheet_ignores_taps(client):
    """The sheet stays on screen while it slides away; inert keeps a tap then from logging again."""
    assert ':inert="!open"' in client.get("/").text


def test_entry_form_drops_a_second_submit(client):
    guard = 'hx-sync="this:drop"'
    disable = "hx-disabled-elt=\"find button[type='submit']\""
    page = client.get("/").text
    # Both the live form and the blank copy show() swaps in.
    assert page.count(guard) >= 2 and page.count(disable) >= 2
    r = client.post("/entries", data={"calories": "abc"})
    assert r.status_code == 422
    assert guard in r.text and disable in r.text


def test_log_sheet_search_filters_tiles_by_name(client, db):
    create_quick_food(db, name="Greek Yogurt", serving_label="", macros=Macros(100))
    r = client.get("/")
    assert 'type="search"' in r.text
    assert 'data-name="greek yogurt"' in r.text


def test_log_sheet_without_foods_has_no_search(client):
    r = client.get("/")
    assert 'type="search"' not in r.text


def test_log_sheet_offers_logging_with_claude(app, client):
    app.dependency_overrides[get_macro_estimator] = lambda: object()
    r = client.get("/")
    assert 'x-data="claudeLog" @open-log.window="reset()"' in r.text
    assert "Log with Claude" in r.text
    assert r.text.count('hx-post="/entries/estimate"') == 2
    assert 'capture="environment"' in r.text and "Choose a photo" in r.text
    assert 'id="claude-what"' in r.text and "Describe" in r.text
    assert 'id="entry-form"' in r.text


def test_both_claude_fields_can_be_dictated(app, client):
    app.dependency_overrides[get_macro_estimator] = lambda: object()
    r = client.get("/")
    assert r.text.count('@click="dictate()"') == 2  # Describe box and the photo's "What is it?"
    assert r.text.count('class="listen-badge"') == 2


def _sheet(html):
    """The log sheet's contents, so an entry on the day's list doesn't count as a tile."""
    return html.split('id="log-sheet-body"')[1]


def test_opening_the_sheet_needs_no_route(client):
    assert client.get("/log-sheet").status_code == 404


def test_past_day_page_sheet_logs_to_that_day(client):
    assert 'name="day" value="2026-10-10"' in _sheet(client.get("/day/2026-10-10").text)


def test_create_response_updates_the_sheet(client, db):
    r = client.post("/entries", data={"name": "Chicken bowl", "calories": "300", "save_quick": "on"})
    assert 'id="log-sheet-body" hx-swap-oob="innerHTML"' in r.text
    assert 'class="qf-name">Chicken bowl' in _sheet(r.text)
    assert 'name="day" value=""' in _sheet(r.text)


def test_quick_food_log_response_reorders_the_sheet(client, db):
    create_quick_food(db, name="Apple", serving_label="", macros=Macros(100))
    yogurt = create_quick_food(db, name="Yogurt", serving_label="", macros=Macros(100))
    r = client.post(f"/quick-foods/{yogurt.id}/log", data={"day": "", "servings": "1"})
    sheet = _sheet(r.text)
    assert sheet.index("Yogurt") < sheet.index("Apple")


def test_past_day_edit_response_keeps_the_sheet_on_that_day(client, db):
    entry = create_entry(db, day=date(2026, 10, 10), macros=Macros(100), name="Snack")
    r = client.put(f"/entries/{entry.id}", data={"name": "Toast", "calories": "100"})
    assert 'name="day" value="2026-10-10"' in _sheet(r.text)


def test_write_response_honors_photo_setting(app, client):
    r = client.post("/entries", data={"calories": "100"})
    assert "Log with Claude" not in _sheet(r.text)
    app.dependency_overrides[get_macro_estimator] = lambda: object()
    r = client.post("/entries", data={"calories": "100"})
    assert "Log with Claude" in _sheet(r.text)
