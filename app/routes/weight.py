from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.deps import DB, Today
from app.forms import fmt_num, parse_weight
from app.services.weight import (
    MIN_DAYS,
    balance,
    chart_series,
    delete_weigh_in,
    get_weigh_in,
    get_weigh_in_by_id,
    previous_weigh_in,
    recent_weigh_ins,
    save_weigh_in,
    trend_points,
    update_weigh_in,
    weekly,
)
from app.templating import templates

router = APIRouter()


def _card_context(db, today: date, *, editing: bool = False, value: str = "", error: str | None = None) -> dict:
    weighed = get_weigh_in(db, today)
    if editing and weighed and not value:
        value = fmt_num(weighed.weight)
    return {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "weighed": weighed,
        "prev": previous_weigh_in(db, today),
        "editing": editing,
        "value": value,
        "error": error,
    }


def _body_context(db, today: date) -> dict:
    points = trend_points(db)
    return {
        **_card_context(db, today),
        "trend": points[-1].trend if points else None,
        "bal": balance(db, points, today),
        "weeks": weekly(db, points, today),
        "weigh_ins": recent_weigh_ins(db),
        "min_days": MIN_DAYS,
    }


def _body(request: Request, db, today: date):
    return templates.TemplateResponse(request, "partials/weight_body.html", _body_context(db, today))


def _weigh_in_or_404(db, weigh_in_id: int):
    row = get_weigh_in_by_id(db, weigh_in_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Weigh-in not found")
    return row


@router.get("/weight", response_class=HTMLResponse)
def weight_page(request: Request, db: DB, today: Today):
    return templates.TemplateResponse(request, "weight.html", {**_body_context(db, today), "nav": "weight"})


@router.get("/weight/card", response_class=HTMLResponse)
def weigh_card(request: Request, db: DB, today: Today, edit: bool = False):
    return templates.TemplateResponse(request, "partials/weigh_card.html", _card_context(db, today, editing=edit))


@router.post("/weight", response_class=HTMLResponse)
async def save_weight(request: Request, db: DB, today: Today):
    raw = str((await request.form()).get("weight") or "").strip()
    weight, error = parse_weight(raw)
    if error:
        context = _card_context(db, today, editing=True, value=raw, error=error)
        return templates.TemplateResponse(
            request, "partials/weigh_card.html", context, status_code=422,
            headers={"HX-Retarget": "#weigh-card", "HX-Reswap": "outerHTML"},
        )
    save_weigh_in(db, today, weight)
    return _body(request, db, today)


@router.get("/weight/data")
def weight_data(db: DB, today: Today, days: int = Query(90, ge=7, le=365)) -> dict:
    return chart_series(trend_points(db), today, days)


@router.get("/weigh-ins/{weigh_in_id}/edit", response_class=HTMLResponse)
def edit_weigh_in_form(weigh_in_id: int, request: Request, db: DB, today: Today):
    row = _weigh_in_or_404(db, weigh_in_id)
    context = {"w": row, "today": today, "value": fmt_num(row.weight), "error": None}
    return templates.TemplateResponse(request, "partials/weigh_in_edit.html", context)


@router.get("/weigh-ins/{weigh_in_id}/row", response_class=HTMLResponse)
def weigh_in_row(weigh_in_id: int, request: Request, db: DB, today: Today):
    row = _weigh_in_or_404(db, weigh_in_id)
    return templates.TemplateResponse(request, "partials/weigh_in_row.html", {"w": row, "today": today})


@router.put("/weigh-ins/{weigh_in_id}", response_class=HTMLResponse)
async def update_weigh_in_route(weigh_in_id: int, request: Request, db: DB, today: Today):
    row = _weigh_in_or_404(db, weigh_in_id)
    raw = str((await request.form()).get("weight") or "").strip()
    weight, error = parse_weight(raw)
    if error:
        context = {"w": row, "today": today, "value": raw, "error": error}
        return templates.TemplateResponse(
            request, "partials/weigh_in_edit.html", context, status_code=422,
            headers={"HX-Retarget": f"#weigh-in-{row.id}", "HX-Reswap": "outerHTML"},
        )
    update_weigh_in(db, row, weight)
    return _body(request, db, today)


@router.delete("/weigh-ins/{weigh_in_id}", response_class=HTMLResponse)
def delete_weigh_in_route(weigh_in_id: int, request: Request, db: DB, today: Today):
    delete_weigh_in(db, _weigh_in_or_404(db, weigh_in_id))
    return _body(request, db, today)
