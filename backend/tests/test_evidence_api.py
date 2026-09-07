"""What the Evidence API promises: a workbook, and the cases inside it.

The HTTP boundary is the agreed test seam (design.md §6 F5 测试接缝). Blocks
arrive in later tickets; what is here is the organising layer — Evidence and
Case — and the sheet-name rule that has to hold before anything is exported.
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.evidence.models import Evidence, EvidenceCase
from app.modules.evidence.service import RECENT_EVIDENCE_LIMIT

from .conftest import workutil_at


def new_evidence(client: TestClient, title: str = "受注一覧の絞り込み修正") -> int:
    created = client.post("/api/evidence", json={"title": title})
    assert created.status_code == 201
    evidence_id: int = created.json()["id"]
    return evidence_id


def add_case(client: TestClient, evidence_id: int, name: str) -> int:
    created = client.post(f"/api/evidence/{evidence_id}/cases", json={"name": name})
    assert created.status_code == 201, created.text
    case_id: int = created.json()["id"]
    return case_id


def case_names(client: TestClient, evidence_id: int) -> list[str]:
    detail = client.get(f"/api/evidence/{evidence_id}")
    assert detail.status_code == 200
    return [case["name"] for case in detail.json()["cases"]]


# --- Evidence ---------------------------------------------------------------


def test_a_new_evidence_can_be_read_back_from_the_list(client: TestClient) -> None:
    client.post("/api/evidence", json={"title": "受注一覧の絞り込み修正"})

    listed = client.get("/api/evidence")

    assert listed.status_code == 200
    assert [one["title"] for one in listed.json()] == ["受注一覧の絞り込み修正"]


def test_the_newest_evidence_comes_first(client: TestClient) -> None:
    for title in ("first", "second", "third"):
        client.post("/api/evidence", json={"title": title})

    listed = client.get("/api/evidence").json()

    assert [one["title"] for one in listed] == ["third", "second", "first"]


def test_the_order_follows_when_an_evidence_was_created(
    client: TestClient, session: Session
) -> None:
    """Renaming an old evidence must not drag it to the top of the list.

    Same rule as memo: the list is ordered by creation, so "the one I started
    last week" stays where it was. Written straight to the database because the
    API cannot say "pretend this is from 2020".
    """
    client.post("/api/evidence", json={"title": "recent"})
    session.add(
        Evidence(
            title="started long ago, renamed just now",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            updated_at=utc_now(),
        )
    )
    session.commit()

    listed = client.get("/api/evidence").json()

    assert [one["title"] for one in listed] == [
        "recent",
        "started long ago, renamed just now",
    ]


def test_evidence_created_in_the_same_instant_still_have_a_stable_order(
    client: TestClient,
) -> None:
    for title in ("first", "second"):
        client.post("/api/evidence", json={"title": title})

    def ids_in_list() -> list[int]:
        return [one["id"] for one in client.get("/api/evidence").json()]

    orders = [ids_in_list() for _ in range(5)]

    assert orders == [orders[0]] * 5


def test_the_list_shows_how_many_cases_each_evidence_has(client: TestClient) -> None:
    evidence_id = new_evidence(client)
    for name in ("1", "2", "2~5"):
        add_case(client, evidence_id, name)

    listed = client.get("/api/evidence").json()

    assert [one["case_count"] for one in listed] == [3]


def test_the_list_stops_at_a_fixed_number(client: TestClient) -> None:
    """No paging: the list is a window on the recent past, like memo's."""
    for index in range(RECENT_EVIDENCE_LIMIT + 3):
        client.post("/api/evidence", json={"title": f"evidence {index}"})

    listed = client.get("/api/evidence").json()

    assert len(listed) == RECENT_EVIDENCE_LIMIT
    assert listed[0]["title"] == f"evidence {RECENT_EVIDENCE_LIMIT + 2}"


def test_an_evidence_can_be_read_by_id(client: TestClient) -> None:
    evidence_id = new_evidence(client, "詳細を開く")

    detail = client.get(f"/api/evidence/{evidence_id}")

    assert detail.status_code == 200
    assert detail.json()["title"] == "詳細を開く"
    assert detail.json()["cases"] == []


def test_reading_a_nonexistent_evidence_returns_404(client: TestClient) -> None:
    assert client.get("/api/evidence/999999").status_code == 404


