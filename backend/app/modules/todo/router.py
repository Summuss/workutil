"""HTTP for todos.

Forwarding only — the behaviour lives in service.py.
"""

from fastapi import APIRouter, status

from app.core.deps import SessionDep
from app.core.errors import http_error
from app.modules.todo import service
from app.modules.todo.models import Todo
from app.modules.todo.schemas import (
    MoveRequest,
    TodoCreate,
    TodoListResponse,
    TodoRead,
    TodoUpdate,
)

router = APIRouter(prefix="/todos", tags=["todo"])


def _to_read(todo: Todo) -> TodoRead:
    return TodoRead.model_validate(todo)


@router.post(
    "",
    response_model=TodoRead,
    status_code=status.HTTP_201_CREATED,
)
def create_todo(payload: TodoCreate, session: SessionDep) -> TodoRead:
    try:
        todo = service.create_todo(
            session,
            payload.title,
            description=payload.description,
            due_date=payload.due_date,
        )
    except service.EmptyTitle as err:
        raise http_error(status.HTTP_422_UNPROCESSABLE_CONTENT, err) from err
    return _to_read(todo)


@router.get("", response_model=TodoListResponse)
def list_todos(session: SessionDep) -> TodoListResponse:
    todos, completed = service.list_todos(session)
    return TodoListResponse(
        todos=[_to_read(t) for t in todos],
        completed=[_to_read(t) for t in completed],
    )


@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo(todo_id: int, payload: TodoUpdate, session: SessionDep) -> TodoRead:
    update_due_date = "due_date" in payload.model_fields_set
    try:
        todo = service.update_todo(
            session,
            todo_id,
            raw_title=payload.title,
            description=payload.description,
            due_date=payload.due_date,
            update_due_date=update_due_date,
        )
    except service.TodoNotFound as err:
        raise http_error(status.HTTP_404_NOT_FOUND, err) from err
    except service.EmptyTitle as err:
        raise http_error(status.HTTP_422_UNPROCESSABLE_CONTENT, err) from err
    return _to_read(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, session: SessionDep) -> None:
    try:
        service.delete_todo(session, todo_id)
    except service.TodoNotFound as err:
        raise http_error(status.HTTP_404_NOT_FOUND, err) from err


@router.post("/{todo_id}/complete", response_model=TodoRead)
def complete_todo(todo_id: int, session: SessionDep) -> TodoRead:
    try:
        todo = service.complete_todo(session, todo_id)
    except service.TodoNotFound as err:
        raise http_error(status.HTTP_404_NOT_FOUND, err) from err
    return _to_read(todo)


@router.post("/{todo_id}/reopen", response_model=TodoRead)
def reopen_todo(todo_id: int, session: SessionDep) -> TodoRead:
    try:
        todo = service.reopen_todo(session, todo_id)
    except service.TodoNotFound as err:
        raise http_error(status.HTTP_404_NOT_FOUND, err) from err
    return _to_read(todo)


@router.post("/{todo_id}/move", response_model=list[TodoRead])
def move_todo(
    todo_id: int, payload: MoveRequest, session: SessionDep
) -> list[TodoRead]:
    try:
        reordered = service.move_todo(session, todo_id, payload.to)
    except service.TodoNotFound as err:
        raise http_error(status.HTTP_404_NOT_FOUND, err) from err
    except service.CannotMoveCompletedTodo as err:
        raise http_error(status.HTTP_400_BAD_REQUEST, err) from err
    return [_to_read(t) for t in reordered]
