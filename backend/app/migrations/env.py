"""Alembic entry point.

Runs either from the application at startup (which passes its own engine in
`config.attributes`) or from the `alembic` CLI while developing, which builds
one from the ambient settings.
"""

from typing import Any, Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import Engine

from app.core.config import load_settings
from app.core.db import UtcDateTime, create_db_engine, target_metadata


def render_item(
    type_: str, obj: Any, autogen_context: AutogenContext
) -> str | Literal[False]:
    """Write workutil's own column types out as their plain SQL equivalent.

    A migration is a historical record; it should keep working after the
    application class it was generated from is renamed or moved.
    """
    if type_ == "type" and isinstance(obj, UtcDateTime):
        return "sa.DateTime()"
    return False


def engine_to_migrate() -> Engine:
    from_application: Engine | None = context.config.attributes.get("engine")
    if from_application is not None:
        return from_application

    settings = load_settings()
    settings.create_directories()
    return create_db_engine(settings)


def run_migrations() -> None:
    engine = engine_to_migrate()

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata(),
            render_item=render_item,
            render_as_batch=True,  # SQLite cannot ALTER columns in place
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
