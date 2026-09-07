from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import create_db_engine
from app.main import create_app


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """A throwaway data directory, standing in for the real one on disk."""
    return tmp_path / "workutil"


@contextmanager
def workutil_at(
    data_dir: Path, frontend_dist: Path | None = None
) -> Iterator[TestClient]:
    """Start workutil against a data directory, the way launching it would.

    `frontend_dist` stands in for a frontend build when a test cares about the
    UI being served; left out, `Settings` points at the real one.
    """
    settings = Settings(data_dir=data_dir)
    if frontend_dist is not None:
        settings = replace(settings, frontend_dist=frontend_dist)
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def client(data_dir: Path) -> Iterator[TestClient]:
    with workutil_at(data_dir) as client:
        yield client


@pytest.fixture
def session(client: TestClient, data_dir: Path) -> Iterator[Session]:
    """Direct access to the running application's database.

    Only for arranging state the HTTP API deliberately cannot express, such as
    a memo written long ago. Assertions still go through the API.
    """
    engine = create_db_engine(Settings(data_dir=data_dir))
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()
