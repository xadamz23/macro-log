from datetime import date

from sqlalchemy import func, select

from app.models import Target
from app.services.macros import Macros
from app.services.targets import resolve_targets, set_targets, target_history

OLD = Macros(2000, 150, 70, 200)
NEW = Macros(2500, 180, 80, 260)


def test_no_targets_resolves_to_none(db):
    assert resolve_targets(db, date(2026, 10, 13)) is None


def test_single_target_applies_before_and_after(db):
    set_targets(db, date(2026, 10, 13), OLD)
    assert resolve_targets(db, date(2026, 10, 1)) == OLD   # earliest-row fallback
    assert resolve_targets(db, date(2026, 10, 20)) == OLD


def test_changing_targets_does_not_affect_earlier_days(db):
    set_targets(db, date(2026, 10, 1), OLD)
    set_targets(db, date(2026, 10, 15), NEW)
    assert resolve_targets(db, date(2026, 10, 14)) == OLD
    assert resolve_targets(db, date(2026, 10, 15)) == NEW
    assert resolve_targets(db, date(2026, 11, 1)) == NEW


def test_set_targets_twice_same_day_updates(db):
    set_targets(db, date(2026, 10, 1), OLD)
    set_targets(db, date(2026, 10, 13), NEW)
    set_targets(db, date(2026, 10, 13), Macros(2200, 160, 75, 230))
    assert db.scalar(select(func.count()).select_from(Target)) == 2
    assert resolve_targets(db, date(2026, 10, 13)) == Macros(2200, 160, 75, 230)
    assert resolve_targets(db, date(2026, 10, 12)) == OLD


def test_target_history_newest_first(db):
    set_targets(db, date(2026, 10, 1), OLD)
    set_targets(db, date(2026, 10, 15), NEW)
    assert [t.effective_date for t in target_history(db)] == [date(2026, 10, 15), date(2026, 10, 1)]
