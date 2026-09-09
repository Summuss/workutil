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
        body = response.json()
        assert body.get("code") == "todo.empty_title"


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
            order=i,
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
            order=i,
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


def test_new_todos_appended_at_end(client: TestClient) -> None:
    todo_a = client.post("/api/todos", json={"title": "A"}).json()
    todo_b = client.post("/api/todos", json={"title": "B"}).json()
    todo_c = client.post("/api/todos", json={"title": "C"}).json()

    assert todo_a["order"] == 0
    assert todo_b["order"] == 1
    assert todo_c["order"] == 2

    listed = client.get("/api/todos").json()["todos"]
    assert [t["title"] for t in listed] == ["A", "B", "C"]


def test_move_todo_absolute_and_boundary(client: TestClient) -> None:
    client.post("/api/todos", json={"title": "A"})
    client.post("/api/todos", json={"title": "B"})
    todo_c = client.post("/api/todos", json={"title": "C"}).json()

    # Move C to top -> [C, A, B]
    resp = client.post(f"/api/todos/{todo_c['id']}/move", json={"to": "top"})
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert titles == ["C", "A", "B"]
    orders = [t["order"] for t in resp.json()]
    assert orders == [0, 1, 2]

    # Move C to middle (index 1) -> [A, C, B]
    resp = client.post(f"/api/todos/{todo_c['id']}/move", json={"to": 1})
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["A", "C", "B"]

    # Move C to same position (index 1) -> [A, C, B] (no change)
    resp = client.post(f"/api/todos/{todo_c['id']}/move", json={"to": 1})
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["A", "C", "B"]

    # Move C to bottom -> [A, B, C]
    resp = client.post(f"/api/todos/{todo_c['id']}/move", json={"to": "bottom"})
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["A", "B", "C"]

    # Boundary moves: moving to -1 clamps to 0 (top) -> [C, A, B]
    resp = client.post(f"/api/todos/{todo_c['id']}/move", json={"to": -1})
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["C", "A", "B"]

    # Moving to 999 clamps to end -> [A, B, C]
    resp = client.post(f"/api/todos/{todo_c['id']}/move", json={"to": 999})
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["A", "B", "C"]

    # Refuse deprecated "up" / "down"
    for invalid in ("up", "down", "sideways"):
        res = client.post(f"/api/todos/{todo_c['id']}/move", json={"to": invalid})
        assert res.status_code == 422


def test_cannot_move_completed_todo(client: TestClient) -> None:
    todo_a = client.post("/api/todos", json={"title": "A"}).json()
    client.post(f"/api/todos/{todo_a['id']}/complete")

    resp = client.post(f"/api/todos/{todo_a['id']}/move", json={"to": "top"})
    assert resp.status_code == 400
    assert "已完成" in resp.json()["detail"]


def test_move_nonexistent_todo(client: TestClient) -> None:
    resp = client.post("/api/todos/99999/move", json={"to": "top"})
    assert resp.status_code == 404


def test_delete_todo_renumbers_remaining(client: TestClient) -> None:
    client.post("/api/todos", json={"title": "A"})
    todo_b = client.post("/api/todos", json={"title": "B"}).json()
    client.post("/api/todos", json={"title": "C"})

    # Delete middle todo B
    client.delete(f"/api/todos/{todo_b['id']}")

    listed = client.get("/api/todos").json()["todos"]
    assert len(listed) == 2
    assert listed[0]["title"] == "A"
    assert listed[0]["order"] == 0
    assert listed[1]["title"] == "C"
    assert listed[1]["order"] == 1


def test_complete_and_reopen_preserves_order_and_position(client: TestClient) -> None:
    """Main seam test for Ticket 02:

    When a todo is completed, its order is UNTOUCHED.
    When reopened, it returns to its exact original place in the list.
    """
    todo_a = client.post("/api/todos", json={"title": "A"}).json()
    client.post("/api/todos", json={"title": "B"})
    todo_c = client.post("/api/todos", json={"title": "C"}).json()

    # Initial order: A (0), B (1), C (2)
    # Reorder so C is first: [C (0), A (1), B (2)]
    client.post(f"/api/todos/{todo_c['id']}/move", json={"to": "top"})

    # Complete middle todo A: order remains 1!
    client.post(f"/api/todos/{todo_a['id']}/complete")

    # Active list now only shows C and B
    active = client.get("/api/todos").json()["todos"]
    assert [t["title"] for t in active] == ["C", "B"]

    # Reopen A: returns back between C and B, exactly in place!
    client.post(f"/api/todos/{todo_a['id']}/reopen")

    reopened_active = client.get("/api/todos").json()["todos"]
    assert [t["title"] for t in reopened_active] == ["C", "A", "B"]
    assert [t["order"] for t in reopened_active] == [0, 1, 2]


