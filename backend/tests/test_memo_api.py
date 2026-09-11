"""What the Memo API promises its users.

The HTTP boundary is the agreed test seam: these drive the real application
against a temporary data directory, and say nothing about how the module is
organised inside.
"""

import base64
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.memo.models import Memo
from app.modules.memo.service import RECENT_MEMO_LIMIT

from .conftest import SAMPLE_PNG, SAMPLE_PNG_2, workutil_at


def image_urls(body: str) -> list[str]:
    """Where a saved body points at its screenshots, in the order it names them.

    Read out of the body rather than written down: the name a screenshot is
    stored under carries a token so that no name is ever handed out twice
    (`core/images.next_name`), and is therefore deliberately unpredictable. A
    test that spelled the name out would be asserting the one thing about it
    that is not promised.
    """
    return re.findall(r"/api/memos/\d+/images/[^)\s]+", body)


def at(timestamp: str) -> datetime:
    """A timestamp from the API, as a datetime.

    Compared as strings these would not always sort the way the clock ran: a
    whole-second timestamp serialises without a fractional part, so "…:37Z"
    lands after "…:37.1Z".
    """
    return datetime.fromisoformat(timestamp)


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


def test_updating_a_memo_records_when_it_changed(client: TestClient) -> None:
    """The edit must move `updated_at` and leave `created_at` where it was."""
    created = client.post("/api/memos", json={"body": "原始内容"}).json()
    memo_id = created["id"]

    updated = client.patch(
        f"/api/memos/{memo_id}", json={"body": "修改后的内容"}
    ).json()

    assert updated["created_at"] == created["created_at"]
    assert at(updated["updated_at"]) > at(created["updated_at"])


def test_updating_a_nonexistent_memo_returns_404(client: TestClient) -> None:
    response = client.patch("/api/memos/999999", json={"body": "something"})
    assert response.status_code == 404


def test_updating_a_memo_to_empty_body_is_refused(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "不可被改为空"}).json()
    memo_id = created["id"]

    for body in ("", "   ", "\n\t "):
        assert (
            client.patch(f"/api/memos/{memo_id}", json={"body": body}).status_code
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

    old_memo_id = (
        session.scalars(select(Memo).where(Memo.body == "older memo original")).one().id
    )

    client.patch(f"/api/memos/{old_memo_id}", json={"body": "older memo updated"})

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
    updated = client.patch(f"/api/memos/{memo_id}", json={"body": updated_html}).json()
    assert updated["body"] == updated_html
    assert client.get(f"/api/memos/{memo_id}").json()["body"] == updated_html


def test_a_memo_can_be_deleted(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "要被删除的记录"}).json()
    memo_id = created["id"]

    response = client.delete(f"/api/memos/{memo_id}")
    assert response.status_code == 204

    assert client.get(f"/api/memos/{memo_id}").status_code == 404
    assert client.get("/api/memos").json() == []


def test_deleting_a_nonexistent_memo_returns_404(client: TestClient) -> None:
    response = client.delete("/api/memos/999999")
    assert response.status_code == 404


def test_deleting_a_memo_leaves_other_memos_and_their_order_intact(
    client: TestClient,
) -> None:
    for body in ("first", "second", "third"):
        client.post("/api/memos", json={"body": body})

    listed = client.get("/api/memos").json()
    second_id = [m["id"] for m in listed if m["body"] == "second"][0]

    assert client.delete(f"/api/memos/{second_id}").status_code == 204

    remaining = client.get("/api/memos").json()
    assert [m["body"] for m in remaining] == ["third", "first"]


def test_deleted_memo_remains_gone_after_restart(data_dir: Path) -> None:
    with workutil_at(data_dir) as before:
        m1 = before.post("/api/memos", json={"body": "survives"}).json()
        m2 = before.post("/api/memos", json={"body": "to delete"}).json()
        assert before.delete(f"/api/memos/{m2['id']}").status_code == 204

    with workutil_at(data_dir) as after:
        assert [m["body"] for m in after.get("/api/memos").json()] == ["survives"]
        assert after.get(f"/api/memos/{m2['id']}").status_code == 404
        assert after.get(f"/api/memos/{m1['id']}").status_code == 200


