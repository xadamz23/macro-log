from datetime import UTC, date, datetime

import pytest

from app.services import app_settings, clock


def test_today_in_late_evening_stays_on_local_day():
    # 04:30 UTC on Oct 14 = 23:30 CDT on Oct 13
    assert clock.today_in("America/Chicago", datetime(2026, 10, 14, 4, 30, tzinfo=UTC)) == date(2026, 10, 13)


def test_today_in_just_after_local_midnight_rolls_over():
    # 05:30 UTC on Oct 14 = 00:30 CDT on Oct 14
    assert clock.today_in("America/Chicago", datetime(2026, 10, 14, 5, 30, tzinfo=UTC)) == date(2026, 10, 14)


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
