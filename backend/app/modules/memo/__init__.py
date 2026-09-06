"""Memo — a scrap of information saved in one go. See CONTEXT.md."""

from app.modules.memo import models as models  # noqa: F401  — registers ORM tables
from app.modules.memo.router import router as memo_router

__all__ = ["memo_router"]
