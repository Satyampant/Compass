"""Alembic environment: migrate the database the app is configured for."""

from alembic import context

import app.models  # noqa: F401
from app.kernel import db

target_metadata = db.Base.metadata


def run() -> None:
    """Run migrations on a connection passed in, or on the app engine."""
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _migrate(connection)
        return
    with db.engine.begin() as conn:
        _migrate(conn)


def _migrate(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


run()
