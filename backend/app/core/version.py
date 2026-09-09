"""Application version resolution from pyproject.toml."""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _APP_DIR.parent.parent


def get_version() -> str:
    """Read version from pyproject.toml, falling back to importlib.metadata.

    Neither source is guaranteed: a portable package ships no pyproject.toml
    (ticket 04's bundle is `app/` + `site-packages/`, not a checkout), and an
    editable dev install may have no distribution metadata either. Both
    exceptions caught below are the specific ways each source is absent or
    unreadable — not a blanket `except Exception`, so an actual bug in this
    function still surfaces instead of quietly falling through to "0.1.0".
    """
    candidates = [
        _REPO_ROOT / "pyproject.toml",
        _APP_DIR.parent / "pyproject.toml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                with open(candidate, "rb") as f:
                    data = tomllib.load(f)
                    ver = data.get("project", {}).get("version")
                    if ver:
                        return str(ver)
            except (OSError, tomllib.TOMLDecodeError):
                pass

    try:
        return version("workutil")
    except PackageNotFoundError:
        pass

    return "0.1.0"
