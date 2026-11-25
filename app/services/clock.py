from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; everything we store is UTC."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


# A day runs from 3:01am to 3:01am local time, not midnight to midnight, so something eaten late at night still
# counts toward the evening before. Everything that asks for "today" goes through today_in, so all pages agree.
DAY_STARTS = time(3, 1)
_DAY_OFFSET = timedelta(hours=DAY_STARTS.hour, minutes=DAY_STARTS.minute)


def today_in(tz_name: str, now: datetime | None = None) -> date:
    # Aware datetime minus timedelta is wall-clock arithmetic, so this holds across DST changes.
    return (as_utc(now or utcnow()).astimezone(ZoneInfo(tz_name)) - _DAY_OFFSET).date()


def day_ends(day: date, tz_name: str) -> datetime:
    """When `day` ends (DAY_STARTS on the next calendar day, local time), in UTC."""
    return datetime.combine(day + timedelta(days=1), DAY_STARTS, tzinfo=ZoneInfo(tz_name)).astimezone(UTC)


def to_local(dt: datetime, tz_name: str) -> datetime:
    return as_utc(dt).astimezone(ZoneInfo(tz_name))


@lru_cache
def _zones() -> frozenset[str]:
    return frozenset(available_timezones())


def is_valid_timezone(name: str) -> bool:
    return name in _zones()


def timezone_choices() -> list[str]:
    return sorted(_zones())