def test_an_evidence_can_be_renamed(client: TestClient) -> None:
    evidence_id = new_evidence(client, "とりあえず")

    renamed = client.patch(
        f"/api/evidence/{evidence_id}", json={"title": "受注一覧の修正"}
    )

    assert renamed.status_code == 200
    assert renamed.json()["title"] == "受注一覧の修正"
    assert client.get("/api/evidence").json()[0]["title"] == "受注一覧の修正"


def test_renaming_an_evidence_records_when_it_changed(client: TestClient) -> None:
    created = client.post("/api/evidence", json={"title": "とりあえず"}).json()
    assert created["created_at"] == created["updated_at"]

    renamed = client.patch(
        f"/api/evidence/{created['id']}", json={"title": "名前を決めた"}
    ).json()

    assert renamed["created_at"] == created["created_at"]
    assert renamed["updated_at"] > created["updated_at"]


def test_renaming_a_nonexistent_evidence_returns_404(client: TestClient) -> None:
    assert client.patch("/api/evidence/999999", json={"title": "x"}).status_code == 404


def test_an_evidence_needs_a_title(client: TestClient) -> None:
    """The title becomes the delivered file's name, so it cannot be blank."""
    assert client.post("/api/evidence", json={"title": "   "}).status_code == 422

    evidence_id = new_evidence(client)
    assert (
        client.patch(f"/api/evidence/{evidence_id}", json={"title": ""}).status_code
        == 422
    )


def test_an_evidence_title_is_kept_verbatim(client: TestClient) -> None:
    """Characters Excel dislikes in a *sheet* name are fine in a title.

    The title is cleaned when it becomes a filename at export, not on the way
    in — unlike a case name, which is delivered content (spec Excel 导出).
    """
    title = "検索: 一覧/明細 [第2版]"

    created = client.post("/api/evidence", json={"title": title}).json()

    assert created["title"] == title
    assert client.get(f"/api/evidence/{created['id']}").json()["title"] == title


def test_an_evidence_can_be_deleted(client: TestClient) -> None:
    evidence_id = new_evidence(client)

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204
    assert client.get("/api/evidence").json() == []
    assert client.get(f"/api/evidence/{evidence_id}").status_code == 404


def test_deleting_a_nonexistent_evidence_returns_404(client: TestClient) -> None:
    assert client.delete("/api/evidence/999999").status_code == 404


def test_deleting_an_evidence_takes_its_cases_with_it(
    client: TestClient, session: Session
) -> None:
    evidence_id = new_evidence(client)
    add_case(client, evidence_id, "1")
    add_case(client, evidence_id, "2")
    kept = new_evidence(client, "残るほう")
    add_case(client, kept, "1")

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204

    remaining = session.scalars(select(EvidenceCase)).all()
    assert [case.evidence_id for case in remaining] == [kept]


def test_evidence_survives_a_restart(data_dir: Path) -> None:
    with workutil_at(data_dir) as before:
        evidence_id = new_evidence(before, "跨重启")
        add_case(before, evidence_id, "2~5")

    with workutil_at(data_dir) as after:
        assert [one["title"] for one in after.get("/api/evidence").json()] == ["跨重启"]
        assert case_names(after, evidence_id) == ["2~5"]


# --- Case -------------------------------------------------------------------


def test_a_case_can_be_added_and_read_back(client: TestClient) -> None:
    evidence_id = new_evidence(client)

    created = client.post(f"/api/evidence/{evidence_id}/cases", json={"name": "1"})

    assert created.status_code == 201
    assert created.json()["name"] == "1"
    assert case_names(client, evidence_id) == ["1"]


def test_new_cases_land_at_the_end(client: TestClient) -> None:
    evidence_id = new_evidence(client)

    for name in ("1", "2", "3"):
        add_case(client, evidence_id, name)

    assert case_names(client, evidence_id) == ["1", "2", "3"]


def test_a_case_name_need_not_be_a_number(client: TestClient) -> None:
    """`2~5` is what a real case number looks like (spec User Stories 3)."""
    evidence_id = new_evidence(client)

    add_case(client, evidence_id, "2~5")

    assert case_names(client, evidence_id) == ["2~5"]


def test_a_case_can_be_renamed(client: TestClient) -> None:
    evidence_id = new_evidence(client)
    case_id = add_case(client, evidence_id, "1")

    renamed = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}", json={"name": "1~3"}
    )

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "1~3"
    assert case_names(client, evidence_id) == ["1~3"]


