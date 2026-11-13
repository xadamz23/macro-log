from datetime import date

from app.services.entries import create_entry
from app.services.history import average, chart_series, logged_days
from app.services.macros import Macros
from app.services.targets import set_targets

TODAY = date(2026, 10, 13)


def _seed(db):
    set_targets(db, date(2026, 10, 1), Macros(2000, 150, 70, 200))
    set_targets(db, date(2026, 10, 10), Macros(2500, 180, 80, 260))
    create_entry(db, day=date(2026, 10, 5), macros=Macros(1800, 140, 60, 180))
    create_entry(db, day=date(2026, 10, 12), macros=Macros(1000, 80, 30, 100))
    create_entry(db, day=date(2026, 10, 12), macros=Macros(1200, 90, 40, 120))
    create_entry(db, day=TODAY, macros=Macros(500, 40, 10, 50))


def test_logged_days_use_each_days_own_targets(db):
    _seed(db)
    days = logged_days(db)
    assert [d.day for d in days] == [TODAY, date(2026, 10, 12), date(2026, 10, 5)]
    oct12 = days[1]
    assert oct12.totals == Macros(2200, 170, 70, 220)
    assert oct12.entry_count == 2
    assert oct12.targets.calories == 2500
    assert days[2].targets.calories == 2000
    assert days[2].bars[0].pct == 90.0


def test_logged_days_paging(db):
    _seed(db)
    page = logged_days(db, limit=2)
    assert [d.day for d in page] == [TODAY, date(2026, 10, 12)]
    rest = logged_days(db, before=page[-1].day, limit=2)
    assert [d.day for d in rest] == [date(2026, 10, 5)]


def test_average_excludes_today_and_unlogged_days(db):
    _seed(db)
    avg = average(db, TODAY, 7)       # Oct 6..12 → only Oct 12 logged
    assert avg.days_logged == 1
    assert avg.totals == Macros(2200, 170, 70, 220)
    avg30 = average(db, TODAY, 30)    # Oct 5 and Oct 12
    assert avg30.days_logged == 2
    assert avg30.totals.calories == 2000
    assert avg30.targets.calories == 2250


def test_average_none_without_data(db):
    assert average(db, TODAY, 7) is None


def test_chart_series_shape_and_gaps(db):
    _seed(db)
    data = chart_series(db, TODAY, 14)
    assert len(data["labels"]) == 14
    assert data["labels"][-1] == "2026-10-13"
    assert data["series"]["calories"][-1] == 500
    assert data["series"]["calories"][-2] == 2200
    assert data["series"]["calories"][-3] is None
    assert data["targets"]["calories"][-1] == 2500
    assert data["targets"]["calories"][0] == 2000


def test_dashboard_on_target_streak_and_heat(db):
    from datetime import timedelta

    from app.services.history import dashboard

    set_targets(db, date(2026, 9, 1), Macros(2000, 150, 70, 200))
    # yesterday and the day before on target, then one over, then one far under
    for n, kcal in [(1, 2050), (2, 1900), (3, 2400), (4, 1500)]:
        create_entry(db, day=TODAY - timedelta(days=n), macros=Macros(kcal))
    create_entry(db, day=TODAY, macros=Macros(300))  # today is in progress: not in the 30-day counts

    dash = dashboard(db, TODAY)
    assert (dash.on_target, dash.with_target, dash.streak) == (2, 4, 2)
    assert dash.spark7[-4:] == [1500, 2400, 1900, 2050]
    assert len(dash.spark30) == 30 and dash.spark30[0] is None

    assert len(dash.heat) == 13 * 7
    assert dash.heat[0].day.weekday() == 0 and dash.heat[-1].day.weekday() == 6
    by_day = {c.day: c for c in dash.heat}
    assert [by_day[TODAY - timedelta(days=n)].level for n in (1, 3, 4, 5)] == ["on", "over", "low", ""]
    assert by_day[TODAY].is_today
    assert all(c.level == "fut" for c in dash.heat if c.day > TODAY)


def test_dashboard_without_targets(db):
    from app.services.history import dashboard

    create_entry(db, day=date(2026, 10, 12), macros=Macros(1800))
    dash = dashboard(db, TODAY)
    assert (dash.on_target, dash.with_target, dash.streak) == (0, 0, 0)
