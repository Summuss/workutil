"""What the Memo API promises its users.

The HTTP boundary is the agreed test seam: these drive the real application
against a temporary data directory, and say nothing about how the module is
organised inside.
"""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.memo.models import Memo

from .conftest import workutil_at


def test_a_saved_memo_can_be_read_back_from_the_list(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "取消 timeout 的绕过办法"})
    assert created.status_code == 201

    listed = client.get("/api/memos")
    assert listed.status_code == 200
    assert [memo["body"] for memo in listed.json()] == ["取消 timeout 的绕过办法"]


def test_a_memo_keeps_its_body_verbatim(client: TestClient) -> None:
    body = "标题行\n\n```sh\ncurl -sS http://example.test/  # 复现命令\n```"

    created = client.post("/api/memos", json={"body": body}).json()

    assert created["body"] == body
    assert client.get("/api/memos").json()[0]["body"] == body


def test_the_newest_memo_comes_first(client: TestClient) -> None:
    for body in ("first", "second", "third"):
        client.post("/api/memos", json={"body": body})

    listed = client.get("/api/memos").json()

    assert [memo["body"] for memo in listed] == ["third", "second", "first"]


def test_the_order_follows_when_a_memo_was_written(
    client: TestClient, session: Session
) -> None:
    """An old memo stays low in the list however recently it was touched.

    This is what makes "I wrote that around last month" work as a way of
    finding things, and editing a memo must never disturb it. The old memo is
    written straight to the database because the API has no way to say
    "pretend I wrote this in 2020".
    """
    client.post("/api/memos", json={"body": "recent"})
    session.add(
        Memo(
            body="written long ago, edited just now",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            updated_at=utc_now(),
        )
    )
    session.commit()

    listed = client.get("/api/memos").json()

    assert [memo["body"] for memo in listed] == [
        "recent",
        "written long ago, edited just now",
    ]


def test_memos_created_in_the_same_instant_still_have_a_stable_order(
    client: TestClient,
) -> None:
    """Two memos saved back to back must not swap places between requests."""
    for body in ("first", "second"):
        client.post("/api/memos", json={"body": body})

    def ids_in_list() -> list[int]:
        return [memo["id"] for memo in client.get("/api/memos").json()]

    orders = [ids_in_list() for _ in range(5)]

    assert orders == [orders[0]] * 5


def test_memos_survive_a_restart(data_dir: Path) -> None:
    with workutil_at(data_dir) as before:
        before.post("/api/memos", json={"body": "survives"})

    with workutil_at(data_dir) as after:
        assert [memo["body"] for memo in after.get("/api/memos").json()] == ["survives"]


def test_a_memo_has_no_title_of_its_own(client: TestClient) -> None:
    """A memo is body-only; the first line shown in the list is the caller's
    business, not a stored field. See spec 领域模型."""
    created = client.post("/api/memos", json={"body": "首行\n第二行"}).json()

    assert "title" not in created
    assert "title" not in client.get("/api/memos").json()[0]


def test_a_memo_records_when_it_was_created_and_last_changed(
    client: TestClient,
) -> None:
    created = client.post("/api/memos", json={"body": "记一笔"}).json()

    assert created["created_at"] == created["updated_at"]
    assert created["created_at"].endswith("Z") or "+00:00" in created["created_at"]


def test_an_empty_memo_is_refused(client: TestClient) -> None:
    for body in ("", "   ", "\n\t "):
        assert client.post("/api/memos", json={"body": body}).status_code == 422

    assert client.get("/api/memos").json() == []


def test_a_single_memo_can_be_read_by_id(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "详细内容"}).json()
    memo_id = created["id"]

    response = client.get(f"/api/memos/{memo_id}")
    assert response.status_code == 200
    memo = response.json()
    assert memo["id"] == memo_id
    assert memo["body"] == "详细内容"
    assert memo["created_at"] == created["created_at"]
    assert memo["updated_at"] == created["updated_at"]


def test_reading_a_nonexistent_memo_returns_404(client: TestClient) -> None:
    response = client.get("/api/memos/999999")
    assert response.status_code == 404


def test_a_memo_body_can_be_updated(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "旧内容"}).json()
    memo_id = created["id"]

    response = client.patch(f"/api/memos/{memo_id}", json={"body": "新内容"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == memo_id
    assert updated["body"] == "新内容"

    read_back = client.get(f"/api/memos/{memo_id}").json()
    assert read_back["body"] == "新内容"


def test_updating_a_memo_updates_timestamp_while_preserving_creation_time(
    client: TestClient,
) -> None:
    created = client.post("/api/memos", json={"body": "原始内容"}).json()
    memo_id = created["id"]

    updated = client.patch(
        f"/api/memos/{memo_id}", json={"body": "修改后的内容"}
    ).json()

    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] >= created["updated_at"]


def test_updating_a_nonexistent_memo_returns_404(client: TestClient) -> None:
    response = client.patch("/api/memos/999999", json={"body": "something"})
    assert response.status_code == 404


def test_updating_a_memo_to_empty_body_is_refused(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "不可被改为空"}).json()
    memo_id = created["id"]

    for body in ("", "   ", "\n\t "):
        assert (
            client.patch(
                f"/api/memos/{memo_id}", json={"body": body}
            ).status_code
            == 422
        )

    assert client.get(f"/api/memos/{memo_id}").json()["body"] == "不可被改为空"


def test_editing_an_old_memo_does_not_change_its_position_in_the_list(
    client: TestClient, session: Session
) -> None:
    """Editing an old memo must not drag it to the top.

    Sorting is strictly by created_at desc, never updated_at.
    """
    client.post("/api/memos", json={"body": "newer memo"})
    session.add(
        Memo(
            body="older memo original",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            updated_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
    )
    session.commit()

    old_memo_id = session.scalars(
        select(Memo).where(Memo.body == "older memo original")
    ).one().id

    client.patch(
        f"/api/memos/{old_memo_id}", json={"body": "older memo updated"}
    )

    listed = client.get("/api/memos").json()
    assert [memo["body"] for memo in listed] == [
        "newer memo",
        "older memo updated",
    ]


def test_a_memo_stores_and_returns_html_verbatim(client: TestClient) -> None:
    """HTML and scripts are preserved as-is at the storage and API boundary.

    Safety is the frontend markdown renderer's responsibility (it disables
    raw HTML execution). The backend does not strip or tamper with user text.
    """
    html_body = (
        '<script>alert("xss")</script><img src="x" onerror="evil()"><p>原生标签</p>'
    )
    created = client.post("/api/memos", json={"body": html_body}).json()
    memo_id = created["id"]

    assert created["body"] == html_body
    assert client.get(f"/api/memos/{memo_id}").json()["body"] == html_body
    assert client.get("/api/memos").json()[0]["body"] == html_body

    updated_html = '<div class="test"><script>console.log(1)</script></div>'
    updated = client.patch(
        f"/api/memos/{memo_id}", json={"body": updated_html}
    ).json()
    assert updated["body"] == updated_html
    assert client.get(f"/api/memos/{memo_id}").json()["body"] == updated_html

