import pytest

from app.kernel import db, migrate


@pytest.fixture
def session(tmp_path):
    """A session on a fresh database built from migrations."""
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    migrate.upgrade()
    with db.SessionLocal() as s:
        yield s
