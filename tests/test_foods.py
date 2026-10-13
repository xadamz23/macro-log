from datetime import UTC, date, datetime, timedelta

from app.services.entries import create_entry, get_entry, log_quick_food
from app.services.foods import (
    create_quick_food,
    delete_quick_food,
    list_quick_foods,
    list_quick_foods_by_recent_use,
    recent_foods,
    update_quick_food,
)
from app.services.macros import Macros

TODAY = date(2026, 10, 13)


def _food(db, name):
    return create_quick_food(db, name=name, serving_label="", macros=Macros(100, 10, 1, 10))


def test_list_is_alphabetical_case_insensitive(db):
    for n in ["oats", "Shake", "Eggs"]:
        _food(db, n)
    assert [f.name for f in list_quick_foods(db)] == ["Eggs", "oats", "Shake"]


def test_by_recent_use_then_alphabetical(db):
    eggs, oats, shake, apple, zucchini = (_food(db, n) for n in ["Eggs", "Oats", "Shake", "apple", "Zucchini"])
    base = datetime(2026, 10, 13, 8, tzinfo=UTC)
    create_entry(db, day=TODAY, macros=Macros(1), name="Oats", quick_food_id=oats.id, now=base)
    create_entry(db, day=TODAY, macros=Macros(1), name="Shake", quick_food_id=shake.id, now=base + timedelta(hours=2))
    create_entry(db, day=TODAY, macros=Macros(1), name="Oats", quick_food_id=oats.id, now=base + timedelta(hours=3))
    assert [f.name for f in list_quick_foods_by_recent_use(db)] == ["Oats", "Shake", "apple", "Eggs", "Zucchini"]


def test_update_quick_food(db):
    food = _food(db, "Eggs")
    update_quick_food(db, food, name="2 eggs", serving_label="2 large", macros=Macros(140, 12, 10, 1))
    assert (list_quick_foods(db)[0].name, list_quick_foods(db)[0].calories) == ("2 eggs", 140)


def test_delete_quick_food_keeps_entries(db):
    food = _food(db, "Eggs")
    entry = log_quick_food(db, food, day=TODAY)
    update_quick_food(db, food, name="Renamed", serving_label="", macros=Macros(1))
    delete_quick_food(db, food)
    db.expire_all()
    kept = get_entry(db, entry.id)
    assert kept.name == "Eggs"
    assert kept.macros == Macros(100, 10, 1, 10)
    assert kept.quick_food_id is None


def test_recent_foods_ranks_excludes_and_limits(db):
    noon = datetime(2026, 10, 13, 17, tzinfo=UTC)
    for i in range(3):
        create_entry(db, day=TODAY, macros=Macros(300, 30, 10, 20), name="Chicken bowl", now=noon + timedelta(minutes=i))
    create_entry(db, day=TODAY, macros=Macros(150, 5, 5, 20), name="Granola bar", now=noon + timedelta(hours=1))
    create_entry(db, day=TODAY, macros=Macros(100, 10, 1, 10), name="eggs")          # quick food name (case-insensitive)
    create_entry(db, day=TODAY, macros=Macros(50))                                    # unnamed
    create_entry(db, day=TODAY - timedelta(days=30), macros=Macros(80), name="Old")   # outside 30-day window
    _food(db, "Eggs")

    recent = recent_foods(db, TODAY)
    assert [(r.name, r.count) for r in recent] == [("Chicken bowl", 3), ("Granola bar", 1)]
    assert recent[0].macros == Macros(300, 30, 10, 20)
    assert len(recent_foods(db, TODAY, limit=1)) == 1
