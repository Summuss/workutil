"""Where workutil keeps its data, and where it listens.

The data directory is the unit of backup: everything workutil owns lives under
it, and nothing outside it is referenced from within, so copying the directory
copies the data (docs/design.md §5).
"""

import os
from dataclasses import dataclass
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

_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    frontend_dist: Path = _REPO_ROOT / "frontend" / "dist"

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
