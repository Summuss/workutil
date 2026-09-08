"""HTTP tests for Todo API.

The HTTP boundary is the agreed test seam: these drive the real application
against a temporary data directory and test all required behaviors for Ticket 01.
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.todo.models import Todo
from app.modules.todo.service import RECENT_COMPLETED_LIMIT


def test_create_todo(client: TestClient) -> None:
    response = client.post("/api/todos", json={"title": "买牛奶"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "买牛奶"
    assert data["completed_at"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_todo_strips_whitespace(client: TestClient) -> None:
    response = client.post("/api/todos", json={"title": "  写单元测试  \n"})
    assert response.status_code == 201
    assert response.json()["title"] == "写单元测试"


def test_create_todo_refuses_empty_title(client: TestClient) -> None:
    for empty in ("", "   ", "\t\n"):
        response = client.post("/api/todos", json={"title": empty})
        assert response.status_code == 422
        assert "待办" in response.json()["detail"]


def test_list_todos_empty(client: TestClient) -> None:
    response = client.get("/api/todos")
    assert response.status_code == 200
    assert response.json() == {"todos": [], "completed": []}


def test_update_todo_title(client: TestClient) -> None:
    created = client.post("/api/todos", json={"title": "旧标题"}).json()
    todo_id = created["id"]

    response = client.patch(f"/api/todos/{todo_id}", json={"title": "新标题"})
    assert response.status_code == 200
    assert response.json()["title"] == "新标题"

    listed = client.get("/api/todos").json()
    assert listed["todos"][0]["title"] == "新标题"


def test_update_todo_refuses_empty_title(client: TestClient) -> None:
    created = client.post("/api/todos", json={"title": "原标题"}).json()
    todo_id = created["id"]

    response = client.patch(f"/api/todos/{todo_id}", json={"title": "   "})
    assert response.status_code == 422

    # Unchanged
    todo = client.get("/api/todos").json()["todos"][0]
    assert todo["title"] == "原标题"


def test_update_nonexistent_todo(client: TestClient) -> None:
    response = client.patch("/api/todos/99999", json={"title": "测试"})
    assert response.status_code == 404


def test_delete_todo(client: TestClient) -> None:
    created = client.post("/api/todos", json={"title": "待删除"}).json()
    todo_id = created["id"]

    response = client.delete(f"/api/todos/{todo_id}")
    assert response.status_code == 204

    listed = client.get("/api/todos").json()
    assert len(listed["todos"]) == 0

    # Deleting again returns 404
    second_delete = client.delete(f"/api/todos/{todo_id}")
    assert second_delete.status_code == 404


def test_complete_and_reopen_todo(client: TestClient) -> None:
    created = client.post("/api/todos", json={"title": "做晚饭"}).json()
    todo_id = created["id"]

    # Mark as complete
    complete_resp = client.post(f"/api/todos/{todo_id}/complete")
    assert complete_resp.status_code == 200
    completed_data = complete_resp.json()
    assert completed_data["completed_at"] is not None

    # Check list: now in completed, removed from active todos
    listed = client.get("/api/todos").json()
    assert len(listed["todos"]) == 0
    assert len(listed["completed"]) == 1
    assert listed["completed"][0]["id"] == todo_id
    assert listed["completed"][0]["completed_at"] is not None

    # Reopen
    reopen_resp = client.post(f"/api/todos/{todo_id}/reopen")
    assert reopen_resp.status_code == 200
    reopened_data = reopen_resp.json()
    assert reopened_data["completed_at"] is None

    # Check list again: returned to active todos
    listed_again = client.get("/api/todos").json()
    assert len(listed_again["todos"]) == 1
    assert len(listed_again["completed"]) == 0
    assert listed_again["todos"][0]["id"] == todo_id


def test_complete_nonexistent_todo(client: TestClient) -> None:
    response = client.post("/api/todos/99999/complete")
    assert response.status_code == 404


def test_reopen_nonexistent_todo(client: TestClient) -> None:
    response = client.post("/api/todos/99999/reopen")
    assert response.status_code == 404


def test_unfinished_todos_unlimited_and_completed_todos_capped(
    client: TestClient, session: Session
) -> None:
    """Main seam test:

    - Unfinished todos return all items without limit (invisible tasks = lost tasks)
    - Completed todos are capped at RECENT_COMPLETED_LIMIT (200), newest first
    """
    now = utc_now()

    # Create RECENT_COMPLETED_LIMIT + 10 unfinished todos
    extra = 10
    total_unfinished = RECENT_COMPLETED_LIMIT + extra
    unfinished_rows = [
        Todo(
            title=f"未完成待办 {i}",
            created_at=now + timedelta(seconds=i),
            updated_at=now + timedelta(seconds=i),
            completed_at=None,
        )
        for i in range(total_unfinished)
    ]
    session.add_all(unfinished_rows)

    # Create RECENT_COMPLETED_LIMIT + 10 completed todos
    total_completed = RECENT_COMPLETED_LIMIT + extra
    completed_rows = [
        Todo(
            title=f"已完成待办 {i}",
            created_at=now + timedelta(seconds=i),
            updated_at=now + timedelta(seconds=i),
            completed_at=now + timedelta(seconds=i),
        )
        for i in range(total_completed)
    ]
    session.add_all(completed_rows)
    session.commit()

    # Query via API
    resp = client.get("/api/todos")
    assert resp.status_code == 200
    data = resp.json()

    # Unfinished: ALL items returned
    assert len(data["todos"]) == total_unfinished
    assert data["todos"][0]["title"] == "未完成待办 0"
    assert data["todos"][-1]["title"] == f"未完成待办 {total_unfinished - 1}"

    # Completed: exactly RECENT_COMPLETED_LIMIT returned, ordered by completed_at desc
    assert len(data["completed"]) == RECENT_COMPLETED_LIMIT
    # Most recently completed is at index 0
    assert data["completed"][0]["title"] == f"已完成待办 {total_completed - 1}"
