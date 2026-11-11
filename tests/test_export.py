import csv
import io
from datetime import UTC, date, datetime, timedelta

from app.services.entries import create_entry
from app.services.export import daily_csv, daily_rows, entries_csv, export_range, render_prompt, target_periods
from app.services.macros import Macros
from app.services.profile import ProfileData, save_profile
from app.services.targets import set_targets
from app.services.weight import save_weigh_in, trend_points
from tests.conftest import TODAY

YESTERDAY = TODAY - timedelta(days=1)


def _rows(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_range_ends_yesterday(db):
    assert export_range(db, TODAY, "30") == (YESTERDAY - timedelta(days=29), YESTERDAY)


def test_all_time_starts_at_first_entry_or_weigh_in(db):
    save_weigh_in(db, date(2026, 9, 20), 180)
    create_entry(db, day=date(2026, 9, 25), macros=Macros(2000))
    assert export_range(db, TODAY, "all") == (date(2026, 9, 20), YESTERDAY)


def test_all_time_with_no_data_is_just_yesterday(db):
    assert export_range(db, TODAY, "all") == (YESTERDAY, YESTERDAY)


def test_daily_csv_has_every_day_and_resolves_targets(db):
    set_targets(db, date(2026, 10, 1), Macros(2000, 150, 70, 200))
    set_targets(db, date(2026, 10, 10), Macros(2500, 180, 80, 260))
    create_entry(db, day=date(2026, 10, 8), macros=Macros(1900, 140, 60, 190))
    create_entry(db, day=date(2026, 10, 8), macros=Macros(100, 10, 5, 5))
    create_entry(db, day=date(2026, 10, 11), macros=Macros(2400, 170, 80, 250))
    save_weigh_in(db, date(2026, 10, 8), 180.2)
    points = trend_points(db)
    rows = _rows(daily_csv(daily_rows(db, date(2026, 10, 8), date(2026, 10, 12), points)))

    assert [r["date"] for r in rows] == ["2026-10-08", "2026-10-09", "2026-10-10", "2026-10-11", "2026-10-12"]
    first, gap, _, changed, _ = rows
    assert (first["logged"], first["entry_count"], first["calories"], first["protein"]) == ("true", "2", "2000", "150.0")
    assert (first["target_calories"], first["weight"], first["weight_trend"]) == ("2000", "180.2", "180.2")
    assert (gap["logged"], gap["entry_count"], gap["calories"], gap["weight"]) == ("false", "0", "", "")
    assert gap["target_calories"] == "2000"
    assert gap["weight_trend"] == "180.2"
    assert changed["target_calories"] == "2500"


def test_entries_csv_uses_local_time_and_blanks_backfilled(db):
    # 2026-10-12 17:30 UTC is 12:30 in Chicago.
    create_entry(db, day=date(2026, 10, 12), macros=Macros(500, 40, 10, 50), name="Chicken & rice",
                 now=datetime(2026, 10, 12, 17, 30, tzinfo=UTC))
    create_entry(db, day=date(2026, 10, 11), macros=Macros(300), now=datetime(2026, 10, 12, 18, tzinfo=UTC))
    rows = _rows(entries_csv(db, date(2026, 10, 11), date(2026, 10, 12), "America/Chicago"))
    assert [(r["date"], r["time_local"], r["name"]) for r in rows] == [
        ("2026-10-11", "", "Quick add"),
        ("2026-10-12", "12:30", "Chicken & rice"),
    ]


def _prompt(db) -> str:
    start, end = export_range(db, TODAY, "all")
    points = trend_points(db)
    return render_prompt(db, TODAY, start, end, daily_rows(db, start, end, points), points)


def test_prompt_includes_profile_unescaped(db):
    save_profile(db, ProfileData(sex="male", birth_year=1990, height_in=70, goal="lean_bulk",
                                 training="Push/pull/legs & arms <4 h>"))
    save_weigh_in(db, YESTERDAY, 180)
    text = _prompt(db)
    assert "**Sex:** Male" in text
    assert "about 36 (born 1990)" in text
    assert "5 ft 10 in (178 cm)" in text
    assert "Lean bulk" in text
    assert "Push/pull/legs & arms <4 h>" in text
    assert "**Activity outside training:** not provided" in text
    assert "180.0 lb (81.6 kg)" in text


def test_prompt_with_balance_ready(db):
    for n in range(20, 0, -1):
        day = TODAY - timedelta(days=n)
        save_weigh_in(db, day, 180 + 0.05 * (20 - n))
        create_entry(db, day=day, macros=Macros(2800, 180, 80, 330))
    text = _prompt(db)
    assert "estimated maintenance" in text
    assert "surplus of" in text
    assert "Days logged: **20 / 20**" in text
    assert "| Week of |" in text


def test_prompt_empty_db_renders(db):
    text = _prompt(db)
    assert "Current targets: none set." in text
    assert "not ready yet" in text
    assert "**Sex:** not provided" in text


def test_prompt_weekly_skips_week_starting_today(db):
    monday = date(2026, 10, 12)
    create_entry(db, day=monday - timedelta(days=1), macros=Macros(2000, 150, 70, 200))
    start, end = export_range(db, monday, "all")
    text = render_prompt(db, monday, start, end, daily_rows(db, start, end, []), [])
    assert "| 2026-10-12 |" not in text
    assert "| 2026-10-05 | 2000 |" in text


def _periods(db, start, end):
    points = trend_points(db)
    return target_periods(db, daily_rows(db, start, end, points), points)


def test_target_periods_split_at_each_change_and_clip_to_range(db):
    set_targets(db, date(2026, 10, 1), Macros(2000, 150, 70, 200))
    set_targets(db, date(2026, 10, 10), Macros(2500, 180, 80, 260))
    create_entry(db, day=date(2026, 10, 8), macros=Macros(1900, 140, 60, 190))
    create_entry(db, day=date(2026, 10, 8), macros=Macros(100, 10, 5, 5))
    create_entry(db, day=date(2026, 10, 11), macros=Macros(2400, 170, 80, 250))
    for day, lb in [(8, 180.0), (9, 180.2), (11, 180.6), (12, 180.8)]:
        save_weigh_in(db, date(2026, 10, day), lb)

    first, second = _periods(db, date(2026, 10, 8), date(2026, 10, 12))

    assert (first.start, first.end, first.days, first.target.calories) == (date(2026, 10, 8), date(2026, 10, 9), 2, 2000)
    assert (first.days_logged, first.avg_calories, first.avg_protein, first.days_near_target) == (1, 2000, 150.0, 1)
    assert first.weigh_ins == 2
    assert first.trend_start == 180.0
    assert round(first.rate, 2) == 1.4
    assert (second.start, second.end, second.days, second.target.calories) == (date(2026, 10, 10), date(2026, 10, 12), 3, 2500)
    assert (second.days_logged, second.avg_calories, second.days_near_target, second.weigh_ins) == (1, 2400, 1, 2)
    assert second.trend_start == first.trend_end
    assert round(second.rate, 2) == 1.4


def test_target_periods_skip_days_before_the_first_target(db):
    set_targets(db, date(2026, 10, 10), Macros(2500, 180, 80, 260))
    create_entry(db, day=date(2026, 10, 8), macros=Macros(1000))
    (only,) = _periods(db, date(2026, 10, 8), date(2026, 10, 12))
    assert (only.start, only.days_logged, only.avg_calories) == (date(2026, 10, 10), 0, None)
    assert (only.weigh_ins, only.trend_start, only.trend_end, only.rate) == (0, None, None, None)


def test_near_target_means_within_ten_percent_of_calories(db):
    set_targets(db, date(2026, 10, 1), Macros(2500, 180, 80, 260))
    create_entry(db, day=date(2026, 10, 10), macros=Macros(2750))
    create_entry(db, day=date(2026, 10, 11), macros=Macros(2751))
    (only,) = _periods(db, date(2026, 10, 10), date(2026, 10, 11))
    assert (only.days_logged, only.days_near_target) == (2, 1)


def test_target_periods_none_without_targets(db):
    create_entry(db, day=YESTERDAY, macros=Macros(2000))
    assert _periods(db, YESTERDAY, YESTERDAY) == []


def test_prompt_has_target_period_table_and_instruction(db):
    set_targets(db, date(2026, 10, 1), Macros(2000, 150, 70, 200))
    set_targets(db, date(2026, 10, 8), Macros(2500, 180, 80, 260))
    create_entry(db, day=date(2026, 10, 5), macros=Macros(2100, 150, 70, 200))
    text = _prompt(db)
    assert "### By target period" in text
    assert "| 2026-10-05 to 2026-10-07 | 3 | 2000 kcal · P 150 · F 70 · C 200 | 1 | 2100 | 150 | 1 / 1 |" in text
    assert "| 2026-10-08 to 2026-10-12 | 5 | 2500 kcal · P 180 · F 80 · C 260 | 0 |" in text
    assert "**Target periods:**" in text


def test_prompt_without_targets_says_no_periods(db):
    assert "No targets set, so there are no periods to compare." in _prompt(db)
