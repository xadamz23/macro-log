from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.assets import assets
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


SHELL_ASSETS = (
    "css/app.css",
    "js/app.js",
    "vendor/htmx.min.js",
    "vendor/alpine.min.js",
    "vendor/chart.umd.js",
    "icons/icon-192.png",
)
NO_CACHE = {"Cache-Control": "no-cache"}


@router.get("/sw.js", include_in_schema=False)
def service_worker(request: Request):
    context = {"version": assets.version(), "shell": [assets.url(path) for path in SHELL_ASSETS]}
    return templates.TemplateResponse(
        request, "sw.js", context, media_type="application/javascript", headers=NO_CACHE
    )


@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest(request: Request):
    return templates.TemplateResponse(
        request, "manifest.webmanifest", {}, media_type="application/manifest+json", headers=NO_CACHE
    )
