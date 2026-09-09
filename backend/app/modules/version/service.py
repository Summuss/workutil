"""Reading the app's own version — the router/service split every other
module here has, even though the actual work is a one-liner.

The reason it's a one-liner is that the real logic lives in
`app.core.version`, not here: `scripts/build_packages.py` needs the same
version string outside of any FastAPI context (to name the zip it builds),
so it can't live behind this module's router. This file exists so a request
for "/version" still goes through the same router → service shape as every
other endpoint, rather than the router reaching into core/ directly.

No models.py: this module owns no database table, so there is nothing to
model.
"""

from app.core.version import get_version as get_version

__all__ = ["get_version"]
