from datetime import date

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.deps import DB, Today
from app.services.history import average, chart_series, logged_days
from app.templating import templates

router = APIRouter()

PAGE_SIZE = 20


def _rows_context(db, today: date, before: date | None) -> dict:
    days = logged_days(db, before=before, limit=PAGE_SIZE)
    next_before = days[-1].day if len(days) == PAGE_SIZE else None
    return {"days": days, "next_before": next_before, "today": today}


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, db: DB, today: Today):
    context = {
        "nav": "history",
        "avg7": average(db, today, 7),
        "avg30": average(db, today, 30),
        **_rows_context(db, today, None),
    }
    return templates.TemplateResponse(request, "history.html", context)


@router.get("/history/days", response_class=HTMLResponse)
def history_days(request: Request, db: DB, today: Today, before: date):
    return templates.TemplateResponse(request, "partials/day_rows.html", _rows_context(db, today, before))


@router.get("/history/data")
def history_data(db: DB, today: Today, days: int = Query(30, ge=7, le=365)) -> dict:
    return chart_series(db, today, days)
