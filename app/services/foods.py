from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry, QuickFood
from app.services.clock import as_utc
from app.services.macros import Macros


def list_quick_foods(db: Session) -> list[QuickFood]:
    return list(db.scalars(select(QuickFood).order_by(QuickFood.sort_order, QuickFood.id)))


def get_quick_food(db: Session, food_id: int) -> QuickFood | None:
    return db.get(QuickFood, food_id)


def _apply(food: QuickFood, name: str, serving_label: str, macros: Macros) -> None:
    food.name = name.strip()
    food.serving_label = serving_label.strip()
    food.calories = macros.calories
    food.protein = macros.protein
    food.fat = macros.fat
    food.carbs = macros.carbs


def create_quick_food(db: Session, *, name: str, serving_label: str, macros: Macros) -> QuickFood:
    max_order = db.scalar(select(func.max(QuickFood.sort_order)))
    food = QuickFood(sort_order=(max_order if max_order is not None else -1) + 1)
    _apply(food, name, serving_label, macros)
    db.add(food)
    db.commit()
    return food


def update_quick_food(db: Session, food: QuickFood, *, name: str, serving_label: str, macros: Macros) -> QuickFood:
    _apply(food, name, serving_label, macros)
    db.commit()
    return food


def delete_quick_food(db: Session, food: QuickFood) -> None:
    db.delete(food)
    db.commit()


def move_quick_food(db: Session, food: QuickFood, direction: str) -> None:
    foods = list_quick_foods(db)
    index = next(i for i, f in enumerate(foods) if f.id == food.id)
    target = index - 1 if direction == "up" else index + 1
    if not 0 <= target < len(foods):
        return
    foods[index], foods[target] = foods[target], foods[index]
    for order, item in enumerate(foods):
        item.sort_order = order
    db.commit()


@dataclass(frozen=True)
class RecentFood:
    name: str
    macros: Macros
    count: int


def recent_foods(db: Session, today: date, *, days: int = 30, limit: int = 8) -> list[RecentFood]:
    quick_names = {f.name.strip().lower() for f in list_quick_foods(db)}
    entries = db.scalars(
        select(Entry).where(
            Entry.name.is_not(None),
            Entry.day >= today - timedelta(days=days - 1),
            Entry.day <= today,
        )
    )
    groups: dict[tuple[str, Macros], dict] = {}
    for entry in entries:
        key = (entry.name.strip().lower(), entry.macros)
        if key[0] in quick_names:
            continue
        group = groups.setdefault(key, {"name": entry.name, "count": 0, "last": None})
        group["count"] += 1
        logged = as_utc(entry.logged_at)
        if group["last"] is None or logged > group["last"]:
            group["last"] = logged
    ranked = sorted(groups.items(), key=lambda kv: (kv[1]["count"], kv[1]["last"]), reverse=True)
    return [RecentFood(g["name"], key[1], g["count"]) for key, g in ranked[:limit]]
