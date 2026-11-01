from collections.abc import Iterator
from datetime import date
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.services.app_settings import get_timezone
from app.services.clock import today_in
from app.services.photo_macros import ClaudeMacroEstimator, MacroEstimator


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


def get_macro_estimator(request: Request) -> MacroEstimator | None:
    """None when no API key is configured. One client per app, so its connections are reused."""
    state = request.app.state
    if not state.settings.anthropic_api_key:
        return None
    if getattr(state, "macro_estimator", None) is None:
        state.macro_estimator = ClaudeMacroEstimator(state.settings.anthropic_api_key, state.settings.anthropic_model)
    return state.macro_estimator


Estimator = Annotated[MacroEstimator | None, Depends(get_macro_estimator)]
