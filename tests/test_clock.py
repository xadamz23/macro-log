from datetime import UTC, date, datetime, timedelta

import pytest

from app.services import app_settings, clock


def test_today_in_late_evening_stays_on_local_day():
    # 04:30 UTC on Oct 14 = 23:30 CDT on Oct 13
    assert clock.today_in("America/Chicago", datetime(2026, 10, 14, 4, 30, tzinfo=UTC)) == date(2026, 10, 13)


def test_today_in_after_local_midnight_stays_on_evening_before():
    # 05:30 UTC on Oct 14 = 00:30 CDT on Oct 14
    assert clock.today_in("America/Chicago", datetime(2026, 10, 14, 5, 30, tzinfo=UTC)) == date(2026, 10, 13)


def test_today_in_rolls_over_at_3_01_local():
    # 08:00 UTC on Oct 14 = 03:00 CDT, 08:01 UTC = 03:01 CDT
    assert clock.today_in("America/Chicago", datetime(2026, 10, 14, 8, 0, 59, tzinfo=UTC)) == date(2026, 10, 13)
    assert clock.today_in("America/Chicago", datetime(2026, 10, 14, 8, 1, tzinfo=UTC)) == date(2026, 10, 14)


def test_today_in_rolls_over_at_3_01_across_dst_changes():
    # Clocks fall back on Nov 1 2026 (03:01 CST = 09:01 UTC) and spring forward on Mar 8 2026 (03:01 CDT = 08:01 UTC).
    assert clock.today_in("America/Chicago", datetime(2026, 11, 1, 9, 0, tzinfo=UTC)) == date(2026, 10, 31)
    assert clock.today_in("America/Chicago", datetime(2026, 11, 1, 9, 1, tzinfo=UTC)) == date(2026, 11, 1)
    assert clock.today_in("America/Chicago", datetime(2026, 3, 8, 8, 0, tzinfo=UTC)) == date(2026, 3, 7)
    assert clock.today_in("America/Chicago", datetime(2026, 3, 8, 8, 1, tzinfo=UTC)) == date(2026, 3, 8)


def test_day_ends_at_3_01_next_morning_local():
    assert clock.day_ends(date(2026, 10, 13), "America/Chicago") == datetime(2026, 10, 14, 8, 1, tzinfo=UTC)
    assert clock.day_ends(date(2026, 10, 31), "America/Chicago") == datetime(2026, 11, 1, 9, 1, tzinfo=UTC)
    assert clock.day_ends(date(2026, 3, 7), "America/Chicago") == datetime(2026, 3, 8, 8, 1, tzinfo=UTC)


def test_day_ends_matches_today_in():
    for day in (date(2026, 10, 13), date(2026, 10, 31), date(2026, 3, 7)):
        end = clock.day_ends(day, "America/Chicago")
        assert clock.today_in("America/Chicago", end) == day + timedelta(days=1)
        assert clock.today_in("America/Chicago", end - timedelta(seconds=1)) == day


def test_naive_datetimes_are_treated_as_utc():
    local = clock.to_local(datetime(2026, 10, 14, 5, 30), "America/Chicago")
    assert (local.hour, local.minute) == (0, 30)


def test_timezone_validation():
    assert clock.is_valid_timezone("Europe/London")
    assert not clock.is_valid_timezone("Mars/Olympus")
    assert "America/Chicago" in clock.timezone_choices()


def test_get_timezone_defaults_then_persists(db):
    assert app_settings.get_timezone(db, "UTC") == "UTC"
    app_settings.set_timezone(db, "Europe/Berlin")
    assert app_settings.get_timezone(db, "UTC") == "Europe/Berlin"
    app_settings.set_timezone(db, "Asia/Tokyo")
    assert app_settings.get_timezone(db, "UTC") == "Asia/Tokyo"


def test_set_timezone_rejects_unknown(db):
    with pytest.raises(ValueError):
        app_settings.set_timezone(db, "Mars/Olympus")