def test_renaming_a_case_to_its_own_name_is_allowed(client: TestClient) -> None:
    """The uniqueness check must not see the case as a clash with itself."""
    evidence_id = new_evidence(client)
    case_id = add_case(client, evidence_id, "1")

    renamed = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}", json={"name": "1"}
    )

    assert renamed.status_code == 200


def test_a_case_can_be_deleted(client: TestClient) -> None:
    evidence_id = new_evidence(client)
    add_case(client, evidence_id, "1")
    case_id = add_case(client, evidence_id, "2")
    add_case(client, evidence_id, "3")

    assert (
        client.delete(f"/api/evidence/{evidence_id}/cases/{case_id}").status_code == 204
    )
    assert case_names(client, evidence_id) == ["1", "3"]


def test_a_deleted_case_name_can_be_used_again(client: TestClient) -> None:
    evidence_id = new_evidence(client)
    case_id = add_case(client, evidence_id, "1")

    client.delete(f"/api/evidence/{evidence_id}/cases/{case_id}")

    assert case_names(client, evidence_id) == []
    add_case(client, evidence_id, "1")
    assert case_names(client, evidence_id) == ["1"]


def test_a_case_belongs_to_exactly_one_evidence(client: TestClient) -> None:
    """A case id from another evidence is a 404 here, not someone else's case."""
    mine = new_evidence(client, "こっち")
    theirs = new_evidence(client, "あっち")
    case_id = add_case(client, theirs, "1")

    assert (
        client.patch(
            f"/api/evidence/{mine}/cases/{case_id}", json={"name": "2"}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/evidence/{mine}/cases/{case_id}").status_code == 404
    assert (
        client.post(
            f"/api/evidence/{mine}/cases/{case_id}/move", json={"to": "top"}
        ).status_code
        == 404
    )
    assert case_names(client, theirs) == ["1"]


def test_adding_a_case_to_a_nonexistent_evidence_returns_404(
    client: TestClient,
) -> None:
    assert (
        client.post("/api/evidence/999999/cases", json={"name": "1"}).status_code == 404
    )


# --- Sheet-name validation --------------------------------------------------
#
# Guardrails for spec Excel 导出: a case name *is* a sheet name, and the file is
# delivered to someone else. Cleaning it at export would hand them a workbook
# they never checked, so every one of these has to be refused on the way in.


@pytest.mark.parametrize(
    ("name", "why"),
    [
        ("", "empty"),
        ("   ", "whitespace only"),
        ("a" * 32, "one character over Excel's limit"),
        ("検索: 一覧", "colon"),
        ("入出力\\確認", "backslash"),
        ("入出力/確認", "forward slash"),
        ("これで良い?", "question mark"),
        ("全件*", "asterisk"),
        ("[1]", "square brackets"),
    ],
)
def test_an_illegal_sheet_name_is_refused_when_typed(
    client: TestClient, name: str, why: str
) -> None:
    evidence_id = new_evidence(client)

    created = client.post(f"/api/evidence/{evidence_id}/cases", json={"name": name})

    assert created.status_code == 422, why
    assert case_names(client, evidence_id) == []


def test_a_sheet_name_of_exactly_31_characters_is_allowed(client: TestClient) -> None:
    """Excel's limit is 31, and openpyxl will not tell us when we pass it —
    it warns and writes the long name anyway (3.1.5). One off either side of
    the boundary is the whole point of this pair of tests."""
    evidence_id = new_evidence(client)

    add_case(client, evidence_id, "a" * 31)

    assert case_names(client, evidence_id) == ["a" * 31]


def test_renaming_a_case_is_checked_the_same_way(client: TestClient) -> None:
    evidence_id = new_evidence(client)
    case_id = add_case(client, evidence_id, "1")

    refused = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}", json={"name": "a" * 32}
    )

    assert refused.status_code == 422
    assert case_names(client, evidence_id) == ["1"]


def test_two_cases_in_one_evidence_cannot_share_a_name(client: TestClient) -> None:
    """Excel cannot hold two sheets with the same name at all."""
    evidence_id = new_evidence(client)
    add_case(client, evidence_id, "2~5")

    clash = client.post(f"/api/evidence/{evidence_id}/cases", json={"name": "2~5"})

    assert clash.status_code == 422
    assert case_names(client, evidence_id) == ["2~5"]


