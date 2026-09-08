"""HTTP for todos.

Forwarding only — the behaviour lives in service.py.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import SessionDep
from app.modules.todo import service
from app.modules.todo.schemas import (
    TodoCreate,
    TodoListResponse,
    TodoRead,
    TodoUpdate,
)

router = APIRouter(prefix="/todos", tags=["todo"])


@router.post(
    "",
    response_model=TodoRead,
    status_code=status.HTTP_201_CREATED,
)
def create_todo(payload: TodoCreate, session: SessionDep) -> TodoRead:
    try:
        todo = service.create_todo(session, payload.title)
    except service.EmptyTitle as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return TodoRead.model_validate(todo)


@router.get("", response_model=TodoListResponse)
def list_todos(session: SessionDep) -> TodoListResponse:
    todos, completed = service.list_todos(session)
    return TodoListResponse(
        todos=[TodoRead.model_validate(t) for t in todos],
        completed=[TodoRead.model_validate(t) for t in completed],
    )


@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo(todo_id: int, payload: TodoUpdate, session: SessionDep) -> TodoRead:
    try:
        todo = service.update_todo(session, todo_id, payload.title)
    except service.TodoNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.EmptyTitle as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return TodoRead.model_validate(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, session: SessionDep) -> None:
    try:
        service.delete_todo(session, todo_id)
    except service.TodoNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err


@router.post("/{todo_id}/complete", response_model=TodoRead)
def complete_todo(todo_id: int, session: SessionDep) -> TodoRead:
    try:
        todo = service.complete_todo(session, todo_id)
    except service.TodoNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    return TodoRead.model_validate(todo)


@router.post("/{todo_id}/reopen", response_model=TodoRead)
def reopen_todo(todo_id: int, session: SessionDep) -> TodoRead:
    try:
        todo = service.reopen_todo(session, todo_id)
    except service.TodoNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    return TodoRead.model_validate(todo)
