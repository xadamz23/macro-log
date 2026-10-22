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
    assert {"app_settings", "targets", "quick_foods", "entries", "weigh_ins"} <= tables
    engine.dispose()


def test_models_match_migrations(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    _upgrade(url)
    engine = make_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []


def test_drop_sort_order_keeps_entry_links(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0001")
    engine = make_engine(url)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO quick_foods (id, name, serving_label, calories, protein, fat, carbs, sort_order)"
            " VALUES (1, 'Eggs', '', 70, 6, 5, 0, 0)"
        )
        conn.exec_driver_sql(
            "INSERT INTO entries (day, logged_at, name, calories, protein, fat, carbs, servings, quick_food_id)"
            " VALUES ('2026-10-13', '2026-10-13 08:00:00', 'Eggs', 70, 6, 5, 0, 1, 1)"
        )
    engine.dispose()
    command.upgrade(cfg, "head")
    engine = make_engine(url)
    assert "sort_order" not in {c["name"] for c in inspect(engine).get_columns("quick_foods")}
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT quick_food_id FROM entries").scalar_one() == 1
    engine.dispose()
