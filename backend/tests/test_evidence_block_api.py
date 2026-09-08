"""What a Block promises: a piece of a case, in a place, with a small heading.

The HTTP boundary is the agreed test seam (design.md §6 F5 测试接缝). This is the
bottom layer of the model — Evidence → Case → Block — with the simplest of the
three kinds. What is pinned down here is what every kind shares: ordering,
labelling, deletion, and which case a block belongs to. The half that touches
the disk is in `test_evidence_image_block_api.py`; the table kind arrives in
ticket 06 and slots into the same ordering and labelling.

There are no step numbers: the pieces of a case stand side by side rather than
1→2→3 (ADR-0003), which is why `label` is optional and nothing here counts.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.evidence.models import EvidenceBlock

from .conftest import workutil_at
from .test_evidence_api import add_case, new_evidence


def blocks_of(client: TestClient, evidence_id: int, case_id: int) -> list[Any]:
    opened = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}")
    assert opened.status_code == 200, opened.text
    listed: list[Any] = opened.json()["blocks"]
    return listed


def texts_of(client: TestClient, evidence_id: int, case_id: int) -> list[str]:
    return [block["text"] for block in blocks_of(client, evidence_id, case_id)]


def add_text(
    client: TestClient,
    evidence_id: int,
    case_id: int,
    text: str,
    label: str | None = None,
) -> int:
    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": text, "label": label},
    )
    assert created.status_code == 201, created.text
    block_id: int = created.json()["id"]
    return block_id


@pytest.fixture
def case(client: TestClient) -> tuple[int, int]:
    """One evidence with one case in it — where a block goes."""
    evidence_id = new_evidence(client)
    return evidence_id, add_case(client, evidence_id, "1")


# --- Adding -----------------------------------------------------------------


def test_a_text_block_can_be_added_and_read_back(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": "画面を開いて検索ボタンを押した"},
    )

    assert created.status_code == 201, created.text
    assert created.json()["kind"] == "text"
    assert created.json()["text"] == "画面を開いて検索ボタンを押した"
    assert texts_of(client, evidence_id, case_id) == ["画面を開いて検索ボタンを押した"]


def test_a_new_case_has_no_blocks(client: TestClient, case: tuple[int, int]) -> None:
    """A case with nothing in it is a real state — it exports as an empty
    sheet rather than being refused (design.md §6 F5 Excel 导出)."""
    evidence_id, case_id = case

    opened = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}")

    assert opened.status_code == 200
    assert opened.json()["name"] == "1"
    assert opened.json()["blocks"] == []


def test_new_blocks_land_at_the_end(client: TestClient, case: tuple[int, int]) -> None:
    """Blocks are appended as the verification happens, in the order it did."""
    evidence_id, case_id = case

    for text in ("事前準備", "実行ログ", "更新後の結果"):
        add_text(client, evidence_id, case_id, text)

    assert texts_of(client, evidence_id, case_id) == [
        "事前準備",
        "実行ログ",
        "更新後の結果",
    ]


def test_a_block_can_be_given_a_label_as_it_is_added(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    add_text(client, evidence_id, case_id, "id=1 の行", "事前準備の DB データ")

    assert blocks_of(client, evidence_id, case_id)[0]["label"] == "事前準備の DB データ"


def test_a_block_without_a_label_has_none(
    client: TestClient, case: tuple[int, int]
) -> None:
    """The label is a heading, not a step number: most blocks do without one."""
    evidence_id, case_id = case

    add_text(client, evidence_id, case_id, "ログ")

    assert blocks_of(client, evidence_id, case_id)[0]["label"] is None


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_a_text_block_with_nothing_in_it_is_refused(
    client: TestClient, case: tuple[int, int], text: str
) -> None:
    """Deleting is how a block goes, so an empty one is a mistake rather than
    an instruction."""
    evidence_id, case_id = case

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": text},
    )

    assert refused.status_code == 422
    assert blocks_of(client, evidence_id, case_id) == []


def test_a_pasted_log_keeps_its_shape(
    client: TestClient, case: tuple[int, int]
) -> None:
    """A log is a text block — there is no separate kind for it (design.md §6
    F5) — so what makes it readable has to survive the trip.

    Blank edges from a paste go; the indent of the first line stays. Trimming
    that indent alone would leave every line under it hanging.
    """
    evidence_id, case_id = case
    pasted = "   \n    2024-01-01 10:00:00 INFO  start\n        detail line\n  \n"

    add_text(client, evidence_id, case_id, pasted)

    assert texts_of(client, evidence_id, case_id) == [
        "    2024-01-01 10:00:00 INFO  start\n        detail line"
    ]


def test_a_kind_with_no_payload_behind_it_is_refused(
    client: TestClient, case: tuple[int, int]
) -> None:
    """`kind` is `text` / `image` / `table`, and each carries its own payload.

    `table` is not implemented yet (ticket 06) and `video` is not a kind at
    all; `image` is real but needs an image, which a body of text is not. All
    three are refused rather than stored as an empty something.
    """
    evidence_id, case_id = case

    for kind in ("image", "table", "video"):
        refused = client.post(
            f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
            json={"kind": kind, "text": "x"},
        )
        assert refused.status_code == 422, kind

    assert blocks_of(client, evidence_id, case_id) == []


def test_adding_a_block_to_a_nonexistent_case_returns_404(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, _ = case

    added = client.post(
        f"/api/evidence/{evidence_id}/cases/999999/blocks",
        json={"kind": "text", "text": "どこにも属さない"},
    )

    assert added.status_code == 404


def test_a_missing_case_is_a_404_even_when_the_text_is_no_good(
    client: TestClient, case: tuple[int, int]
) -> None:
    """What the payload says is beside the point when there is nowhere to put
    it: the answer is "no such case", not "your text is empty"."""
    evidence_id, case_id = case

    added = client.post(
        f"/api/evidence/{evidence_id}/cases/999999/blocks",
        json={"kind": "text", "text": "   "},
    )
    edited = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/999999",
        json={"text": "   "},
    )

    assert (added.status_code, edited.status_code) == (404, 404)


def test_a_block_belongs_to_exactly_one_case(client: TestClient) -> None:
    """A block id from another case is a 404 here, not someone else's block."""
    evidence_id = new_evidence(client)
    mine = add_case(client, evidence_id, "1")
    theirs = add_case(client, evidence_id, "2")
    block_id = add_text(client, evidence_id, theirs, "あっちの内容")

    at = f"/api/evidence/{evidence_id}/cases/{mine}/blocks/{block_id}"
    assert client.patch(at, json={"text": "書き換え"}).status_code == 404
    assert client.put(f"{at}/label", json={"label": "横取り"}).status_code == 404
    assert client.post(f"{at}/move", json={"to": "top"}).status_code == 404
    assert client.delete(at).status_code == 404
    assert texts_of(client, evidence_id, theirs) == ["あっちの内容"]