def test_a_memo_can_be_created_with_an_image(client: TestClient) -> None:
    b64 = "data:image/png;base64," + base64.b64encode(SAMPLE_PNG).decode()
    created = client.post(
        "/api/memos",
        json={
            "body": "报错堆栈截图:\n\n![screenshot](temp:img_1)\n\n复现命令如上",
            "images": [
                {
                    "id": "temp:img_1",
                    "data": b64,
                    "filename": "error.png",
                }
            ],
        },
    ).json()

    memo_id = created["id"]
    assert created["image_count"] == 1
    (expected_image_url,) = image_urls(created["body"])
    assert expected_image_url.startswith(f"/api/memos/{memo_id}/images/")
    assert "temp:img_1" not in created["body"]

    # List endpoint returns image count, not image content
    listed = client.get("/api/memos").json()
    assert listed[0]["image_count"] == 1
    assert "images" not in listed[0]

    # Image can be read back verbatim
    img_resp = client.get(expected_image_url)
    assert img_resp.status_code == 200
    assert img_resp.content == SAMPLE_PNG
    assert "image/png" in img_resp.headers["content-type"]


def test_a_memo_can_contain_multiple_images(client: TestClient) -> None:
    b64_1 = base64.b64encode(SAMPLE_PNG).decode()
    b64_2 = base64.b64encode(SAMPLE_PNG_2).decode()

    created = client.post(
        "/api/memos",
        json={
            "body": "图一:\n![one](temp:1)\n\n图二:\n![two](temp:2)",
            "images": [
                {"id": "temp:1", "data": b64_1, "filename": "one.png"},
                {"id": "temp:2", "data": b64_2, "filename": "two.png"},
            ],
        },
    ).json()

    assert created["image_count"] == 2
    one, two = image_urls(created["body"])
    assert one != two

    img1 = client.get(one)
    assert img1.status_code == 200
    assert img1.content == SAMPLE_PNG

    img2 = client.get(two)
    assert img2.status_code == 200
    assert img2.content == SAMPLE_PNG_2


def test_an_existing_memo_can_have_new_images_appended(client: TestClient) -> None:
    b64_1 = base64.b64encode(SAMPLE_PNG).decode()
    b64_2 = base64.b64encode(SAMPLE_PNG_2).decode()

    created = client.post(
        "/api/memos",
        json={
            "body": "原始说明:\n![img](temp:old)",
            "images": [{"id": "temp:old", "data": b64_1, "filename": "old.png"}],
        },
    ).json()
    memo_id = created["id"]
    assert created["image_count"] == 1

    # Update by appending a second screenshot
    new_body = created["body"] + "\n\n追加的截图:\n![new](temp:new)"
    updated = client.patch(
        f"/api/memos/{memo_id}",
        json={
            "body": new_body,
            "images": [{"id": "temp:new", "data": b64_2, "filename": "new.png"}],
        },
    ).json()

    assert updated["image_count"] == 2
    old_url, new_url = image_urls(updated["body"])
    assert old_url != new_url

    # Both images are readable
    assert client.get(old_url).content == SAMPLE_PNG
    assert client.get(new_url).content == SAMPLE_PNG_2


def test_images_are_stored_under_memo_id_directory(
    client: TestClient, data_dir: Path
) -> None:
    b64 = base64.b64encode(SAMPLE_PNG).decode()
    created = client.post(
        "/api/memos",
        json={
            "body": "目录测试\n![img](temp:1)",
            "images": [{"id": "temp:1", "data": b64, "filename": "test.png"}],
        },
    ).json()
    memo_id = created["id"]

    (saved_url,) = image_urls(created["body"])
    saved_file = data_dir / "images" / str(memo_id) / saved_url.rsplit("/", 1)[-1]
    assert saved_file.is_file()
    assert saved_file.read_bytes() == SAMPLE_PNG


def test_reading_nonexistent_or_invalid_image_path_is_handled(
    client: TestClient,
) -> None:
    created = client.post("/api/memos", json={"body": "无图记录"}).json()
    memo_id = created["id"]

    # Nonexistent image returns 404
    assert client.get(f"/api/memos/{memo_id}/images/not_found.png").status_code == 404

    # Traversal attempt returns 404
    assert client.get(f"/api/memos/{memo_id}/images/..%2Fhack.png").status_code == 404


