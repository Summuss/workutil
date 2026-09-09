"""Application version resolution from pyproject.toml."""

import tomllib
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _APP_DIR.parent.parent


def get_version() -> str:
    """Read version from pyproject.toml, falling back to importlib.metadata."""
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
            except Exception:
                pass

    try:
        from importlib.metadata import version

        return version("workutil")
    except Exception:
        pass

    return "0.1.0"