def test_two_case_names_cannot_differ_only_in_case(client: TestClient) -> None:
    """Excel's sheet names are unique case-insensitively, and openpyxl does not
    hold that line — measured on 3.1.5 it silently writes `ABC` as `ABC1` next
    to an existing `abc`, without even a warning. A sheet quietly renamed on
    the way out is what validating on the way in is for (spec Excel 导出)."""
    evidence_id = new_evidence(client)
    add_case(client, evidence_id, "abc")

    clash = client.post(f"/api/evidence/{evidence_id}/cases", json={"name": "ABC"})

    assert clash.status_code == 422
    assert case_names(client, evidence_id) == ["abc"]


def test_renaming_onto_a_sibling_name_is_refused(client: TestClient) -> None:
    evidence_id = new_evidence(client)
    add_case(client, evidence_id, "1")
    case_id = add_case(client, evidence_id, "2")

    clash = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}", json={"name": "1"}
    )

    assert clash.status_code == 422
    assert case_names(client, evidence_id) == ["1", "2"]


def test_different_evidence_may_use_the_same_case_names(client: TestClient) -> None:
    """Uniqueness is per workbook — every evidence starts its numbering at 1."""
    first = new_evidence(client, "一つ目")
    second = new_evidence(client, "二つ目")

    add_case(client, first, "1")
    add_case(client, second, "1")

    assert case_names(client, first) == ["1"]
    assert case_names(client, second) == ["1"]


def test_a_case_name_is_stored_with_its_surrounding_space_removed(
    client: TestClient,
) -> None:
    evidence_id = new_evidence(client)

    add_case(client, evidence_id, "  2~5  ")

    assert case_names(client, evidence_id) == ["2~5"]


# --- Reordering cases -------------------------------------------------------


def move(client: TestClient, evidence_id: int, case_id: int, to: str) -> list[str]:
    moved = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/move", json={"to": to}
    )
    assert moved.status_code == 200, moved.text
    return [case["name"] for case in moved.json()]


@pytest.fixture
def four_cases(client: TestClient) -> tuple[int, dict[str, int]]:
    evidence_id = new_evidence(client)
    ids = {name: add_case(client, evidence_id, name) for name in ("1", "2", "3", "4")}
    return evidence_id, ids


def test_a_case_can_move_up_one_place(
    client: TestClient, four_cases: tuple[int, dict[str, int]]
) -> None:
    evidence_id, ids = four_cases

    assert move(client, evidence_id, ids["3"], "up") == ["1", "3", "2", "4"]
    assert case_names(client, evidence_id) == ["1", "3", "2", "4"]


def test_a_case_can_move_down_one_place(
    client: TestClient, four_cases: tuple[int, dict[str, int]]
) -> None:
    evidence_id, ids = four_cases

    assert move(client, evidence_id, ids["2"], "down") == ["1", "3", "2", "4"]


def test_a_case_can_move_to_the_top(
    client: TestClient, four_cases: tuple[int, dict[str, int]]
) -> None:
    evidence_id, ids = four_cases

    assert move(client, evidence_id, ids["4"], "top") == ["4", "1", "2", "3"]


def test_a_case_can_move_to_the_bottom(
    client: TestClient, four_cases: tuple[int, dict[str, int]]
) -> None:
    evidence_id, ids = four_cases

    assert move(client, evidence_id, ids["1"], "bottom") == ["2", "3", "4", "1"]


def test_moving_past_either_end_leaves_the_order_alone(
    client: TestClient, four_cases: tuple[int, dict[str, int]]
) -> None:
    """The buttons stay clickable at the ends; the answer is just "still here"."""
    evidence_id, ids = four_cases

    assert move(client, evidence_id, ids["1"], "up") == ["1", "2", "3", "4"]
    assert move(client, evidence_id, ids["4"], "down") == ["1", "2", "3", "4"]
    assert move(client, evidence_id, ids["1"], "top") == ["1", "2", "3", "4"]
    assert move(client, evidence_id, ids["4"], "bottom") == ["1", "2", "3", "4"]


