"""Every feature workutil has.

Adding a feature is a directory under `modules/` and one line here — that is
the whole cost, and keeping it that way is this project's first constraint
(requirements.md §5).
"""

from fastapi import APIRouter

from app.modules.memo import memo_router

ROUTERS: tuple[APIRouter, ...] = (memo_router,)
