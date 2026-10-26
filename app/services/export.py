"""Zip export for AI analysis: daily/entry/target CSVs plus a prompt.md that explains them."""

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.forms import fmt_num, fmt_signed
from app.models import Entry, Target, WeighIn
from app.services import weight
from app.services.clock import to_local
from app.services.history import summaries_between
from app.services.macros import MACRO_KEYS, Macros
from app.services.profile import GOALS, SEXES, ProfileData, get_profile
from app.services.targets import targets_resolver

RANGES = {"all": None, "30": 30, "90": 90, "180": 180}
SUMMARY_WEEKS_MAX = 12
KG_PER_LB = 0.45359237

# Markdown, not HTML: the shared app templates autoescape, which would mangle "&" or "<" in notes.
_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent / "templates" / "export"),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)
_env.filters["num"] = fmt_num
_env.filters["signed"] = fmt_signed


def export_range(db: Session, today: date, range_key: str) -> tuple[date, date]:
    """Inclusive [start, end]; ends yesterday because today's log isn't finished."""
    end = today - timedelta(days=1)
    days = RANGES[range_key]
    if days is not None:
        return end - timedelta(days=days - 1), end
    firsts = [d for d in (db.scalar(select(func.min(Entry.day))), db.scalar(select(func.min(WeighIn.day)))) if d]
    return (min(min(firsts), end) if firsts else end), end


@dataclass(frozen=True)
class DailyRow:
    day: date
    entry_count: int
    totals: Macros | None
    target: Macros | None
    weight: float | None
    trend: float | None


def daily_rows(db: Session, start: date, end: date, points: list[weight.TrendPoint]) -> list[DailyRow]:
    """One row per calendar day so unlogged days are explicit gaps rather than missing rows."""
    logged = {s.day: s for s in summaries_between(db, start, end)}
    resolve = targets_resolver(db)
    weights = {p.day: p.weight for p in points}
    rows = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        summary = logged.get(day)
        rows.append(
            DailyRow(
                day=day,
                entry_count=summary.entry_count if summary else 0,
                totals=summary.totals if summary else None,
                target=resolve(day),
                weight=weights.get(day),
                trend=weight.trend_on(points, day),
            )
        )
    return rows


def _csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue()


def _blank(value):
    return "" if value is None else value


def daily_csv(rows: list[DailyRow]) -> str:
    header = ["date", "logged", "entry_count", *MACRO_KEYS, *(f"target_{k}" for k in MACRO_KEYS), "weight", "weight_trend"]
    return _csv(
        header,
        [
            [
                r.day.isoformat(),
                "true" if r.totals else "false",
                r.entry_count,
                *(_blank(r.totals and getattr(r.totals, k)) for k in MACRO_KEYS),
                *(_blank(r.target and getattr(r.target, k)) for k in MACRO_KEYS),
                _blank(r.weight),
                "" if r.trend is None else round(r.trend, 2),
            ]
            for r in rows
        ],
    )


def entries_csv(db: Session, start: date, end: date, tz: str) -> str:
    stmt = select(Entry).where(Entry.day >= start, Entry.day <= end).order_by(Entry.day, Entry.logged_at)
    rows = []
    for e in db.scalars(stmt):
        local = to_local(e.logged_at, tz)
        # Items back-filled on a later date carry the time they were typed in, not eaten, so drop it.
        time_local = local.strftime("%H:%M") if local.date() == e.day else ""
        rows.append([e.day.isoformat(), time_local, e.name or "Quick add", e.servings, e.calories, e.protein, e.fat, e.carbs])
    return _csv(["date", "time_local", "name", "servings", *MACRO_KEYS], rows)


def targets_csv(db: Session) -> str:
    rows = [
        [t.effective_date.isoformat(), t.calories, t.protein, t.fat, t.carbs]
        for t in db.scalars(select(Target).order_by(Target.effective_date))
    ]
    return _csv(["effective_date", *MACRO_KEYS], rows)


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _profile_lines(profile: ProfileData, today: date, trend: float | None) -> dict[str, str]:
    missing = "not provided"
    height = missing
    if profile.height_in is not None:
        feet, inches = divmod(round(profile.height_in), 12)
        height = f"{feet} ft {inches} in ({round(profile.height_in * 2.54)} cm)"
    return {
        "Sex": SEXES.get(profile.sex or "", missing),
        "Age": f"about {today.year - profile.birth_year} (born {profile.birth_year})" if profile.birth_year else missing,
        "Height": height,
        "Current trend weight": f"{trend:.1f} lb ({trend * KG_PER_LB:.1f} kg)" if trend is not None else missing,
        "Goal": GOALS.get(profile.goal or "", missing),
        "Training": profile.training or missing,
        "Activity outside training": profile.activity or missing,
        "Notes": profile.notes or missing,
    }


def render_prompt(db: Session, today: date, start: date, end: date, rows: list[DailyRow], points) -> str:
    logged = [r for r in rows if r.totals]
    trend_now = weight.trend_on(points, end)
    trend_start = weight.trend_on(points, start)
    # Monday-start weeks from the one holding `start` through the current one; the current is dropped below if empty.
    weeks = min(SUMMARY_WEEKS_MAX, (_monday(today) - _monday(start)).days // 7 + 1)

    def avg(attr: str, key: str) -> float | None:
        return _mean([getattr(getattr(r, attr), key) for r in logged if getattr(r, attr) is not None])

    return _env.get_template("prompt.md").render(
        today=today,
        start=start,
        end=end,
        span_days=len(rows),
        days_logged=len(logged),
        days_weighed=sum(1 for r in rows if r.weight is not None),
        profile=_profile_lines(get_profile(db), today, trend_now),
        current_target=targets_resolver(db)(today),
        avg_intake={k: avg("totals", k) for k in MACRO_KEYS},
        avg_target={k: avg("target", k) for k in MACRO_KEYS},
        trend_start=trend_start,
        trend_now=trend_now,
        protein_per_lb=(avg("totals", "protein") / trend_now) if trend_now and logged else None,
        bal=weight.balance(db, points, today),
        weeks=[w for w in weight.weekly(db, points, today, weeks=weeks) if w.start <= end],
        alpha=weight.ALPHA,
        window_days=weight.WINDOW_DAYS,
        min_days=weight.MIN_DAYS,
        kcal_per_lb=weight.KCAL_PER_LB,
    )


def build_export(db: Session, today: date, tz: str, range_key: str) -> bytes:
    start, end = export_range(db, today, range_key)
    points = weight.trend_points(db)
    rows = daily_rows(db, start, end, points)
    folder = f"macro-log-{today.isoformat()}"
    files = {
        "prompt.md": render_prompt(db, today, start, end, rows, points),
        "daily.csv": daily_csv(rows),
        "entries.csv": entries_csv(db, start, end, tz),
        "targets.csv": targets_csv(db),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(f"{folder}/{name}", content)
    return buf.getvalue()
