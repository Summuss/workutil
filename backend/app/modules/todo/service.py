"""What you can do with todos. Knows nothing about HTTP."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.core.ordering import Move, renumber, reorder
from app.modules.todo.models import Todo

#: The ceiling on completed todos returned in the list. Same shape as memo's
#: `RECENT_MEMO_LIMIT`. Completed items can grow indefinitely, but only recent
#: ones are needed on screen. Unfinished todos have deliberately NO limit.
RECENT_COMPLETED_LIMIT = 200


class TodoNotFound(LookupError):
    """No todo has that id."""

    code = "todo.not_found"


class EmptyTitle(ValueError):
    """A todo must have a non-empty title."""

    code = "todo.empty_title"


class CannotMoveCompletedTodo(ValueError):
    """A completed todo cannot be moved."""

    code = "todo.cannot_move_completed"


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


def _unfinished_todos_in_order(session: Session) -> list[Todo]:
    stmt = select(Todo).where(Todo.completed_at.is_(None)).order_by(Todo.order, Todo.id)
    return list(session.scalars(stmt).all())


def create_todo(
    session: Session,
    raw_title: str,
    description: str = "",
    due_date: date | None = None,
) -> Todo:
    title = _clean_title(raw_title)
    unfinished = _unfinished_todos_in_order(session)
    order = (unfinished[-1].order + 1) if unfinished else 0
    now = utc_now()
    todo = Todo(
        title=title,
        description=description,
        order=order,
        due_date=due_date,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


def update_todo(
    session: Session,
    todo_id: int,
    raw_title: str | None = None,
    description: str | None = None,
    due_date: date | None = None,
    update_due_date: bool = False,
) -> Todo:
    todo = get_todo(session, todo_id)
    if raw_title is not None:
        todo.title = _clean_title(raw_title)
    if description is not None:
        todo.description = description
    if update_due_date:
        todo.due_date = due_date
    todo.updated_at = utc_now()
    session.commit()
    session.refresh(todo)
    return todo


def delete_todo(session: Session, todo_id: int) -> None:
    todo = get_todo(session, todo_id)
    was_unfinished = todo.completed_at is None
    session.delete(todo)
    session.flush()
    if was_unfinished:
        renumber(_unfinished_todos_in_order(session))
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


def move_todo(session: Session, todo_id: int, to: Move | int) -> list[Todo]:
    todo = get_todo(session, todo_id)
    if todo.completed_at is not None:
        raise CannotMoveCompletedTodo("已完成的待办不能移动")
    unfinished = _unfinished_todos_in_order(session)
    reordered = reorder(unfinished, todo, to)
    session.commit()
    return reordered


def list_todos(session: Session) -> tuple[list[Todo], list[Todo]]:
    """Return all unfinished todos and recent completed todos."""
    todos = _unfinished_todos_in_order(session)
    completed_stmt = (
        select(Todo)
        .where(Todo.completed_at.is_not(None))
        .order_by(Todo.completed_at.desc(), Todo.id.desc())
        .limit(RECENT_COMPLETED_LIMIT)
    )
    completed = list(session.scalars(completed_stmt).all())
    return todos, completed
