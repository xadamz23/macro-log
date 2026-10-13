import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from app.auth import AccessVerifier, install_access_check
from app.config import Settings, get_settings
from app.csrf import install_csrf_guard
from app.db import make_engine
from app.routes import entries, foods, history, pages
from app.routes import settings as settings_routes

STATIC_DIR = Path(__file__).parent / "static"
mimetypes.add_type("application/manifest+json", ".webmanifest")


def create_app(settings: Settings | None = None, access_verifier: AccessVerifier | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)

    app = FastAPI(title="Macro Log", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)

    if access_verifier is None and settings.cf_access_team_domain and settings.cf_access_aud:
        access_verifier = AccessVerifier(settings.cf_access_team_domain, settings.cf_access_aud)
    if access_verifier is not None:
        install_access_check(app, access_verifier)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    install_csrf_guard(app)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(pages.router)
    app.include_router(entries.router)
    app.include_router(settings_routes.router)
    app.include_router(foods.router)
    app.include_router(history.router)

    return app
