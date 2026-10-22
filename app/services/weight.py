"""Morning weigh-ins: smoothed trend, weekly rate, and maintenance calories estimated from logged intake."""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WeighIn
from app.services.clock import utcnow
from app.services.history import day_totals_between

ALPHA = 0.1  # trend smoothing per day
WINDOW_DAYS = 28
MIN_DAYS = 14  # days with both a weigh-in and logged food before estimating
KCAL_PER_LB = 3500


def get_weigh_in(db: Session, day: date) -> WeighIn | None:
    return db.scalar(select(WeighIn).where(WeighIn.day == day))


def get_weigh_in_by_id(db: Session, weigh_in_id: int) -> WeighIn | None:
    return db.get(WeighIn, weigh_in_id)


def previous_weigh_in(db: Session, day: date) -> WeighIn | None:
    return db.scalar(select(WeighIn).where(WeighIn.day < day).order_by(WeighIn.day.desc()).limit(1))


def recent_weigh_ins(db: Session, limit: int = 30) -> list[WeighIn]:
    return list(db.scalars(select(WeighIn).order_by(WeighIn.day.desc()).limit(limit)))


def save_weigh_in(db: Session, day: date, weight: float, *, now: datetime | None = None) -> WeighIn:
    row = get_weigh_in(db, day)
    if row is None:
        row = WeighIn(day=day)
        db.add(row)
    row.weight = round(weight, 1)
    row.logged_at = now or utcnow()
    db.commit()
    return row


def update_weigh_in(db: Session, row: WeighIn, weight: float) -> WeighIn:
    row.weight = round(weight, 1)
    db.commit()
    return row


def delete_weigh_in(db: Session, row: WeighIn) -> None:
    db.delete(row)
    db.commit()


@dataclass(frozen=True)
class TrendPoint:
    day: date
    weight: float
    trend: float


def trend_points(db: Session) -> list[TrendPoint]:
    """Exponentially smoothed weight; a gap of g days counts as g smoothing steps toward the next reading."""
    points: list[TrendPoint] = []
    for row in db.scalars(select(WeighIn).order_by(WeighIn.day)):
        if not points:
            trend = row.weight
        else:
            prev = points[-1]
            alpha = 1 - (1 - ALPHA) ** (row.day - prev.day).days
            trend = prev.trend + alpha * (row.weight - prev.trend)
        points.append(TrendPoint(row.day, row.weight, trend))
    return points


def trend_on(points: list[TrendPoint], day: date) -> float | None:
    index = bisect_right([p.day for p in points], day) - 1
    return points[index].trend if index >= 0 else None


def _slope_per_day(points: list[TrendPoint]) -> float | None:
    if len(points) < 2:
        return None
    xs = [p.day.toordinal() for p in points]
    ys = [p.weight for p in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    var = sum((x - mx) ** 2 for x in xs)
    if not var:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var


@dataclass(frozen=True)
class Balance:
    start: date
    end: date
    span_days: int
    days_logged: int
    days_both: int
    avg_calories: int | None
    rate: float | None  # lb/week, negative when losing
    deficit: int | None  # kcal/day below maintenance; negative is a surplus
    maintenance: int | None

    @property
    def ready(self) -> bool:
        return self.maintenance is not None

    @property
    def weeks(self) -> int:
        return max(1, round(self.span_days / 7))


def balance(db: Session, points: list[TrendPoint], today: date) -> Balance:
    """Intake vs. weight change over the 28 days ending yesterday (today's food isn't finished yet)."""
    end = today - timedelta(days=1)
    start = end - timedelta(days=WINDOW_DAYS - 1)
    if points:
        start = max(start, points[0].day)
    if not points or start > end:
        return Balance(end, end, 0, 0, 0, None, None, None, None)

    totals = day_totals_between(db, start, end)
    window = [p for p in points if start <= p.day <= end]
    days_both = sum(1 for p in window if p.day in totals)
    avg_calories = round(sum(t.calories for t in totals.values()) / len(totals)) if totals else None

    rate = deficit = maintenance = None
    slope = _slope_per_day(window)
    if days_both >= MIN_DAYS and slope is not None and avg_calories is not None:
        rate = slope * 7
        deficit = round(-slope * KCAL_PER_LB)
        maintenance = avg_calories + deficit
    return Balance(start, end, (end - start).days + 1, len(totals), days_both, avg_calories, rate, deficit, maintenance)


@dataclass(frozen=True)
class WeekRow:
    start: date
    avg_calories: int | None
    avg_protein: float | None
    trend_change: float | None


def weekly(db: Session, points: list[TrendPoint], today: date, weeks: int = 4) -> list[WeekRow]:
    """Monday-start weeks, newest first; intake excludes today, trend change is end-of-week vs. prior week."""
    monday = today - timedelta(days=today.weekday())
    first = monday - timedelta(weeks=weeks - 1)
    totals = day_totals_between(db, first, today - timedelta(days=1))
    rows = []
    for i in range(weeks):
        start = monday - timedelta(weeks=i)
        end = min(start + timedelta(days=6), today)
        week_totals = [t for day, t in totals.items() if start <= day <= end]
        change = None
        if any(start <= p.day <= end for p in points):
            before, after = trend_on(points, start - timedelta(days=1)), trend_on(points, end)
            if before is not None and after is not None:
                change = after - before
        rows.append(
            WeekRow(
                start=start,
                avg_calories=round(sum(t.calories for t in week_totals) / len(week_totals)) if week_totals else None,
                avg_protein=round(sum(t.protein for t in week_totals) / len(week_totals)) if week_totals else None,
                trend_change=change,
            )
        )
    return rows


def chart_series(points: list[TrendPoint], today: date, days: int) -> dict:
    start = today - timedelta(days=days - 1)
    by_day = {p.day: p.weight for p in points}
    labels, weights, trend = [], [], []
    for offset in range(days):
        day = start + timedelta(days=offset)
        value = trend_on(points, day)
        labels.append(day.isoformat())
        weights.append(by_day.get(day))
        trend.append(None if value is None else round(value, 2))
    return {"labels": labels, "weights": weights, "trend": trend}
