"""Where workutil keeps its data, and where it listens.

The data directory is the unit of backup: everything workutil owns lives under
it, and nothing outside it is referenced from within, so copying the directory
copies the data (docs/design.md §5).
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

APP_NAME = "workutil"

#: workutil can open local files and (from M4) run arbitrary local Python, so it
#: must stay unreachable from the network. See requirements.md §5.
HOST = "127.0.0.1"
PORT = 8765

#: Set to point workutil at a different data directory — used by the tests, and
#: handy for keeping a separate scratch database while developing.
DATA_DIR_ENV_VAR = "WORKUTIL_DATA_DIR"

#: Set to point workutil at a custom frontend build directory.
UI_DIR_ENV_VAR = "WORKUTIL_UI_DIR"

#: Set to 1 to open the browser app window upon startup.
OPEN_WINDOW_ENV_VAR = "WORKUTIL_OPEN_WINDOW"

_APP_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _APP_DIR.parent.parent


def resolve_frontend_dist(
    environ: Mapping[str, str] | None = None,
    app_dir: Path | None = None,
) -> Path:
    """Find the frontend build directory across three possible layouts.

    Lookup order (first hit wins):
    1. WORKUTIL_UI_DIR environment variable
    2. Portable package layout: app/ sibling directory ui/
    3. Repository layout: <repo>/frontend/dist

    If none exist on disk, returns a non-existent path without throwing, so
    that development mode (where Vite serves the UI) continues to work.
    """
    env = os.environ if environ is None else environ
    base_app_dir = app_dir if app_dir is not None else _APP_DIR

    # 1. Environment variable override
    override = env.get(UI_DIR_ENV_VAR)
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_dir():
            return candidate

    # 2. Package layout: app/ sibling directory ui/
    package_candidate = base_app_dir.parent / "ui"
    if package_candidate.is_dir():
        return package_candidate

    # 3. Repository layout: <repo>/frontend/dist
    repo_candidate = base_app_dir.parent.parent / "frontend" / "dist"
    if repo_candidate.is_dir():
        return repo_candidate

    # None exist: return a non-existent path
    if override:
        return Path(override).expanduser()
    return repo_candidate


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    frontend_dist: Path = field(default_factory=resolve_frontend_dist)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "workutil.db"

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def database_url(self) -> str:
        return f"sqlite+pysqlite:///{self.db_path}"

    def create_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    override = os.environ.get(DATA_DIR_ENV_VAR)
    if override:
        return Settings(data_dir=Path(override).expanduser())
    platform_default = platformdirs.user_data_dir(APP_NAME, appauthor=False)
    return Settings(data_dir=Path(platform_default))
