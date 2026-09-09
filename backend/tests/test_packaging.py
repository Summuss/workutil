"""Tests verifying the contents and layout of built portable packages."""

import zipfile
from pathlib import Path

import pytest

from app.core.version import get_version

REPO_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = REPO_ROOT / "dist"


def test_windows_portable_package_structure() -> None:
    version = get_version()
    windows_zip = DIST_DIR / f"workutil-{version}-windows-x64.zip"
    if not windows_zip.is_file():
        pytest.skip(f"{windows_zip} does not exist yet (run make package first)")

    with zipfile.ZipFile(windows_zip, "r") as zf:
        names = set(zf.namelist())

        # Core required entries
        assert "workutil/app/__init__.py" in names
        assert "workutil/ui/index.html" in names
        assert "workutil/ui/favicon.ico" in names
        assert "workutil/ui/manifest.webmanifest" in names
        assert "workutil/site-packages/fastapi/__init__.py" in names
        assert "workutil/python/python.exe" in names
        assert "workutil/workutil.bat" in names
        assert "workutil/README.txt" in names

        # Migration scripts are included
        migrations = [
            n
            for n in names
            if n.startswith("workutil/app/migrations/versions/") and n.endswith(".py")
        ]
        assert len(migrations) > 0


def test_macos_portable_package_structure() -> None:
    version = get_version()
    macos_zip = DIST_DIR / f"workutil-{version}-macos-arm64.zip"
    if not macos_zip.is_file():
        pytest.skip(f"{macos_zip} does not exist yet (run make package first)")

    with zipfile.ZipFile(macos_zip, "r") as zf:
        names = set(zf.namelist())

        assert "workutil/app/__init__.py" in names
        assert "workutil/ui/index.html" in names
        assert "workutil/site-packages/fastapi/__init__.py" in names
        assert "workutil/python/bin/python3" in names
        assert "workutil/workutil.command" in names
        assert "workutil/README.txt" in names

        # Executable bit is preserved for .command launcher
        info = zf.getinfo("workutil/workutil.command")
        mode = info.external_attr >> 16
        assert (mode & 0o111) != 0, "workutil.command must be executable"
