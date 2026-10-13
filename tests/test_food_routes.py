from app.services.entries import get_entry, log_quick_food
from app.services.foods import create_quick_food, list_quick_foods
from app.services.macros import Macros
from tests.conftest import TODAY


def _food(db, name):
    return create_quick_food(db, name=name, serving_label="", macros=Macros(100, 10, 1, 10))


def test_foods_page(client, db):
    _food(db, "Eggs")
    r = client.get("/settings/foods")
    assert r.status_code == 200 and "Eggs" in r.text and 'id="food-add"' in r.text


def test_add_food(client, db):
    r = client.post("/quick-foods", data={"name": "Oats", "serving_label": "40 g", "protein": "5", "fat": "3", "carbs": "27", "calories": ""})
    assert r.status_code == 200
    assert 'id="food-list" class="card" hx-swap-oob="true"' in r.text
    [food] = list_quick_foods(db)
    assert (food.name, food.serving_label, food.calories) == ("Oats", "40 g", 155)


def test_add_food_requires_name(client, db):
    r = client.post("/quick-foods", data={"protein": "5"})
    assert r.status_code == 422
    assert "Required" in r.text
    assert list_quick_foods(db) == []


def test_edit_food(client, db):
    food = _food(db, "Eggs")
    assert client.get(f"/quick-foods/{food.id}/edit").status_code == 200
    r = client.put(f"/quick-foods/{food.id}", data={"name": "2 eggs", "serving_label": "2 large", "protein": "12", "fat": "10", "carbs": "1", "calories": "140"})
    assert r.status_code == 200 and "2 eggs" in r.text
    bad = client.put(f"/quick-foods/{food.id}", data={"name": "", "protein": "1"})
    assert bad.status_code == 422
    assert bad.headers["HX-Retarget"] == f"#food-{food.id}"


def test_delete_food_route_keeps_history(client, db):
    food = _food(db, "Eggs")
    entry = log_quick_food(db, food, day=TODAY)
    r = client.delete(f"/quick-foods/{food.id}")
    assert r.status_code == 200
    db.expire_all()
    assert list_quick_foods(db) == []
    kept = get_entry(db, entry.id)
    assert (kept.name, kept.calories) == ("Eggs", 100)


def test_unknown_food_404(client):
    assert client.delete("/quick-foods/999").status_code == 404
