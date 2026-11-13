from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.services.entries import day_totals, list_entries
from app.services.foods import list_quick_foods_by_recent_use
from app.services.history import week_of
from app.services.macros import build_bars
from app.services.targets import resolve_targets


def day_context(db: Session, day: date, today: date) -> dict:
    targets = resolve_targets(db, day)
    return {
        "day": day,
        "today": today,
        "is_today": day == today,
        "prev_day": day - timedelta(days=1),
        "next_day": day + timedelta(days=1) if day < today else None,
        "bars": build_bars(day_totals(db, day), targets),
        "has_targets": targets is not None,
        "entries": list_entries(db, day),
        "week": week_of(db, day, today),
    }


def sheet_context(db: Session, day: date, today: date, *, photo_enabled: bool) -> dict:
    """The log sheet's contents. day_value is blank on Today so its posts resolve the date at request time."""
    return {
        "day": day,
        "day_value": "" if day == today else day.isoformat(),
        "photo_enabled": photo_enabled,
        "quick_foods": list_quick_foods_by_recent_use(db),
        "values": {},
        "errors": {},
        "prefix": "entry",
    }
