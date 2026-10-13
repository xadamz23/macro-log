from datetime import UTC, date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; everything we store is UTC."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def today_in(tz_name: str, now: datetime | None = None) -> date:
    return as_utc(now or utcnow()).astimezone(ZoneInfo(tz_name)).date()


def to_local(dt: datetime, tz_name: str) -> datetime:
    return as_utc(dt).astimezone(ZoneInfo(tz_name))


@lru_cache
def _zones() -> frozenset[str]:
    return frozenset(available_timezones())


def is_valid_timezone(name: str) -> bool:
    return name in _zones()


def timezone_choices() -> list[str]:
    return sorted(_zones())
