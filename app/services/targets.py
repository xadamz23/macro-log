from bisect import bisect_right
from collections.abc import Callable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Target
from app.services.macros import Macros


def targets_resolver(db: Session) -> Callable[[date], Macros | None]:
    """Load all target rows once and return a day -> Macros lookup."""
    rows = list(db.scalars(select(Target).order_by(Target.effective_date)))
    dates = [row.effective_date for row in rows]

    def resolve(day: date) -> Macros | None:
        if not rows:
            return None
        index = bisect_right(dates, day) - 1
        return rows[max(index, 0)].macros

    return resolve


def resolve_targets(db: Session, day: date) -> Macros | None:
    return targets_resolver(db)(day)


def set_targets(db: Session, day: date, macros: Macros) -> Target:
    row = db.scalar(select(Target).where(Target.effective_date == day))
    if row is None:
        row = Target(effective_date=day)
        db.add(row)
    row.calories = macros.calories
    row.protein = macros.protein
    row.fat = macros.fat
    row.carbs = macros.carbs
    db.commit()
    return row


def target_history(db: Session) -> list[Target]:
    return list(db.scalars(select(Target).order_by(Target.effective_date.desc())))
