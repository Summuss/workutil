"""Todo — a single task to be done. See CONTEXT.md."""

from app.modules.todo import models as models  # noqa: F401  — registers ORM tables
from app.modules.todo.router import router as todo_router

__all__ = ["todo_router"]
