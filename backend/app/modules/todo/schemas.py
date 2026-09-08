from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TodoCreate(BaseModel):
    title: str


class TodoUpdate(BaseModel):
    title: str | None = None


class TodoRead(BaseModel):
    """A todo as the list and editor see it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TodoListResponse(BaseModel):
    """GET /api/todos returns all unfinished todos and recent completed todos."""

    todos: list[TodoRead]
    completed: list[TodoRead]
