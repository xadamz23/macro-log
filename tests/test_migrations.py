from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

import app.models  # noqa: F401
from app.db import Base, make_engine


def _upgrade(url: str) -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def test_upgrade_creates_tables(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    _upgrade(url)
    engine = make_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert {"app_settings", "targets", "quick_foods", "entries"} <= tables
    engine.dispose()


def test_models_match_migrations(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    _upgrade(url)
    engine = make_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []
