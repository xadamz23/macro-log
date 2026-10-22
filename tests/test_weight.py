from datetime import UTC, date, datetime, timedelta

import pytest

from app.services.entries import create_entry
from app.services.macros import Macros
from app.services.weight import (
    balance,
    chart_series,
    get_weigh_in,
    previous_weigh_in,
    recent_weigh_ins,
    save_weigh_in,
    trend_on,
    trend_points,
    weekly,
)

TODAY = date(2026, 10, 13)  # a Tuesday


def _days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def test_save_weigh_in_upserts_one_per_day(db):
    save_weigh_in(db, TODAY, 180.04, now=datetime(2026, 10, 13, 12, tzinfo=UTC))
    save_weigh_in(db, TODAY, 179.5)
    assert get_weigh_in(db, TODAY).weight == 179.5
    assert len(recent_weigh_ins(db)) == 1


def test_recent_weigh_ins_newest_first_and_previous(db):
    for n, w in [(3, 181.0), (1, 180.0), (0, 179.0)]:
        save_weigh_in(db, _days_ago(n), w)
    assert [w.day for w in recent_weigh_ins(db)] == [TODAY, _days_ago(1), _days_ago(3)]
    assert previous_weigh_in(db, TODAY).weight == 180.0
    assert previous_weigh_in(db, _days_ago(3)) is None


def test_trend_smooths_and_is_gap_aware(db):
    save_weigh_in(db, _days_ago(10), 180.0)
    save_weigh_in(db, _days_ago(9), 190.0)
    save_weigh_in(db, _days_ago(4), 190.0)
    points = trend_points(db)
    assert points[0].trend == 180.0
    assert points[1].trend == pytest.approx(181.0)  # alpha 0.1 for a 1-day step
    # 5-day gap: alpha = 1 - 0.9**5 ~= 0.40951
    assert points[2].trend == pytest.approx(181.0 + (1 - 0.9**5) * 9.0)
    assert trend_on(points, _days_ago(5)) == pytest.approx(181.0)
    assert trend_on(points, _days_ago(11)) is None


def _seed_steady_loss(db, days: int, *, kcal: int = 2200, lb_per_day: float = -0.1, skip_food=()):
    for n in range(days, -1, -1):
        day = _days_ago(n)
        save_weigh_in(db, day, round(190 + lb_per_day * (days - n), 1))
        if n > 0 and n not in skip_food:
            create_entry(db, day=day, macros=Macros(kcal, 150, 70, 200))


def test_balance_not_ready_under_14_days(db):
    _seed_steady_loss(db, 10)
    b = balance(db, trend_points(db), TODAY)
    assert not b.ready
    assert b.days_both == 10
    assert b.rate is None and b.maintenance is None


def test_balance_estimates_maintenance_from_raw_slope(db):
    _seed_steady_loss(db, 40)  # -0.7 lb/week exactly
    b = balance(db, trend_points(db), TODAY)
    assert b.ready
    assert (b.start, b.end) == (_days_ago(28), _days_ago(1))
    assert b.span_days == 28 and b.days_logged == 28
    assert b.rate == pytest.approx(-0.7, abs=0.01)
    assert b.avg_calories == 2200
    assert b.deficit == pytest.approx(350, abs=5)
    assert b.maintenance == pytest.approx(2550, abs=5)


def test_balance_window_shorter_than_28_days_and_skipped_food(db):
    _seed_steady_loss(db, 20, skip_food={3, 4})
    b = balance(db, trend_points(db), TODAY)
    assert b.start == _days_ago(20) and b.span_days == 20
    assert b.days_logged == 18 and b.days_both == 18
    assert b.ready


def test_balance_with_no_data(db):
    b = balance(db, trend_points(db), TODAY)
    assert not b.ready and b.days_both == 0 and b.span_days == 0


def test_weekly_rows_monday_start(db):
    _seed_steady_loss(db, 20)
    rows = weekly(db, trend_points(db), TODAY)
    assert [r.start for r in rows] == [date(2026, 10, 12), date(2026, 10, 5), date(2026, 9, 28), date(2026, 9, 21)]
    current = rows[0]  # Mon only (today excluded from intake)
    assert current.avg_calories == 2200 and current.avg_protein == 150
    assert rows[1].trend_change < 0
    assert rows[3].avg_calories == 2200  # Sep 23..27 seeded (20 days back = Sep 23)
    assert rows[3].trend_change is None  # no trend before that week


def test_weekly_empty(db):
    rows = weekly(db, [], TODAY)
    assert all(r.avg_calories is None and r.trend_change is None for r in rows)


def test_chart_series_has_gaps_for_weights_and_carried_trend(db):
    save_weigh_in(db, _days_ago(5), 180.0)
    save_weigh_in(db, _days_ago(2), 182.0)
    data = chart_series(trend_points(db), TODAY, 7)
    assert data["labels"][0] == _days_ago(6).isoformat() and data["labels"][-1] == TODAY.isoformat()
    assert data["weights"] == [None, 180.0, None, None, 182.0, None, None]
    assert data["trend"][0] is None
    assert data["trend"][2] == 180.0
    assert data["trend"][-1] == data["trend"][4]