def test_an_unknown_move_is_refused(
    client: TestClient, four_cases: tuple[int, dict[str, int]]
) -> None:
    evidence_id, ids = four_cases

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{ids['1']}/move", json={"to": "sideways"}
    )

    assert refused.status_code == 422
    assert case_names(client, evidence_id) == ["1", "2", "3", "4"]


def test_the_order_survives_a_restart(data_dir: Path) -> None:
    with workutil_at(data_dir) as before:
        evidence_id = new_evidence(before, "順番を覚えている")
        ids = {name: add_case(before, evidence_id, name) for name in ("1", "2", "3")}
        move(before, evidence_id, ids["3"], "top")

    with workutil_at(data_dir) as after:
        assert case_names(after, evidence_id) == ["3", "1", "2"]


def test_deleting_a_case_leaves_the_rest_in_order(client: TestClient) -> None:
    """Whatever the gaps in `order` look like afterwards, the list must not
    start wobbling between calls."""
    evidence_id = new_evidence(client)
    ids = {name: add_case(client, evidence_id, name) for name in ("1", "2", "3", "4")}

    client.delete(f"/api/evidence/{evidence_id}/cases/{ids['2']}")
    add_case(client, evidence_id, "5")

    assert case_names(client, evidence_id) == ["1", "3", "4", "5"]
    assert move(client, evidence_id, ids["4"], "up") == ["1", "4", "3", "5"]


# --- Images -----------------------------------------------------------------


def test_deleting_an_evidence_clears_its_images_directory(
    client: TestClient, data_dir: Path
) -> None:
    """Evidence keeps its screenshots under `images/evidence/<id>/`, and they
    are useless once the workbook is gone (spec User Stories 26)."""
    evidence_id = new_evidence(client)
    evidence_images = data_dir / "images" / "evidence" / str(evidence_id)
    evidence_images.mkdir(parents=True)
    (evidence_images / "img_1.png").write_bytes(b"not really a png")

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204

    assert not evidence_images.exists()


def test_evidence_images_sit_beside_the_memo_directories(
    client: TestClient, data_dir: Path
) -> None:
    """Memo directories are named by a decimal id, so the literal `evidence`
    cannot collide with one and no existing data has to move (design.md §5)."""
    memo_id = client.post("/api/memos", json={"body": "隣にいる"}).json()["id"]
    evidence_id = new_evidence(client)

    memo_images = data_dir / "images" / str(memo_id)
    memo_images.mkdir(parents=True, exist_ok=True)
    (memo_images / "img_1.png").write_bytes(b"not really a png")
    evidence_images = data_dir / "images" / "evidence" / str(evidence_id)
    evidence_images.mkdir(parents=True)
    (evidence_images / "img_1.png").write_bytes(b"not really a png")

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204

    assert not evidence_images.exists()
    assert (memo_images / "img_1.png").is_file()


def test_deleting_an_evidence_succeeds_even_if_its_images_will_not_go(
    client: TestClient, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The evidence is gone the moment the row is; the files are housekeeping.

    Same rule as memo: a screenshot held open by a viewer on Windows cannot be
    unlinked, and reporting a failure would claim the evidence is still there.
    """
    evidence_id = new_evidence(client)
    evidence_images = data_dir / "images" / "evidence" / str(evidence_id)
    evidence_images.mkdir(parents=True)
    (evidence_images / "img_1.png").write_bytes(b"not really a png")

    def locked(path: Path, ignore_errors: bool = False, **kwargs: object) -> None:
        """`shutil.rmtree` meeting a file it cannot unlink.

        Left as it is when asked to ignore errors, raising otherwise — so this
        test fails if the deletion stops asking.
        """
        if not ignore_errors:
            raise PermissionError("[WinError 32] the file is open in another program")

    monkeypatch.setattr(shutil, "rmtree", locked)

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204
    assert client.get("/api/evidence").json() == []
    assert evidence_images.is_dir()


def test_a_new_evidence_never_inherits_images_left_by_an_earlier_one(
    client: TestClient, data_dir: Path
) -> None:
    """SQLite hands out the id of an evidence that is gone. If its screenshots
    could not be deleted, the next one to take that id must not adopt them."""
    stale = data_dir / "images" / "evidence" / "1"
    stale.mkdir(parents=True)
    (stale / "img_1.png").write_bytes(b"not really a png")

    evidence_id = new_evidence(client, "全新的一份")

    assert evidence_id == 1
    assert not (stale / "img_1.png").exists()
