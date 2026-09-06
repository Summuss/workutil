"""SQLite plumbing shared by every module."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import DateTime, Engine, create_engine
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import Settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


class Base(DeclarativeBase):
    pass


class UtcDateTime(TypeDecorator[datetime]):
    """A timestamp that stays in UTC across a SQLite round trip.

    SQLite has no timezone-aware type, so an aware datetime would come back
    naive and be read as local time. This stores UTC and hands back UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def migrate_to_head(engine: Engine) -> None:
    """Bring the database up to the latest schema, creating it if absent.

    The engine is handed over directly rather than as a URL, so data
    directories with awkward characters in their path cannot trip over
    Alembic's ini interpolation.
    """
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["engine"] = engine
    command.upgrade(config, "head")


def target_metadata() -> Any:
    """Metadata for Alembic autogenerate, with every module's tables registered."""
    import app.modules.registry  # noqa: F401  — importing registers the ORM models

    return Base.metadata
