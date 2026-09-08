"""What you can do with todos. Knows nothing about HTTP."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.todo.models import Todo

#: The ceiling on completed todos returned in the list. Same shape as memo's
#: `RECENT_MEMO_LIMIT`. Completed items can grow indefinitely, but only recent
#: ones are needed on screen. Unfinished todos have deliberately NO limit.
RECENT_COMPLETED_LIMIT = 200


class TodoNotFound(LookupError):
    """No todo has that id."""


class EmptyTitle(ValueError):
    """A todo must have a non-empty title."""


def _clean_title(raw_title: str) -> str:
    title = raw_title.strip()
    if not title:
        raise EmptyTitle("待办内容不能为空")
    return title


def get_todo(session: Session, todo_id: int) -> Todo:
    todo = session.get(Todo, todo_id)
    if todo is None:
        raise TodoNotFound(f"没有找到 id 为 {todo_id} 的待办")
    return todo


def create_todo(session: Session, raw_title: str) -> Todo:
    title = _clean_title(raw_title)
    now = utc_now()
    todo = Todo(
        title=title,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


def update_todo(session: Session, todo_id: int, raw_title: str | None = None) -> Todo:
    todo = get_todo(session, todo_id)
    if raw_title is not None:
        todo.title = _clean_title(raw_title)
    todo.updated_at = utc_now()
    session.commit()
    session.refresh(todo)
    return todo


def delete_todo(session: Session, todo_id: int) -> None:
    todo = get_todo(session, todo_id)
    session.delete(todo)
    session.commit()


def complete_todo(session: Session, todo_id: int) -> Todo:
    todo = get_todo(session, todo_id)
    if todo.completed_at is None:
        now = utc_now()
        todo.completed_at = now
        todo.updated_at = now
        session.commit()
        session.refresh(todo)
    return todo


def reopen_todo(session: Session, todo_id: int) -> Todo:
    todo = get_todo(session, todo_id)
    if todo.completed_at is not None:
        now = utc_now()
        todo.completed_at = None
        todo.updated_at = now
        session.commit()
        session.refresh(todo)
    return todo


def list_todos(session: Session) -> tuple[list[Todo], list[Todo]]:
    """Return all unfinished todos and recent completed todos."""
    unfinished_stmt = (
        select(Todo)
        .where(Todo.completed_at.is_(None))
        .order_by(Todo.created_at.asc(), Todo.id.asc())
    )
    completed_stmt = (
        select(Todo)
        .where(Todo.completed_at.is_not(None))
        .order_by(Todo.completed_at.desc(), Todo.id.desc())
        .limit(RECENT_COMPLETED_LIMIT)
    )
    todos = list(session.scalars(unfinished_stmt).all())
    completed = list(session.scalars(completed_stmt).all())
    return todos, completed
