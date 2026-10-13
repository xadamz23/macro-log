from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.deps import DB, TZ, Today
from app.forms import form_values, parse_macro_form, parse_servings, parse_text
from app.services.entries import create_entry, delete_entry, get_entry, log_quick_food, update_entry
from app.services.foods import create_quick_food, get_quick_food, list_quick_foods_by_recent_use, recent_foods
from app.templating import templates
from app.views import day_context

router = APIRouter()


def _parse_day(raw, today: date) -> date:
    try:
        day = date.fromisoformat(str(raw or ""))
    except ValueError:
        return today
    return min(day, today)


def _refresh(request: Request, db, day: date, today: date, tz: str, *, toast_entry=None, headers=None):
    context = {**day_context(db, day, today), "tz": tz, "oob": True, "toast_entry": toast_entry}
    return templates.TemplateResponse(request, "partials/day_refresh.html", context, headers=headers)


def _entry_or_404(db, entry_id: int):
    entry = get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


def _day_value(raw, day: date) -> str:
    """What the sheet posts back: blank on Today (resolved at request time), else the explicit date."""
    return day.isoformat() if raw else ""


@router.get("/log-sheet", response_class=HTMLResponse)
def log_sheet(request: Request, db: DB, today: Today, day: str = ""):
    parsed = _parse_day(day, today)
    context = {
        "day": parsed,
        "day_value": _day_value(day, parsed),
        "quick_foods": list_quick_foods_by_recent_use(db),
        "recent": recent_foods(db, today),
        "values": {},
        "errors": {},
        "prefix": "entry",
    }
    return templates.TemplateResponse(request, "partials/log_sheet.html", context)


@router.post("/entries", response_class=HTMLResponse)
async def create_entry_route(request: Request, db: DB, tz: TZ, today: Today):
    data = await request.form()
    day = _parse_day(data.get("day"), today)
    form = parse_macro_form(data)
    name, name_error = parse_text(data, "name", max_len=100)
    serving_label, label_error = parse_text(data, "serving_label", max_len=50)
    save_quick = data.get("save_quick") == "on"

    errors = dict(form.errors)
    if name_error:
        errors["name"] = name_error
    if label_error:
        errors["serving_label"] = label_error
    if save_quick and not name:
        errors["name"] = "Name is required to save as a quick food"
    if errors:
        context = {
            "day": day,
            "day_value": _day_value(data.get("day"), day),
            "values": {**form.values, "name": name, "serving_label": serving_label, "save_quick": save_quick},
            "errors": errors,
            "prefix": "entry",
        }
        return templates.TemplateResponse(
            request, "partials/entry_form.html", context, status_code=422,
            headers={"HX-Retarget": "#entry-form", "HX-Reswap": "outerHTML"},
        )

    quick_food_id = None
    if save_quick:
        quick_food_id = create_quick_food(db, name=name, serving_label=serving_label, macros=form.macros).id
    entry = create_entry(db, day=day, macros=form.macros, name=name, quick_food_id=quick_food_id)
    return _refresh(request, db, day, today, tz, toast_entry=entry, headers={"HX-Trigger": "entry-logged"})


@router.post("/quick-foods/{food_id}/log", response_class=HTMLResponse)
async def log_quick_food_route(food_id: int, request: Request, db: DB, tz: TZ, today: Today):
    data = await request.form()
    food = get_quick_food(db, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Quick food not found")
    try:
        servings = parse_servings(data.get("servings"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid servings") from None
    day = _parse_day(data.get("day"), today)
    entry = log_quick_food(db, food, day=day, servings=servings)
    return _refresh(request, db, day, today, tz, toast_entry=entry, headers={"HX-Trigger": "entry-logged"})


@router.get("/entries/{entry_id}/edit", response_class=HTMLResponse)
def edit_entry_form(entry_id: int, request: Request, db: DB):
    entry = _entry_or_404(db, entry_id)
    context = {"entry": entry, "values": {**form_values(entry.macros), "name": entry.name or ""}, "errors": {}}
    return templates.TemplateResponse(request, "partials/entry_edit.html", context)


@router.get("/entries/{entry_id}/row", response_class=HTMLResponse)
def entry_row(entry_id: int, request: Request, db: DB, tz: TZ):
    entry = _entry_or_404(db, entry_id)
    return templates.TemplateResponse(request, "partials/entry_row.html", {"entry": entry, "tz": tz})


@router.put("/entries/{entry_id}", response_class=HTMLResponse)
async def update_entry_route(entry_id: int, request: Request, db: DB, tz: TZ, today: Today):
    entry = _entry_or_404(db, entry_id)
    data = await request.form()
    form = parse_macro_form(data)
    name, name_error = parse_text(data, "name", max_len=100)
    errors = dict(form.errors)
    if name_error:
        errors["name"] = name_error
    if errors:
        context = {"entry": entry, "values": {**form.values, "name": name}, "errors": errors}
        return templates.TemplateResponse(
            request, "partials/entry_edit.html", context, status_code=422,
            headers={"HX-Retarget": f"#entry-{entry.id}", "HX-Reswap": "outerHTML"},
        )
    update_entry(db, entry, name=name, macros=form.macros)
    return _refresh(request, db, entry.day, today, tz)


@router.delete("/entries/{entry_id}", response_class=HTMLResponse)
def delete_entry_route(entry_id: int, request: Request, db: DB, tz: TZ, today: Today):
    entry = _entry_or_404(db, entry_id)
    day = entry.day
    delete_entry(db, entry)
    return _refresh(request, db, day, today, tz)
