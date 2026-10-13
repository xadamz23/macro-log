from sqlalchemy.orm import Session

from app.models import AppSettings
from app.services.clock import is_valid_timezone

_ROW_ID = 1


def get_timezone(db: Session, default: str) -> str:
    row = db.get(AppSettings, _ROW_ID)
    return row.timezone if row else default


def set_timezone(db: Session, name: str) -> None:
    if not is_valid_timezone(name):
        raise ValueError(f"Unknown timezone: {name}")
    row = db.get(AppSettings, _ROW_ID)
    if row is None:
        db.add(AppSettings(id=_ROW_ID, timezone=name))
    else:
        row.timezone = name
    db.commit()