def test_images_survive_restart(data_dir: Path) -> None:
    b64 = base64.b64encode(SAMPLE_PNG).decode()

    with workutil_at(data_dir) as before:
        created = before.post(
            "/api/memos",
            json={
                "body": "持久化测试\n![img](temp:1)",
                "images": [{"id": "temp:1", "data": b64, "filename": "shot.png"}],
            },
        ).json()
        (image_url,) = image_urls(created["body"])

    with workutil_at(data_dir) as after:
        res = after.get(image_url)
        assert res.status_code == 200
        assert res.content == SAMPLE_PNG


def test_deleting_a_memo_cleans_up_its_images_directory(
    client: TestClient, data_dir: Path
) -> None:
    b64 = base64.b64encode(SAMPLE_PNG).decode()
    created = client.post(
        "/api/memos",
        json={
            "body": "带图将被删除\n![img](temp:1)",
            "images": [{"id": "temp:1", "data": b64, "filename": "shot.png"}],
        },
    ).json()
    memo_id = created["id"]
    (image_url,) = image_urls(created["body"])
    memo_images_dir = data_dir / "images" / str(memo_id)
    assert memo_images_dir.is_dir()
    assert (memo_images_dir / image_url.rsplit("/", 1)[-1]).is_file()

    # Delete memo
    assert client.delete(f"/api/memos/{memo_id}").status_code == 204

    # Images directory is gone from disk
    assert not memo_images_dir.exists()

    # Requesting the image now returns 404
    assert client.get(image_url).status_code == 404


def test_removing_image_reference_from_body_keeps_image_file_on_disk(
    client: TestClient, data_dir: Path
) -> None:
    """Deliberate decision: cutting text does not delete files (no reference counting).

    Deleting text in editor is reversible, but losing files is not.
    """
    b64 = base64.b64encode(SAMPLE_PNG).decode()
    created = client.post(
        "/api/memos",
        json={
            "body": "保留文件测试\n![img](temp:1)",
            "images": [{"id": "temp:1", "data": b64, "filename": "shot.png"}],
        },
    ).json()
    memo_id = created["id"]
    (image_url,) = image_urls(created["body"])
    saved_file = data_dir / "images" / str(memo_id) / image_url.rsplit("/", 1)[-1]
    assert saved_file.is_file()

    # Remove the image reference from the body
    client.patch(f"/api/memos/{memo_id}", json={"body": "只保留文字，删除了图片引用"})

    # The image file is still preserved on disk
    assert saved_file.is_file()

    # The image endpoint still serves it
    img_resp = client.get(image_url)
    assert img_resp.status_code == 200
    assert img_resp.content == SAMPLE_PNG


def test_deleting_a_memo_without_images_succeeds(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "无图记录"}).json()
    assert client.delete(f"/api/memos/{created['id']}").status_code == 204


def test_search_cjk_keywords_guardrail_adr_0002(client: TestClient) -> None:
    """ADR-0002 guardrail tests for CJK substring search.

    These must pass with LIKE '%q%' and would fail on SQLite FTS5 unicode61/trigram.
    """
    client.post("/api/memos", json={"body": "今日任务\n完成バグ修正工作"})
    client.post("/api/memos", json={"body": "技术预研\n中文分词测试"})
    client.post("/api/memos", json={"body": "客户支持\n障害対応中，排查完毕"})
    client.post("/api/memos", json={"body": "无关记录\n普通日常记事"})

    # 1. 搜索 バグ 能命中含「バグ修正」的 Memo
    res1 = client.get("/api/memos", params={"q": "バグ"}).json()
    assert len(res1) == 1
    assert "バグ修正" in res1[0]["body"]
    assert any("バグ" in s for s in res1[0]["snippets"])

    # 2. 搜索 中文 能命中含「中文分词」的 Memo
    res2 = client.get("/api/memos", params={"q": "中文"}).json()
    assert len(res2) == 1
    assert "中文分词" in res2[0]["body"]
    assert any("中文分词" in s for s in res2[0]["snippets"])

    # 3. 搜索 対応 能命中含该词的 Memo
    res3 = client.get("/api/memos", params={"q": "対応"}).json()
    assert len(res3) == 1
    assert "対応中" in res3[0]["body"]
    assert any("対応" in s for s in res3[0]["snippets"])


