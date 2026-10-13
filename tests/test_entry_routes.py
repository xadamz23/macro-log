from datetime import date

from sqlalchemy import func, select

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
    assert 'id="bars" class="card bars" hx-swap-oob="true"' in r.text
    assert 'id="entries" class="card entries" hx-swap-oob="true"' in r.text
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


def test_log_sheet_lists_quick_and_recent(client, db):
    create_quick_food(db, name="Yogurt", serving_label="", macros=Macros(100))
    create_entry(db, day=TODAY, macros=Macros(300, 30, 10, 20), name="Chicken bowl")
    r = client.get(f"/log-sheet?day={TODAY.isoformat()}")
    assert r.status_code == 200
    assert "Yogurt" in r.text and "Chicken bowl" in r.text
    assert 'id="entry-form"' in r.text
    assert "Save as quick food" in r.text


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
    assert 'data-url="/log-sheet?day=2026-10-13"' in r.text
