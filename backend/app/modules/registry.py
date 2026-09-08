"""Every feature workutil has.

Adding a feature is a directory under `modules/` and one line here — that is
the whole cost, and keeping it that way is this project's first constraint
(requirements.md §5).
"""

from fastapi import APIRouter

from app.modules.bookmark import bookmark_router
from app.modules.evidence import evidence_router
from app.modules.memo import memo_router
from app.modules.todo import todo_router

ROUTERS: tuple[APIRouter, ...] = (
    memo_router,
    evidence_router,
    bookmark_router,
    todo_router,
)
