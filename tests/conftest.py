from datetime import date

import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.config import Settings
from app.db import Base
from app.deps import get_today
from app.main import create_app

TODAY = date(2026, 10, 13)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        app_tz="America/Chicago",
        cf_access_team_domain=None,
        cf_access_aud=None,
    )


@pytest.fixture
def app(settings):
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)
    application.dependency_overrides[get_today] = lambda: TODAY
    yield application
    application.state.engine.dispose()


@pytest.fixture
def db(app):
    with app.state.sessionmaker() as session:
        yield session


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c
