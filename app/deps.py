from collections.abc import Iterator
from datetime import date
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.services.app_settings import get_timezone
from app.services.clock import today_in


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.sessionmaker() as session:
        yield session


DB = Annotated[Session, Depends(get_db)]


def get_tz(request: Request, db: DB) -> str:
    return get_timezone(db, request.app.state.settings.app_tz)


TZ = Annotated[str, Depends(get_tz)]


def get_today(tz: TZ) -> date:
    return today_in(tz)


Today = Annotated[date, Depends(get_today)]