def test_a_case_id_from_another_evidence_is_not_reachable(
    client: TestClient,
) -> None:
    mine = new_evidence(client, "こっち")
    theirs = new_evidence(client, "あっち")
    case_id = add_case(client, theirs, "1")

    assert client.get(f"/api/evidence/{mine}/cases/{case_id}").status_code == 404
    assert (
        client.post(
            f"/api/evidence/{mine}/cases/{case_id}/blocks",
            json={"kind": "text", "text": "横取り"},
        ).status_code
        == 404
    )


# --- Editing ----------------------------------------------------------------


def test_the_text_of_a_block_can_be_changed(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "打ち間違い")

    edited = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}",
        json={"text": "検索結果は 3 件"},
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["text"] == "検索結果は 3 件"
    assert texts_of(client, evidence_id, case_id) == ["検索結果は 3 件"]


def test_emptying_a_block_is_refused(client: TestClient, case: tuple[int, int]) -> None:
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "消したくない内容")

    refused = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}",
        json={"text": "   "},
    )

    assert refused.status_code == 422
    assert texts_of(client, evidence_id, case_id) == ["消したくない内容"]


def test_editing_a_nonexistent_block_returns_404(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/999999"
    assert client.patch(at, json={"text": "x"}).status_code == 404
    assert client.put(f"{at}/label", json={"label": "x"}).status_code == 404
    assert client.delete(at).status_code == 404


# --- Labels -----------------------------------------------------------------


def test_a_label_can_be_added_to_a_block_that_had_none(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "select * from orders")

    labelled = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/label",
        json={"label": "事前準備の DB データ"},
    )

    assert labelled.status_code == 200, labelled.text
    assert labelled.json()["label"] == "事前準備の DB データ"


def test_a_label_can_be_changed(client: TestClient, case: tuple[int, int]) -> None:
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "ログ", "実行前")

    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/label"
    assert client.put(at, json={"label": "実行後"}).status_code == 200

    assert blocks_of(client, evidence_id, case_id)[0]["label"] == "実行後"


