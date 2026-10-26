from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.deps import DB, TZ, Today
from app.services.export import build_export
from app.services.profile import get_profile
from app.templating import templates

router = APIRouter()

RANGE_CHOICES = [("all", "All time"), ("180", "Last 180 days"), ("90", "Last 90 days"), ("30", "Last 30 days")]


@router.get("/export", response_class=HTMLResponse)
def export_page(request: Request, db: DB):
    context = {"nav": "export", "ranges": RANGE_CHOICES, "profile_empty": get_profile(db).is_empty()}
    return templates.TemplateResponse(request, "export.html", context)


@router.get("/export/download")
def export_download(db: DB, tz: TZ, today: Today, range: Literal["all", "30", "90", "180"] = "all") -> Response:
    filename = f"macro-log-{today.isoformat()}.zip"
    return Response(
        build_export(db, today, tz, range),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
