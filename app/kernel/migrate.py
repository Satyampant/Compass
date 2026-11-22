"""Bring the configured database up to the latest migration."""

from alembic import command
from alembic.config import Config

from app.kernel.db import ROOT


def upgrade() -> None:
    """Apply all migrations to the app engine."""
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
