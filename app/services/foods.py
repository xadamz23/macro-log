from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry, HiddenRecentFood, QuickFood
from app.services.clock import as_utc, utcnow
from app.services.macros import Macros


def list_quick_foods(db: Session) -> list[QuickFood]:
    return list(db.scalars(select(QuickFood).order_by(func.lower(QuickFood.name), QuickFood.id)))


def list_quick_foods_by_recent_use(db: Session) -> list[QuickFood]:
    """Most recently logged first; never-logged foods after, alphabetically."""
    last_used = (
        select(Entry.quick_food_id, func.max(Entry.logged_at).label("last_used"))
        .where(Entry.quick_food_id.is_not(None))
        .group_by(Entry.quick_food_id)
        .subquery()
    )
    stmt = (
        select(QuickFood)
        .outerjoin(last_used, last_used.c.quick_food_id == QuickFood.id)
        .order_by(
            last_used.c.last_used.is_(None),
            last_used.c.last_used.desc(),
            func.lower(QuickFood.name),
            QuickFood.id,
        )
    )
    return list(db.scalars(stmt))


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
    food = QuickFood()
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
    hidden = {(h.name_key, h.macros): as_utc(h.hidden_at) for h in db.scalars(select(HiddenRecentFood))}
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
    groups = {key: g for key, g in groups.items() if key not in hidden or g["last"] > hidden[key]}
    ranked = sorted(groups.items(), key=lambda kv: (kv[1]["count"], kv[1]["last"]), reverse=True)
    return [RecentFood(g["name"], key[1], g["count"]) for key, g in ranked[:limit]]


def hide_recent_food(db: Session, *, name: str, macros: Macros, now: datetime | None = None) -> None:
    """Drop a name+macros pair from Recent until it is logged again."""
    name_key = name.strip().lower()
    row = db.scalar(
        select(HiddenRecentFood).where(
            HiddenRecentFood.name_key == name_key,
            HiddenRecentFood.calories == macros.calories,
            HiddenRecentFood.protein == macros.protein,
            HiddenRecentFood.fat == macros.fat,
            HiddenRecentFood.carbs == macros.carbs,
        )
    )
    if row is None:
        row = HiddenRecentFood(
            name_key=name_key, calories=macros.calories, protein=macros.protein, fat=macros.fat, carbs=macros.carbs
        )
        db.add(row)
    row.hidden_at = now or utcnow()
    db.commit()
