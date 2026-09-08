"""Bookmark — entry to a local file or directory. See CONTEXT.md."""

from app.modules.bookmark import models as models  # noqa: F401  — registers ORM tables
from app.modules.bookmark.router import router as bookmark_router

__all__ = ["bookmark_router"]
