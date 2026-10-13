from datetime import UTC, date, datetime

from app.models import QuickFood
from app.services.entries import (
    create_entry,
    day_totals,
    delete_entry,
    get_entry,
    list_entries,
    log_quick_food,
    update_entry,
)
from app.services.macros import Macros

DAY = date(2026, 10, 13)


def test_create_and_list_in_logged_order(db):
    second = create_entry(db, day=DAY, macros=Macros(200, 10, 5, 20), name="Lunch",
                          now=datetime(2026, 10, 13, 18, tzinfo=UTC))
    first = create_entry(db, day=DAY, macros=Macros(100, 5, 2, 10), name="Breakfast",
                         now=datetime(2026, 10, 13, 13, tzinfo=UTC))
    create_entry(db, day=date(2026, 10, 12), macros=Macros(999))
    assert [e.id for e in list_entries(db, DAY)] == [first.id, second.id]


def test_blank_name_stored_as_none(db):
    assert create_entry(db, day=DAY, macros=Macros(100), name="   ").name is None


def test_day_totals(db):
    assert day_totals(db, DAY) == Macros()
    create_entry(db, day=DAY, macros=Macros(200, 10.5, 5, 20))
    create_entry(db, day=DAY, macros=Macros(300, 20.2, 7, 30))
    assert day_totals(db, DAY) == Macros(500, 30.7, 12, 50)


def test_log_quick_food_scales_and_snapshots(db):
    food = QuickFood(name="Greek yogurt", serving_label="170 g", calories=100, protein=17, fat=0.7, carbs=6, sort_order=0)
    db.add(food)
    db.commit()
    entry = log_quick_food(db, food, day=DAY, servings=2)
    assert entry.macros == Macros(200, 34, 1.4, 12)
    assert (entry.name, entry.servings, entry.quick_food_id) == ("Greek yogurt", 2, food.id)

    food.calories = 999
    db.commit()
    db.expire_all()
    assert get_entry(db, entry.id).calories == 200


def test_update_and_delete(db):
    entry = create_entry(db, day=DAY, macros=Macros(100), name="Snack")
    update_entry(db, entry, name="Apple", macros=Macros(95, 0.5, 0.3, 25))
    db.expire_all()
    fresh = get_entry(db, entry.id)
    assert (fresh.name, fresh.macros) == ("Apple", Macros(95, 0.5, 0.3, 25))
    delete_entry(db, fresh)
    assert get_entry(db, entry.id) is None