@pytest.mark.parametrize("cleared", [None, "", "   "])
def test_a_label_can_be_cleared(
    client: TestClient, case: tuple[int, int], cleared: str | None
) -> None:
    """A heading you no longer want is removed, not left as a blank line above
    the block in the exported sheet."""
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "ログ", "実行前")

    emptied = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/label",
        json={"label": cleared},
    )

    assert emptied.status_code == 200, emptied.text
    assert emptied.json()["label"] is None
    assert blocks_of(client, evidence_id, case_id)[0]["label"] is None


def test_a_label_is_stored_without_its_surrounding_space(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "ログ")

    client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/label",
        json={"label": "  実行ログ  "},
    )

    assert blocks_of(client, evidence_id, case_id)[0]["label"] == "実行ログ"


def test_the_text_and_the_label_are_edited_independently(
    client: TestClient, case: tuple[int, int]
) -> None:
    """The label belongs to every kind of block; the text to one of them. They
    are separate endpoints so neither drags the other along."""
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "ログ", "実行ログ")

    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}"
    client.patch(at, json={"text": "書き直したログ"})

    block = blocks_of(client, evidence_id, case_id)[0]
    assert (block["text"], block["label"]) == ("書き直したログ", "実行ログ")


# --- Deleting ---------------------------------------------------------------


def test_a_block_can_be_deleted(client: TestClient, case: tuple[int, int]) -> None:
    """A screenshot you retook, a paragraph you rewrote — it must not go out
    with the delivery (spec User Stories 14)."""
    evidence_id, case_id = case
    add_text(client, evidence_id, case_id, "一つ目")
    block_id = add_text(client, evidence_id, case_id, "二つ目")
    add_text(client, evidence_id, case_id, "三つ目")

    deleted = client.delete(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}"
    )

    assert deleted.status_code == 204
    assert texts_of(client, evidence_id, case_id) == ["一つ目", "三つ目"]


def test_deleting_a_case_takes_its_blocks_with_it(
    client: TestClient, session: Session
) -> None:
    """Read straight from the database, unlike almost everything here: once the
    case is gone its blocks have no URL, so rows left behind are invisible to
    the API — and rows left behind are the whole thing being ruled out. Same
    shape as `test_deleting_an_evidence_takes_its_cases_with_it` one level up.
    """
    evidence_id = new_evidence(client)
    doomed = add_case(client, evidence_id, "1")
    kept = add_case(client, evidence_id, "2")
    add_text(client, evidence_id, doomed, "消える")
    add_text(client, evidence_id, doomed, "これも消える")
    add_text(client, evidence_id, kept, "残る")

    assert (
        client.delete(f"/api/evidence/{evidence_id}/cases/{doomed}").status_code == 204
    )

    remaining = session.scalars(select(EvidenceBlock)).all()
    assert [block.text for block in remaining] == ["残る"]


def test_deleting_an_evidence_takes_every_block_with_it(
    client: TestClient, session: Session
) -> None:
    evidence_id = new_evidence(client)
    case_id = add_case(client, evidence_id, "1")
    add_text(client, evidence_id, case_id, "消える")
    kept_evidence = new_evidence(client, "残るほう")
    kept_case = add_case(client, kept_evidence, "1")
    add_text(client, kept_evidence, kept_case, "残る")

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204

    remaining = session.scalars(select(EvidenceBlock)).all()
    assert [block.text for block in remaining] == ["残る"]


# --- Reordering -------------------------------------------------------------


def move(
    client: TestClient, evidence_id: int, case_id: int, block_id: int, to: str
) -> list[str]:
    moved = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/move",
        json={"to": to},
    )
    assert moved.status_code == 200, moved.text
    return [block["text"] for block in moved.json()]


@pytest.fixture
def four_blocks(
    client: TestClient, case: tuple[int, int]
) -> tuple[int, int, dict[str, int]]:
    evidence_id, case_id = case
    ids = {
        text: add_text(client, evidence_id, case_id, text)
        for text in ("1", "2", "3", "4")
    }
    return evidence_id, case_id, ids


def test_a_block_can_move_up_one_place(
    client: TestClient, four_blocks: tuple[int, int, dict[str, int]]
) -> None:
    evidence_id, case_id, ids = four_blocks

    assert move(client, evidence_id, case_id, ids["3"], "up") == ["1", "3", "2", "4"]
    assert texts_of(client, evidence_id, case_id) == ["1", "3", "2", "4"]


