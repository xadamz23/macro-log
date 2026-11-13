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


ON_TARGET = 0.10  # within ±10% of the calorie target counts as on target
HEAT_WEEKS = 13


@dataclass(frozen=True)
class HeatCell:
    day: date
    level: str  # "", "fut", "low", "near", "on", "over"
    calories: int | None
    target: int | None
    is_today: bool


@dataclass(frozen=True)
class Dashboard:
    """Desktop-only extras for the History page, all from day totals and their targets."""

    spark7: list[int | None]  # calories per day, oldest first, today excluded
    spark30: list[int | None]
    on_target: int  # of the logged days with a calorie target in the last 30 days
    with_target: int
    streak: int  # consecutive on-target days ending yesterday
    heat: list[HeatCell]  # 13 Monday-start weeks, chronological, ending this Sunday


def _level(calories: int, target: int | None) -> str:
    if not target:
        return "low"
    off = (calories - target) / target
    if off > ON_TARGET:
        return "over"
    if abs(off) <= ON_TARGET:
        return "on"
    return "near" if abs(off) <= 2 * ON_TARGET else "low"


def dashboard(db: Session, today: date) -> Dashboard:
    first = today - timedelta(days=today.weekday()) - timedelta(weeks=HEAT_WEEKS - 1)
    start = min(first, today - timedelta(days=30))
    by_day = {s.day: s for s in _summaries(db, Entry.day >= start, Entry.day <= today)}

    def calories(day: date) -> int | None:
        s = by_day.get(day)
        return s.totals.calories if s else None

    def target(day: date) -> int | None:
        s = by_day.get(day)
        return s.targets.calories if s and s.targets else None

    past = [today - timedelta(days=n) for n in range(30, 0, -1)]
    rated = [d for d in past if calories(d) is not None and target(d)]
    on_target = sum(1 for d in rated if _level(calories(d), target(d)) == "on")
    streak = 0
    for d in reversed(past):
        if calories(d) is None or _level(calories(d), target(d)) != "on":
            break
        streak += 1

    heat = []
    for offset in range(HEAT_WEEKS * 7):
        day = first + timedelta(days=offset)
        cal = calories(day)
        level = "fut" if day > today else "" if cal is None else _level(cal, target(day))
        heat.append(HeatCell(day, level, cal, target(day), day == today))

    return Dashboard(
        spark7=[calories(d) for d in past[-7:]],
        spark30=[calories(d) for d in past],
        on_target=on_target,
        with_target=len(rated),
        streak=streak,
        heat=heat,
    )
