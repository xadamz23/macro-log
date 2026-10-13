from datetime import date
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.deps import DB, TZ, Today
from app.templating import templates
from app.views import day_context

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def today_page(request: Request, db: DB, tz: TZ, today: Today):
    context = {
        **day_context(db, today, today),
        "tz": tz,
        "nav": "today",
        "open_log": request.query_params.get("log") == "1",
    }
    return templates.TemplateResponse(request, "today.html", context)


@router.get("/day/{day}", response_class=HTMLResponse)
def day_page(request: Request, day: date, db: DB, tz: TZ, today: Today):
    if day >= today:
        return RedirectResponse("/", status_code=303)
    context = {**day_context(db, day, today), "tz": tz, "nav": "history", "open_log": False}
    return templates.TemplateResponse(request, "today.html", context)


SW_PATH = Path(__file__).resolve().parent.parent / "static" / "sw.js"


@router.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(SW_PATH, media_type="application/javascript", headers={"Cache-Control": "no-cache"})
