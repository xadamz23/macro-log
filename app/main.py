from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings
from app.db import make_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)

    app = FastAPI(title="Macro Log", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    return app
