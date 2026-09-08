import base64
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import create_db_engine
from app.core.platform import Platform
from app.main import create_app
from tests.fake_platform import FakePlatform


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """A throwaway data directory, standing in for the real one on disk."""
    return tmp_path / "workutil"


@pytest.fixture
def fake_platform() -> FakePlatform:
    """A fake platform that records calls, substitutable into tests."""
    return FakePlatform()


@contextmanager
def workutil_at(
    data_dir: Path,
    frontend_dist: Path | None = None,
    platform: Platform | None = None,
) -> Iterator[TestClient]:
    """Start workutil against a data directory, the way launching it would.

    `frontend_dist` stands in for a frontend build when a test cares about the
    UI being served; left out, `Settings` points at the real one.
    """
    settings = Settings(data_dir=data_dir)
    if frontend_dist is not None:
        settings = replace(settings, frontend_dist=frontend_dist)
    with TestClient(create_app(settings, platform=platform)) as client:
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


#: Two real PNGs, one pixel and four. Small enough to sit in the source, and
#: real enough that anything reading them back gets an actual image — Memo and
#: Evidence both paste screenshots, so the sample lives here rather than in
#: either one's tests.
SAMPLE_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
    b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
SAMPLE_PNG_2 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02"
    b"\x08\x06\x00\x00\x00v\x28\xb5g\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


def data_url(raw: bytes) -> str:
    """Image bytes as the browser hands them over: a base64 data URL."""
    return "data:image/png;base64," + base64.b64encode(raw).decode()