def test_search_matches_arbitrary_position_and_returns_snippets(
    client: TestClient,
) -> None:
    """The match can happen anywhere (e.g. line 5), and results carry snippets."""
    body = (
        "今天调登录系统\n"
        + "第二行没有关键词\n"
        + "第三行依然没有\n"
        + "第四行还是没有\n"
        + "第五行终于出现了 authentication token 的生成逻辑"
    )
    client.post("/api/memos", json={"body": body})

    # Search for token
    res = client.get("/api/memos", params={"q": "token"}).json()
    assert len(res) == 1
    item = res[0]
    # First line is what list shows as title, body is the full content
    assert item["body"].startswith("今天调登录系统")
    # Snippet reveals why this memo was matched
    assert len(item["snippets"]) >= 1
    assert "token" in item["snippets"][0]

    # English case-insensitivity: TOKEN matches token
    res_upper = client.get("/api/memos", params={"q": "TOKEN"}).json()
    assert len(res_upper) == 1
    assert res_upper[0]["id"] == item["id"]


def test_search_multiple_hits_in_one_memo(client: TestClient) -> None:
    body = (
        "Line 1: error occurred during startup.\n"
        + "Unrelated paragraph ...\n" * 4
        + "Line 10: another critical error detected."
    )
    client.post("/api/memos", json={"body": body})
    res = client.get("/api/memos", params={"q": "error"}).json()
    assert len(res) == 1
    # Distant matches should give multiple snippets
    assert len(res[0]["snippets"]) == 2


def test_clearing_search_restores_complete_reverse_chronological_list(
    client: TestClient,
) -> None:
    client.post("/api/memos", json={"body": "第一条记录 alpha"})
    client.post("/api/memos", json={"body": "第二条记录 beta"})
    client.post("/api/memos", json={"body": "第三条记录 gamma"})

    # Search converges
    filtered = client.get("/api/memos", params={"q": "beta"}).json()
    assert len(filtered) == 1
    assert "beta" in filtered[0]["body"]

    # Empty string or omitted q returns all items
    all_empty_q = client.get("/api/memos", params={"q": ""}).json()
    all_no_q = client.get("/api/memos").json()
    assert len(all_empty_q) == 3
    assert len(all_no_q) == 3
    assert all_empty_q[0]["id"] == all_no_q[0]["id"]


def test_search_no_results_returns_empty_list(client: TestClient) -> None:
    client.post("/api/memos", json={"body": "一些内容"})
    res = client.get("/api/memos", params={"q": "nonexistent_term_404"}).json()
    assert res == []


