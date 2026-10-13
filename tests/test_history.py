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
