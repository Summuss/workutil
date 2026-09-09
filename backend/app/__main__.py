"""The workutil entry point when executed as `python -m app`."""

import sys

from app.main import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())