def test_a_block_can_move_down_one_place(
    client: TestClient, four_blocks: tuple[int, int, dict[str, int]]
) -> None:
    evidence_id, case_id, ids = four_blocks

    assert move(client, evidence_id, case_id, ids["2"], "down") == ["1", "3", "2", "4"]


def test_a_block_can_move_to_the_top(
    client: TestClient, four_blocks: tuple[int, int, dict[str, int]]
) -> None:
    """The one move that would otherwise be eight clicks: a screenshot pasted
    at the bottom that belongs at the front (design.md §6 F5)."""
    evidence_id, case_id, ids = four_blocks

    assert move(client, evidence_id, case_id, ids["4"], "top") == ["4", "1", "2", "3"]


def test_a_block_can_move_to_the_bottom(
    client: TestClient, four_blocks: tuple[int, int, dict[str, int]]
) -> None:
    evidence_id, case_id, ids = four_blocks

    assert move(client, evidence_id, case_id, ids["1"], "bottom") == [
        "2",
        "3",
        "4",
        "1",
    ]


def test_moving_past_either_end_leaves_the_order_alone(
    client: TestClient, four_blocks: tuple[int, int, dict[str, int]]
) -> None:
    """The first block moving up and the last moving down: the buttons stay
    clickable at the ends, and the answer is just "still here"."""
    evidence_id, case_id, ids = four_blocks

    assert move(client, evidence_id, case_id, ids["1"], "up") == ["1", "2", "3", "4"]
    assert move(client, evidence_id, case_id, ids["4"], "down") == ["1", "2", "3", "4"]
    assert move(client, evidence_id, case_id, ids["1"], "top") == ["1", "2", "3", "4"]
    assert move(client, evidence_id, case_id, ids["4"], "bottom") == [
        "1",
        "2",
        "3",
        "4",
    ]


def test_the_only_block_in_a_case_can_be_moved_anywhere(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block_id = add_text(client, evidence_id, case_id, "ひとつだけ")

    for to in ("up", "down", "top", "bottom"):
        assert move(client, evidence_id, case_id, block_id, to) == ["ひとつだけ"]


def test_an_unknown_move_is_refused(
    client: TestClient, four_blocks: tuple[int, int, dict[str, int]]
) -> None:
    evidence_id, case_id, ids = four_blocks

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{ids['1']}/move",
        json={"to": "sideways"},
    )

    assert refused.status_code == 422
    assert texts_of(client, evidence_id, case_id) == ["1", "2", "3", "4"]


def test_deleting_a_block_leaves_the_rest_in_order(
    client: TestClient, four_blocks: tuple[int, int, dict[str, int]]
) -> None:
    """Whatever the gaps in `order` look like afterwards, the list must not
    start wobbling between calls."""
    evidence_id, case_id, ids = four_blocks

    client.delete(f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{ids['2']}")
    add_text(client, evidence_id, case_id, "5")

    assert texts_of(client, evidence_id, case_id) == ["1", "3", "4", "5"]
    assert move(client, evidence_id, case_id, ids["4"], "up") == ["1", "4", "3", "5"]


def test_blocks_of_one_case_do_not_reorder_another(client: TestClient) -> None:
    """`order` counts from 0 within a case, so two cases both have a first
    block and moving one must not touch the other."""
    evidence_id = new_evidence(client)
    first = add_case(client, evidence_id, "1")
    second = add_case(client, evidence_id, "2")
    ids = {name: add_text(client, evidence_id, first, name) for name in ("a", "b")}
    for name in ("c", "d"):
        add_text(client, evidence_id, second, name)

    assert move(client, evidence_id, first, ids["b"], "top") == ["b", "a"]

    assert texts_of(client, evidence_id, second) == ["c", "d"]


def test_blocks_survive_a_restart(data_dir: Path) -> None:
    with workutil_at(data_dir) as before:
        evidence_id = new_evidence(before, "跨重启")
        case_id = add_case(before, evidence_id, "2~5")
        ids = {
            text: add_text(before, evidence_id, case_id, text)
            for text in ("1", "2", "3")
        }
        move(before, evidence_id, case_id, ids["3"], "top")
        before.put(
            f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{ids['1']}/label",
            json={"label": "事前準備の DB データ"},
        )

    with workutil_at(data_dir) as after:
        kept = blocks_of(after, evidence_id, case_id)
        assert [block["text"] for block in kept] == ["3", "1", "2"]
        assert [block["label"] for block in kept] == [
            None,
            "事前準備の DB データ",
            None,
        ]