def test_a_pasted_svg_is_never_served_as_a_document(client: TestClient) -> None:
    """An SVG is a scriptable document, and it would come from our own origin.

    Rendering raw HTML is blocked in the markdown renderer, but a memo can link
    to its own image, and following that link would open a page able to call
    this backend — the chain design.md §6 F1 exists to cut. Screenshots are
    never SVG, so nothing is lost by refusing the name.
    """
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    created = client.post(
        "/api/memos",
        json={
            "body": "看图 ![x](temp:svg)",
            "images": [
                {
                    "id": "temp:svg",
                    "data": base64.b64encode(svg).decode(),
                    "filename": "evil.svg",
                }
            ],
        },
    ).json()

    assert ".svg" not in created["body"]

    (url,) = image_urls(created["body"])
    assert url.endswith(".png")
    response = client.get(url)
    assert "svg" not in response.headers["content-type"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_an_oversized_image_is_refused(client: TestClient) -> None:
    from app.core.images import MAX_IMAGE_BYTES

    huge = base64.b64encode(b"\x00" * (MAX_IMAGE_BYTES + 1)).decode()
    response = client.post(
        "/api/memos",
        json={
            "body": "巨图 ![x](temp:big)",
            "images": [{"id": "temp:big", "data": huge, "filename": "big.png"}],
        },
    )
    assert response.status_code == 422
    assert client.get("/api/memos").json() == []


def test_a_refused_save_leaves_no_images_behind(
    client: TestClient, data_dir: Path
) -> None:
    """One bad image fails the whole save, and takes its siblings with it.

    Half a memo's screenshots on disk with no memo naming them is the state the
    single-request design exists to make impossible (spec 图片).
    """
    good = base64.b64encode(SAMPLE_PNG).decode()
    response = client.post(
        "/api/memos",
        json={
            "body": "两张图 ![a](temp:a) ![b](temp:b)",
            "images": [
                {"id": "temp:a", "data": good, "filename": "a.png"},
                {"id": "temp:b", "data": "!!! not base64 !!!", "filename": "b.png"},
            ],
        },
    )

    assert response.status_code == 422
    assert client.get("/api/memos").json() == []
    images_dir = data_dir / "images"
    assert [path.name for path in images_dir.iterdir()] == []


def test_a_new_memo_never_inherits_images_left_by_an_earlier_one(
    client: TestClient, data_dir: Path
) -> None:
    """SQLite hands out the id of a memo that is gone, directory and all.

    If a screenshot could not be deleted — a viewer has it open, which is
    ordinary on Windows — the next memo to take that id must not adopt it and
    announce 「含 1 张图」 over someone else's picture.
    """
    stale = data_dir / "images" / "1"
    stale.mkdir(parents=True)
    (stale / "img_1.png").write_bytes(SAMPLE_PNG)

    created = client.post("/api/memos", json={"body": "全新的一条,从没放过图"}).json()
    assert created["id"] == 1
    assert created["image_count"] == 0
    assert client.get("/api/memos").json()[0]["image_count"] == 0


def test_deleting_a_memo_succeeds_even_if_its_images_will_not_go(
    client: TestClient, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The memo is gone the moment the row is; the files are housekeeping.

    Reporting a failure would say the memo is still there, and it is not.
    """
    b64 = base64.b64encode(SAMPLE_PNG).decode()
    created = client.post(
        "/api/memos",
        json={
            "body": "有图 ![x](temp:x)",
            "images": [{"id": "temp:x", "data": b64, "filename": "x.png"}],
        },
    ).json()

    def locked(path: Path, ignore_errors: bool = False, **kwargs: object) -> None:
        """`shutil.rmtree` meeting a file it cannot unlink.

        Left as it is when asked to ignore errors, raising otherwise — so this
        test fails if the deletion stops asking.
        """
        if not ignore_errors:
            raise PermissionError("[WinError 32] the file is open in another program")

    monkeypatch.setattr(shutil, "rmtree", locked)

    assert client.delete(f"/api/memos/{created['id']}").status_code == 204
    assert client.get("/api/memos").json() == []
    assert client.get(f"/api/memos/{created['id']}").status_code == 404
    assert (data_dir / "images" / str(created["id"])).is_dir()


def test_search_answers_from_the_same_window_the_list_shows(
    client: TestClient, session: Session
) -> None:
    """A query cannot return more rows than browsing does."""
    session.add_all(
        Memo(
            body=f"批量记录 {n} 都含有 keyword",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            updated_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        for n in range(RECENT_MEMO_LIMIT + 20)
    )
    session.commit()

    assert len(client.get("/api/memos").json()) == RECENT_MEMO_LIMIT
    found = client.get("/api/memos", params={"q": "keyword"}).json()
    assert len(found) == RECENT_MEMO_LIMIT


def test_a_memo_matching_many_times_says_how_many(client: TestClient) -> None:
    """Seeing five hits and assuming that is all of them is a wrong answer."""
    filler = "\n" + "这一行没有关键词,只是把两处命中隔得足够远\n" * 10
    client.post(
        "/api/memos",
        json={"body": filler.join(f"第 {n} 处 timeout" for n in range(9))},
    )

    found = client.get("/api/memos", params={"q": "timeout"}).json()[0]
    assert len(found["snippets"]) == 5
    assert found["snippet_total"] == 9


def test_pin_and_unpin_are_idempotent(client: TestClient) -> None:
    created = client.post("/api/memos", json={"body": "幂等性测试"}).json()
    memo_id = created["id"]
    assert created["pinned_at"] is None

    # First pin
    pinned1 = client.post(f"/api/memos/{memo_id}/pin")
    assert pinned1.status_code == 200
    pinned_at1 = pinned1.json()["pinned_at"]
    assert pinned_at1 is not None

    # Second pin (idempotent, timestamp unchanged)
    pinned2 = client.post(f"/api/memos/{memo_id}/pin")
    assert pinned2.status_code == 200
    assert pinned2.json()["pinned_at"] == pinned_at1

    # First unpin
    unpinned1 = client.delete(f"/api/memos/{memo_id}/pin")
    assert unpinned1.status_code == 200
    assert unpinned1.json()["pinned_at"] is None

    # Second unpin (idempotent, stays None)
    unpinned2 = client.delete(f"/api/memos/{memo_id}/pin")
    assert unpinned2.status_code == 200
    assert unpinned2.json()["pinned_at"] is None


def test_pinning_does_not_modify_updated_at_and_editing_preserves_pinned_at(
    client: TestClient,
) -> None:
    created = client.post("/api/memos", json={"body": "时间戳保全测试"}).json()
    memo_id = created["id"]
    original_updated_at = created["updated_at"]

    # Pinning does not touch updated_at
    pinned = client.post(f"/api/memos/{memo_id}/pin").json()
    assert pinned["updated_at"] == original_updated_at
    assert pinned["pinned_at"] is not None
    pinned_at = pinned["pinned_at"]

    # Editing body updates updated_at, but preserves pinned_at
    edited = client.patch(f"/api/memos/{memo_id}", json={"body": "修改后的正文"}).json()
    assert edited["body"] == "修改后的正文"
    assert edited["pinned_at"] == pinned_at
    assert at(edited["updated_at"]) >= at(original_updated_at)


def test_pin_and_unpin_nonexistent_memo_returns_404(client: TestClient) -> None:
    assert client.post("/api/memos/99999/pin").status_code == 404
    assert client.delete("/api/memos/99999/pin").status_code == 404


def test_pinned_old_memo_appears_at_top_even_beyond_recent_limit(
    client: TestClient, session: Session
) -> None:
    """An old memo beyond the 200 recent limit must appear at the top when pinned."""
    oldest = Memo(
        body="最老但被置顶的 memo",
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
        updated_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    session.add(oldest)
    session.flush()
    oldest_id = oldest.id

    session.add_all(
        Memo(
            body=f"中间填充 memo {n}",
            created_at=datetime(2021, 1, 1, tzinfo=UTC),
            updated_at=datetime(2021, 1, 1, tzinfo=UTC),
        )
        for n in range(RECENT_MEMO_LIMIT + 5)
    )
    session.commit()

    # Before pinning, oldest is beyond the recent limit
    list_before = client.get("/api/memos").json()
    assert len(list_before) == RECENT_MEMO_LIMIT
    assert not any(m["id"] == oldest_id for m in list_before)

    # Pin the oldest memo
    client.post(f"/api/memos/{oldest_id}/pin")

    # After pinning, oldest appears at the very top of the list,
    # unbounded by the recent memo limit
    list_after = client.get("/api/memos").json()
    assert len(list_after) == RECENT_MEMO_LIMIT + 1
    assert list_after[0]["id"] == oldest_id
    assert list_after[0]["pinned_at"] is not None


def test_newly_created_pinned_memo_appears_only_once_in_list(
    client: TestClient,
) -> None:
    memo1 = client.post("/api/memos", json={"body": "memo 1"}).json()
    memo2 = client.post("/api/memos", json={"body": "memo 2"}).json()
    memo3 = client.post("/api/memos", json={"body": "memo 3"}).json()

    # Pin memo 1 first, then pin memo 3
    client.post(f"/api/memos/{memo1['id']}/pin")
    client.post(f"/api/memos/{memo3['id']}/pin")

    listed = client.get("/api/memos").json()
    # Recently pinned memo3 is top, then memo1, then unpinned memo2
    assert [m["id"] for m in listed] == [memo3["id"], memo1["id"], memo2["id"]]
    # No duplicate ids
    ids = [m["id"] for m in listed]
    assert len(ids) == len(set(ids))


def test_search_order_is_independent_of_pinning(client: TestClient) -> None:
    memo_a = client.post("/api/memos", json={"body": "alpha first"}).json()
    memo_b = client.post("/api/memos", json={"body": "alpha second"}).json()

    # Pin memo_a (the older one)
    client.post(f"/api/memos/{memo_a['id']}/pin")

    # In default list, pinned memo_a is at the top
    default_list = client.get("/api/memos").json()
    assert default_list[0]["id"] == memo_a["id"]

    # In search, order is strictly created_at DESC (memo_b then memo_a)
    search_list = client.get("/api/memos", params={"q": "alpha"}).json()
    assert [m["id"] for m in search_list] == [memo_b["id"], memo_a["id"]]
