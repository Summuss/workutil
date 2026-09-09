from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.ordering import MoveRequest as MoveRequest


class TodoCreate(BaseModel):
    title: str
    due_date: date | None = None
    source_memo_id: int | None = None


class TodoUpdate(BaseModel):
    title: str | None = None
    due_date: date | None = None


class TodoRead(BaseModel):
    """A todo as the list and editor see it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    order: int
    due_date: date | None = None
    source_memo_id: int | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TodoListResponse(BaseModel):
    """GET /api/todos returns all unfinished todos and recent completed todos."""

    todos: list[TodoRead]
    completed: list[TodoRead]
