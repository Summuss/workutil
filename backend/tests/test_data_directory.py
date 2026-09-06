"""The data directory is the backup story: copy it and you have everything."""

import ipaddress
import shutil
from pathlib import Path

from app.core.config import HOST, Settings

from .conftest import workutil_at


def test_the_database_and_the_images_sit_side_by_side(data_dir: Path) -> None:
    settings = Settings(data_dir=data_dir)
    with workutil_at(data_dir):
        pass

    assert settings.db_path.parent == data_dir
    assert settings.images_dir.parent == data_dir
    assert settings.db_path.is_file()
    assert settings.images_dir.is_dir()


def test_copying_the_directory_copies_the_memos(data_dir: Path, tmp_path: Path) -> None:
    with workutil_at(data_dir) as client:
        client.post("/api/memos", json={"body": "记在原目录里"})

    backup = tmp_path / "backup"
    shutil.copytree(data_dir, backup)

    with workutil_at(backup) as restored:
        listed = restored.get("/api/memos").json()

    assert [memo["body"] for memo in listed] == ["记在原目录里"]


def test_the_service_is_only_reachable_from_this_machine() -> None:
    """Guard for requirements.md 非功能需求 (安全): workutil grows the ability to
    run arbitrary local code, so it must never listen on a routable address."""
    assert ipaddress.ip_address(HOST).is_loopback
