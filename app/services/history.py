from dataclasses import dataclass
from datetime import date, timedelta
from functools import reduce

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry
from app.services.macros import MACRO_KEYS, MacroBar, Macros, build_bars
from app.services.targets import targets_resolver


@dataclass(frozen=True)
class DaySummary:
    day: date
    totals: Macros
    targets: Macros | None
    entry_count: int

    @property
    def bars(self) -> list[MacroBar]:
        return build_bars(self.totals, self.targets)


@dataclass(frozen=True)
class Average:
    days_logged: int
    totals: Macros
    targets: Macros | None


def _summaries(db: Session, *conditions, limit: int | None = None) -> list[DaySummary]:
    stmt = (
        select(
            Entry.day,
            func.sum(Entry.calories),
            func.sum(Entry.protein),
            func.sum(Entry.fat),
            func.sum(Entry.carbs),
            func.count(Entry.id),
        )
        .where(*conditions)
        .group_by(Entry.day)
        .order_by(Entry.day.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    resolve = targets_resolver(db)
    return [
        DaySummary(
            day=day,
            totals=Macros(int(cal), round(float(p), 1), round(float(f), 1), round(float(c), 1)),
            targets=resolve(day),
            entry_count=count,
        )
        for day, cal, p, f, c, count in db.execute(stmt)
    ]


def logged_days(db: Session, *, before: date | None = None, limit: int = 20) -> list[DaySummary]:
    conditions = [Entry.day < before] if before else []
    return _summaries(db, *conditions, limit=limit)


def summaries_between(db: Session, start: date, end: date) -> list[DaySummary]:
    """Each logged day in [start, end], newest first; days without entries are absent."""
    return _summaries(db, Entry.day >= start, Entry.day <= end)


def day_totals_between(db: Session, start: date, end: date) -> dict[date, Macros]:
    """Totals for each logged day in [start, end]; days without entries are absent."""
    return {s.day: s.totals for s in summaries_between(db, start, end)}


def _mean(items: list[Macros]) -> Macros:
    return reduce(lambda a, b: a + b, items, Macros()).scaled(1 / len(items))


def average(db: Session, today: date, days: int) -> Average | None:
    summaries = _summaries(db, Entry.day >= today - timedelta(days=days), Entry.day < today)
    if not summaries:
        return None
    targets = [s.targets for s in summaries if s.targets is not None]
    return Average(
        days_logged=len(summaries),
        totals=_mean([s.totals for s in summaries]),
        targets=_mean(targets) if targets else None,
    )


def chart_series(db: Session, today: date, days: int) -> dict:
    start = today - timedelta(days=days - 1)
    by_day = {s.day: s for s in _summaries(db, Entry.day >= start, Entry.day <= today)}
    resolve = targets_resolver(db)
    labels: list[str] = []
    series: dict[str, list] = {key: [] for key in MACRO_KEYS}
    targets: dict[str, list] = {key: [] for key in MACRO_KEYS}
    for offset in range(days):
        day = start + timedelta(days=offset)
        labels.append(day.isoformat())
        summary = by_day.get(day)
        target = resolve(day)
        for key in MACRO_KEYS:
            series[key].append(getattr(summary.totals, key) if summary else None)
            targets[key].append(getattr(target, key) if target else None)
    return {"labels": labels, "series": series, "targets": targets}
