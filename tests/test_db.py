from sqlalchemy import text

from app.db import make_engine


def test_sqlite_creates_parent_dir_and_enables_foreign_keys(tmp_path):
    url = f"sqlite:///{tmp_path / 'nested' / 'dev.db'}"
    engine = make_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert (tmp_path / "nested").is_dir()
    engine.dispose()
