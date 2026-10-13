"""Reject cross-site state-changing requests (the Cloudflare Access cookie would otherwise ride along)."""

from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import PlainTextResponse

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _is_cross_site(request: Request) -> bool:
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None:
        return fetch_site not in ("same-origin", "none")
    # Older browsers: fall back to comparing Origin with Host.
    origin = request.headers.get("origin")
    return origin is not None and urlsplit(origin).netloc != request.headers.get("host")


def install_csrf_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def csrf_guard(request: Request, call_next):
        if request.method not in SAFE_METHODS and _is_cross_site(request):
            return PlainTextResponse("Cross-site request rejected", status_code=403)
        return await call_next(request)
