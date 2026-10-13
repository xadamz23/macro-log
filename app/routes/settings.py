from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.deps import DB, TZ, Today
from app.forms import form_values, parse_macro_form
from app.services.app_settings import set_timezone
from app.services.clock import timezone_choices, today_in
from app.services.targets import resolve_targets, set_targets, target_history
from app.templating import templates

router = APIRouter()


def _targets_context(db, today: date, *, values=None, errors=None, saved=False) -> dict:
    if values is None:
        current = resolve_targets(db, today)
        values = form_values(current) if current else {}
    return {
        "values": values,
        "errors": errors or {},
        "saved": saved,
        "history": target_history(db),
        "today": today,
        "prefix": "target",
    }


def _tz_context(tz: str, today: date, *, error=None, saved=False) -> dict:
    return {"timezone": tz, "timezones": timezone_choices(), "today": today, "error": error, "saved": saved}


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: DB, tz: TZ, today: Today):
    context = {
        "nav": "settings",
        "targets": _targets_context(db, today),
        "tzctx": _tz_context(tz, today),
    }
    return templates.TemplateResponse(request, "settings.html", context)


@router.post("/settings/targets", response_class=HTMLResponse)
async def save_targets(request: Request, db: DB, today: Today):
    form = parse_macro_form(await request.form())
    if not form.ok:
        context = _targets_context(db, today, values=form.values, errors=form.errors)
        return templates.TemplateResponse(request, "partials/targets_card.html", context, status_code=422)
    set_targets(db, today, form.macros)
    return templates.TemplateResponse(request, "partials/targets_card.html", _targets_context(db, today, saved=True))


@router.post("/settings/timezone", response_class=HTMLResponse)
async def save_timezone(request: Request, db: DB, tz: TZ, today: Today):
    name = str((await request.form()).get("timezone") or "")
    try:
        set_timezone(db, name)
    except ValueError as exc:
        context = _tz_context(tz, today, error=str(exc))
        return templates.TemplateResponse(request, "partials/timezone_card.html", context, status_code=422)
    context = _tz_context(name, today_in(name), saved=True)
    return templates.TemplateResponse(request, "partials/timezone_card.html", context)
