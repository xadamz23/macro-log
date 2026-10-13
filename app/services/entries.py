from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry, QuickFood
from app.services.clock import utcnow
from app.services.macros import Macros


def _clean_name(name: str | None) -> str | None:
    return (name or "").strip() or None


def create_entry(
    db: Session,
    *,
    day: date,
    macros: Macros,
    name: str | None = None,
    servings: float = 1.0,
    quick_food_id: int | None = None,
    now: datetime | None = None,
) -> Entry:
    entry = Entry(
        day=day,
        logged_at=now or utcnow(),
        name=_clean_name(name),
        calories=macros.calories,
        protein=macros.protein,
        fat=macros.fat,
        carbs=macros.carbs,
        servings=servings,
        quick_food_id=quick_food_id,
    )
    db.add(entry)
    db.commit()
    return entry


def log_quick_food(db: Session, food: QuickFood, *, day: date, servings: float = 1.0) -> Entry:
    return create_entry(
        db,
        day=day,
        macros=food.macros.scaled(servings),
        name=food.name,
        servings=servings,
        quick_food_id=food.id,
    )


def get_entry(db: Session, entry_id: int) -> Entry | None:
    return db.get(Entry, entry_id)


def list_entries(db: Session, day: date) -> list[Entry]:
    stmt = select(Entry).where(Entry.day == day).order_by(Entry.logged_at.desc(), Entry.id.desc())
    return list(db.scalars(stmt))


def day_totals(db: Session, day: date) -> Macros:
    row = db.execute(
        select(
            func.coalesce(func.sum(Entry.calories), 0),
            func.coalesce(func.sum(Entry.protein), 0.0),
            func.coalesce(func.sum(Entry.fat), 0.0),
            func.coalesce(func.sum(Entry.carbs), 0.0),
        ).where(Entry.day == day)
    ).one()
    return Macros(int(row[0]), round(float(row[1]), 1), round(float(row[2]), 1), round(float(row[3]), 1))


def update_entry(db: Session, entry: Entry, *, name: str | None, macros: Macros) -> Entry:
    entry.name = _clean_name(name)
    entry.calories = macros.calories
    entry.protein = macros.protein
    entry.fat = macros.fat
    entry.carbs = macros.carbs
    db.commit()
    return entry


def delete_entry(db: Session, entry: Entry) -> None:
    db.delete(entry)
    db.commit()