def test_create_todo_with_due_date(client: TestClient) -> None:
    resp = client.post("/api/todos", json={"title": "买书", "due_date": "2026-09-15"})
    assert resp.status_code == 201
    assert resp.json()["due_date"] == "2026-09-15"


def test_patch_todo_set_and_clear_due_date(client: TestClient) -> None:
    created = client.post("/api/todos", json={"title": "看文档"}).json()
    todo_id = created["id"]
    assert created["due_date"] is None

    # Set due date
    patch_resp = client.patch(f"/api/todos/{todo_id}", json={"due_date": "2026-09-20"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["due_date"] == "2026-09-20"

    # Patch title only; due_date should remain untouched
    patch_title = client.patch(f"/api/todos/{todo_id}", json={"title": "新看文档"})
    assert patch_title.status_code == 200
    assert patch_title.json()["title"] == "新看文档"
    assert patch_title.json()["due_date"] == "2026-09-20"

    # Clear due date by sending null
    clear_resp = client.patch(f"/api/todos/{todo_id}", json={"due_date": None})
    assert clear_resp.status_code == 200
    assert clear_resp.json()["due_date"] is None


def test_ordering_is_independent_of_due_date(client: TestClient) -> None:
    """Main seam test for Ticket 03:

    Two todos with different due_dates (e.g. future vs overdue) have their
    order determined solely by `order`, not by their deadline.
    """
    todo_future = client.post(
        "/api/todos", json={"title": "未来待办", "due_date": "2026-12-31"}
    ).json()
    todo_overdue = client.post(
        "/api/todos", json={"title": "逾期待办", "due_date": "2026-01-01"}
    ).json()

    # Created order: future is 0, overdue is 1
    listed = client.get("/api/todos").json()["todos"]
    assert [t["title"] for t in listed] == ["未来待办", "逾期待办"]

    # Move overdue todo to top -> now overdue is first
    client.post(f"/api/todos/{todo_overdue['id']}/move", json={"to": "top"})
    listed_after_move = client.get("/api/todos").json()["todos"]
    assert [t["title"] for t in listed_after_move] == ["逾期待办", "未来待办"]
    assert listed_after_move[0]["id"] == todo_overdue["id"]
    assert listed_after_move[1]["id"] == todo_future["id"]


def test_create_todo_with_source_memo_id(client: TestClient) -> None:
    memo = client.post("/api/memos", json={"body": "来自会议纪要的待办"}).json()
    resp = client.post(
        "/api/todos",
        json={"title": "会议待办", "source_memo_id": memo["id"]},
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["title"] == "会议待办"
    assert created["source_memo_id"] == memo["id"]


def test_todo_with_deleted_memo_still_listed(client: TestClient) -> None:
    """Main seam test for Ticket 04:

    When the original memo is deleted, the todo is STILL normally listed,
    without any foreign key violation or missing rows, but without a backlink
    (source_memo_id resolved as None).
    """
    memo = client.post("/api/memos", json={"body": "临时记录备忘"}).json()
    memo_id = memo["id"]

    todo = client.post(
        "/api/todos",
        json={"title": "从备忘转出的待办", "source_memo_id": memo_id},
    ).json()
    todo_id = todo["id"]

    # Delete the source memo
    del_resp = client.delete(f"/api/memos/{memo_id}")
    assert del_resp.status_code == 204

    # Todo list is still 200 OK, todo is present, without backlink
    listed_resp = client.get("/api/todos")
    assert listed_resp.status_code == 200
    todos = listed_resp.json()["todos"]

    match = next((t for t in todos if t["id"] == todo_id), None)
    assert match is not None
    assert match["title"] == "从备忘转出的待办"
    assert match["source_memo_id"] is None
