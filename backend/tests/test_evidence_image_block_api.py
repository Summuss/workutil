"""What an image Block promises: one screenshot, and a file that follows it.

The HTTP boundary is the agreed test seam (design.md §6 F5 测试接缝). Everything
a block already has — a label, a place in the order, a case that owns it —
comes from `test_evidence_block_api.py`; what is here is the half that touches
the disk.

**Evidence deletes its screenshots, and that is a deliberate departure from
Memo.** Memo does not count references because they are parsed out of Markdown
and cutting a paragraph is a moment where the count is 0; an image block *is*
one screenshot, with no such moment, so deleting one says "not this one"
(design.md §5). The three-level deletion below is that rule, and the tests that
tolerate a file which will not go are the other half of it: the row is already
gone, and an error would claim otherwise.
"""

import io
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage

from .conftest import SAMPLE_PNG, SAMPLE_PNG_2, data_url, workutil_at
from .test_evidence_api import add_case, new_evidence
from .test_evidence_block_api import add_text, blocks_of


def add_image(
    client: TestClient,
    evidence_id: int,
    case_id: int,
    raw: bytes = SAMPLE_PNG,
    filename: str = "screenshot.png",
    label: str | None = None,
) -> dict[str, Any]:
    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "image",
            "image": {"data": data_url(raw), "filename": filename},
            "label": label,
        },
    )
    assert created.status_code == 201, created.text
    block: dict[str, Any] = created.json()
    return block


def images_dir_of(data_dir: Path, evidence_id: int) -> Path:
    return data_dir / "images" / "evidence" / str(evidence_id)


def file_of(block: dict[str, Any]) -> str:
    """The name this block's screenshot was stored under.

    Read off the URL rather than spelled out: a stored name carries a token so
    that no name is ever handed out twice (`core/images.next_name`), which
    makes it deliberately unpredictable. A test that wrote the name itself
    would be asserting the one thing that is not promised.
    """
    return str(block["image_url"]).rsplit("/", 1)[-1]


@pytest.fixture
def case(client: TestClient) -> tuple[int, int]:
    """One evidence with one case in it — where a screenshot goes."""
    evidence_id = new_evidence(client)
    return evidence_id, add_case(client, evidence_id, "1")


# --- Pasting ----------------------------------------------------------------


def test_a_pasted_screenshot_becomes_an_image_block(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = add_image(client, evidence_id, case_id)

    assert block["kind"] == "image"
    assert blocks_of(client, evidence_id, case_id) == [block]

    served = client.get(block["image_url"])
    assert served.status_code == 200
    assert served.content == SAMPLE_PNG


def test_the_screenshot_is_kept_whole_under_the_evidence_directory(
    client: TestClient, case: tuple[int, int], data_dir: Path
) -> None:
    """Stored uncompressed, byte for byte: the only resizing this tool does
    happens on the copy inside an exported workbook (ticket 07)."""
    evidence_id, case_id = case

    block = add_image(client, evidence_id, case_id)

    saved = images_dir_of(data_dir, evidence_id) / file_of(block)
    assert saved.read_bytes() == SAMPLE_PNG


def test_each_pasted_screenshot_is_a_block_of_its_own(
    client: TestClient, case: tuple[int, int]
) -> None:
    """One image block holds one image, so pasting three makes three — each
    with its own label and its own place in the order (design.md §6 F5)."""
    evidence_id, case_id = case

    first = add_image(client, evidence_id, case_id, SAMPLE_PNG, "1.png")
    second = add_image(client, evidence_id, case_id, SAMPLE_PNG_2, "2.png")
    third = add_image(client, evidence_id, case_id, SAMPLE_PNG, "3.png")

    assert blocks_of(client, evidence_id, case_id) == [first, second, third]
    assert client.get(second["image_url"]).content == SAMPLE_PNG_2


def test_screenshots_of_one_evidence_share_a_directory_without_colliding(
    client: TestClient, case: tuple[int, int], data_dir: Path
) -> None:
    """One directory per evidence, not per case: the names have to be found
    against what is already there, whichever case put it there."""
    evidence_id, first_case = case
    second_case = add_case(client, evidence_id, "2")

    here = add_image(client, evidence_id, first_case, SAMPLE_PNG)
    there = add_image(client, evidence_id, second_case, SAMPLE_PNG_2)

    assert here["image_url"] != there["image_url"]
    assert client.get(here["image_url"]).content == SAMPLE_PNG
    assert client.get(there["image_url"]).content == SAMPLE_PNG_2
    assert len(list(images_dir_of(data_dir, evidence_id).iterdir())) == 2


def test_an_image_block_takes_a_label_and_a_place_like_any_other(
    client: TestClient, case: tuple[int, int]
) -> None:
    """The label and the order belong to every kind of block; only the payload
    is the image's own."""
    evidence_id, case_id = case
    add_text(client, evidence_id, case_id, "事前準備")
    block = add_image(client, evidence_id, case_id, label="検索画面")

    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}"
    assert client.post(f"{at}/move", json={"to": "top"}).status_code == 200
    relabelled = client.put(f"{at}/label", json={"label": "検索結果の画面"})

    assert relabelled.status_code == 200, relabelled.text
    assert relabelled.json()["label"] == "検索結果の画面"
    assert [one["kind"] for one in blocks_of(client, evidence_id, case_id)] == [
        "image",
        "text",
    ]


def test_a_screenshot_is_never_stored_as_a_scriptable_document(
    client: TestClient, case: tuple[int, int], data_dir: Path
) -> None:
    """SVG is a document that can run scripts, and it would be served from this
    app's own origin — the chain design.md §6 F1 exists to cut. The bytes are
    kept as they arrived; only the name is decided here, the same way memo's
    are, because both go through `core/images.py`.
    """
    evidence_id, case_id = case

    block = add_image(client, evidence_id, case_id, filename="diagram.svg")

    assert file_of(block).endswith(".png")
    assert (images_dir_of(data_dir, evidence_id) / file_of(block)).is_file()


def test_a_served_screenshot_is_not_sniffed(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id)

    served = client.get(block["image_url"])

    assert served.headers["x-content-type-options"] == "nosniff"


def test_a_screenshot_is_not_reachable_through_another_evidence(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id)
    other = new_evidence(client, "別件")

    assert (
        client.get(f"/api/evidence/{other}/images/{file_of(block)}").status_code == 404
    )


@pytest.mark.parametrize(
    "filename",
    [
        "../hack.png",
        "..%2Fhack.png",
        "sub/dir.png",
        # Drive-relative, and carrying none of the characters the other three
        # are caught by. On this platform it is refused for want of a file; on
        # Windows — a target platform — it names something outside the
        # directory, and the guard below is what refuses it there.
        "C:hack.png",
    ],
)
def test_asking_for_a_file_outside_the_directory_is_a_404(
    client: TestClient, case: tuple[int, int], filename: str
) -> None:
    evidence_id, _ = case

    got = client.get(f"/api/evidence/{evidence_id}/images/{filename}")

    assert got.status_code == 404


def test_a_name_that_leads_out_of_the_directory_is_a_404(
    client: TestClient, case: tuple[int, int], data_dir: Path, tmp_path: Path
) -> None:
    """Refused by where the name lands, not only by what it is made of.

    Checking characters is a rule about spelling and the filesystem is not
    spelling: a name can be perfectly ordinary and still resolve outside. Here
    that is a symlink; on Windows it is a drive-relative name.
    """
    evidence_id, case_id = case
    add_image(client, evidence_id, case_id)
    outside = tmp_path / "secret.png"
    outside.write_bytes(b"not yours")
    (images_dir_of(data_dir, evidence_id) / "escape.png").symlink_to(outside)

    got = client.get(f"/api/evidence/{evidence_id}/images/escape.png")

    assert got.status_code == 404


def test_a_screenshot_that_is_not_there_is_a_404(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, _ = case

    assert (
        client.get(f"/api/evidence/{evidence_id}/images/img_1.png").status_code == 404
    )


def test_image_blocks_survive_a_restart(data_dir: Path) -> None:
    with workutil_at(data_dir) as before:
        evidence_id = new_evidence(before, "跨重启")
        case_id = add_case(before, evidence_id, "1")
        block = add_image(before, evidence_id, case_id, label="検索画面")

    with workutil_at(data_dir) as after:
        kept = blocks_of(after, evidence_id, case_id)
        assert kept == [block]
        assert after.get(block["image_url"]).content == SAMPLE_PNG


# --- What an image block is not ---------------------------------------------


def test_an_image_block_carries_no_text(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Text is one kind's payload. Writing over an image block with words would
    leave a block claiming to be a picture with a paragraph inside it."""
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id)

    assert block["text"] == ""
    refused = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}",
        json={"text": "書き換え"},
    )

    assert refused.status_code == 422
    assert blocks_of(client, evidence_id, case_id) == [block]


def test_an_image_block_without_an_image_is_refused(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "image", "text": "画像のつもり"},
    )

    assert refused.status_code == 422
    assert blocks_of(client, evidence_id, case_id) == []


def test_a_screenshot_that_will_not_decode_leaves_nothing_behind(
    client: TestClient, case: tuple[int, int], data_dir: Path
) -> None:
    evidence_id, case_id = case

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "image",
            "image": {"data": "data:image/png;base64,not base64!", "filename": "x.png"},
        },
    )

    assert refused.status_code == 422
    assert blocks_of(client, evidence_id, case_id) == []
    assert not images_dir_of(data_dir, evidence_id).exists()


def test_an_oversized_screenshot_is_refused(
    client: TestClient, case: tuple[int, int]
) -> None:
    from app.core.images import MAX_IMAGE_BYTES

    evidence_id, case_id = case

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "image",
            "image": {
                "data": data_url(b"\x00" * (MAX_IMAGE_BYTES + 1)),
                "filename": "big.png",
            },
        },
    )

    assert refused.status_code == 422
    assert blocks_of(client, evidence_id, case_id) == []


# --- Deleting: block, case, evidence ----------------------------------------


def test_deleting_an_image_block_deletes_its_file(
    client: TestClient, case: tuple[int, int], data_dir: Path
) -> None:
    """The point of the whole departure from memo's rule: one image block is
    one screenshot, so deleting it is an unambiguous "not this one"."""
    evidence_id, case_id = case
    doomed = add_image(client, evidence_id, case_id, SAMPLE_PNG, "doomed.png")
    kept = add_image(client, evidence_id, case_id, SAMPLE_PNG_2, "kept.png")

    deleted = client.delete(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{doomed['id']}"
    )

    assert deleted.status_code == 204
    assert not (images_dir_of(data_dir, evidence_id) / file_of(doomed)).exists()
    assert client.get(kept["image_url"]).content == SAMPLE_PNG_2
    assert blocks_of(client, evidence_id, case_id) == [{**kept, "order": 0}]


def test_the_screenshot_after_a_deleted_one_does_not_inherit_its_name(
    client: TestClient, case: tuple[int, int]
) -> None:
    """A stored name is never handed out twice, and this is the flow that used
    to hand one out twice.

    "Pasted the wrong screenshot, delete it, paste the right one" freed the
    lowest name and immediately gave it back, so the new block was served at
    the very URL the browser was already holding the wrong picture under — and
    drew the wrong one again, without asking (`core/images.next_name`).
    """
    evidence_id, case_id = case
    wrong = add_image(client, evidence_id, case_id, SAMPLE_PNG, "wrong.png")
    deleted = client.delete(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{wrong['id']}"
    )
    assert deleted.status_code == 204

    right = add_image(client, evidence_id, case_id, SAMPLE_PNG_2, "right.png")

    assert file_of(right) != file_of(wrong)
    assert client.get(right["image_url"]).content == SAMPLE_PNG_2


def test_deleting_a_case_deletes_the_screenshots_it_held(
    client: TestClient, data_dir: Path
) -> None:
    """A case's screenshots go with it — and only its own: the cases of one
    evidence share a directory."""
    evidence_id = new_evidence(client)
    doomed = add_case(client, evidence_id, "1")
    kept = add_case(client, evidence_id, "2")
    add_image(client, evidence_id, doomed, SAMPLE_PNG, "a.png")
    add_image(client, evidence_id, doomed, SAMPLE_PNG, "b.png")
    survivor = add_image(client, evidence_id, kept, SAMPLE_PNG_2, "c.png")

    assert (
        client.delete(f"/api/evidence/{evidence_id}/cases/{doomed}").status_code == 204
    )

    assert [path.name for path in images_dir_of(data_dir, evidence_id).iterdir()] == [
        file_of(survivor)
    ]
    assert client.get(survivor["image_url"]).content == SAMPLE_PNG_2


def test_deleting_a_case_leaves_the_text_blocks_of_other_cases_alone(
    client: TestClient, data_dir: Path
) -> None:
    """A case of only text has no files to clean up, and must not take the
    directory down with it."""
    evidence_id = new_evidence(client)
    doomed = add_case(client, evidence_id, "1")
    kept = add_case(client, evidence_id, "2")
    add_text(client, evidence_id, doomed, "文字だけ")
    survivor = add_image(client, evidence_id, kept, SAMPLE_PNG)

    assert (
        client.delete(f"/api/evidence/{evidence_id}/cases/{doomed}").status_code == 204
    )

    assert client.get(survivor["image_url"]).content == SAMPLE_PNG


def test_deleting_an_evidence_deletes_every_screenshot_in_it(
    client: TestClient, data_dir: Path
) -> None:
    evidence_id = new_evidence(client)
    first = add_case(client, evidence_id, "1")
    second = add_case(client, evidence_id, "2")
    add_image(client, evidence_id, first, SAMPLE_PNG)
    add_image(client, evidence_id, second, SAMPLE_PNG_2)

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204

    assert not images_dir_of(data_dir, evidence_id).exists()


# --- Deleting when the file will not go --------------------------------------


@pytest.fixture
def unlinkable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A screenshot held open by a viewer on Windows, which cannot be unlinked.

    Patched at `os.unlink`, which is the one call under all three levels —
    `Path.unlink` for a block or a case, `shutil.rmtree` for an evidence — so
    each of the three below meets a real refusal from the filesystem rather
    than a stub of the function it happens to call today.

    The rule this pins down: the row is already gone, so reporting a failure
    would tell the author their block is still there.
    """

    def locked(path: object, *args: object, **kwargs: object) -> None:
        raise PermissionError("[WinError 32] the file is open in another program")

    monkeypatch.setattr(os, "unlink", locked)


def test_deleting_an_image_block_succeeds_even_if_the_file_will_not_go(
    client: TestClient, case: tuple[int, int], data_dir: Path, unlinkable: None
) -> None:
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id)

    deleted = client.delete(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}"
    )

    assert deleted.status_code == 204
    assert blocks_of(client, evidence_id, case_id) == []
    assert (images_dir_of(data_dir, evidence_id) / file_of(block)).is_file()


def test_deleting_a_case_succeeds_even_if_its_screenshots_will_not_go(
    client: TestClient, case: tuple[int, int], data_dir: Path, unlinkable: None
) -> None:
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id)

    deleted = client.delete(f"/api/evidence/{evidence_id}/cases/{case_id}")

    assert deleted.status_code == 204
    assert client.get(f"/api/evidence/{evidence_id}").json()["cases"] == []
    assert (images_dir_of(data_dir, evidence_id) / file_of(block)).is_file()


def test_deleting_an_evidence_succeeds_even_if_its_screenshots_will_not_go(
    client: TestClient, case: tuple[int, int], data_dir: Path, unlinkable: None
) -> None:
    """The directory goes by `shutil.rmtree`, which is asked to ignore what it
    cannot remove — this is what says it is still being asked."""
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id)

    assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204
    assert client.get("/api/evidence").json() == []
    assert (images_dir_of(data_dir, evidence_id) / file_of(block)).is_file()


# --- Red boxes -------------------------------------------------------------


def _png_bytes(width: int, height: int) -> bytes:
    im = PILImage.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def boxes_at(evidence_id: int, case_id: int, block_id: int) -> str:
    return f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/boxes"


def test_a_screenshot_keeps_the_red_boxes_drawn_on_it(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id, raw=_png_bytes(100, 80))
    assert block["boxes"] == []

    boxes = [
        {"x": 10, "y": 15, "w": 30, "h": 20},
        {"x": 50, "y": 40, "w": 25, "h": 35},
    ]
    res = client.put(boxes_at(evidence_id, case_id, block["id"]), json={"boxes": boxes})
    assert res.status_code == 200
    assert res.json()["boxes"] == boxes

    detail = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}").json()
    assert detail["blocks"][0]["boxes"] == boxes


@pytest.mark.parametrize(
    "box",
    [
        pytest.param({"x": 80, "y": 10, "w": 25, "h": 10}, id="past the right edge"),
        pytest.param({"x": 10, "y": 75, "w": 10, "h": 10}, id="past the bottom"),
        pytest.param({"x": 0, "y": 0, "w": 0, "h": 10}, id="no width"),
        pytest.param({"x": -1, "y": 0, "w": 10, "h": 10}, id="left of the image"),
    ],
)
def test_a_red_box_off_the_screenshot_is_refused(
    client: TestClient, case: tuple[int, int], box: dict[str, int]
) -> None:
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id, raw=_png_bytes(100, 80))

    res = client.put(boxes_at(evidence_id, case_id, block["id"]), json={"boxes": [box]})

    assert res.status_code == 422
    detail = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}").json()
    assert detail["blocks"][0]["boxes"] == []


def test_only_a_screenshot_takes_red_boxes(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    text_block_id = add_text(client, evidence_id, case_id, "普通文字段落")

    res = client.put(
        boxes_at(evidence_id, case_id, text_block_id),
        json={"boxes": [{"x": 0, "y": 0, "w": 10, "h": 10}]},
    )

    assert res.status_code == 422
    detail = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}").json()
    assert detail["blocks"][0]["boxes"] == []


def test_sending_no_boxes_takes_every_red_box_off(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id, raw=_png_bytes(100, 80))
    url = boxes_at(evidence_id, case_id, block["id"])
    client.put(url, json={"boxes": [{"x": 10, "y": 10, "w": 20, "h": 20}]})

    cleared = client.put(url, json={"boxes": []})

    assert cleared.status_code == 200
    assert cleared.json()["boxes"] == []
    detail = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}").json()
    assert detail["blocks"][0]["boxes"] == []


def test_a_duplicated_case_has_its_own_copy_of_the_red_boxes(
    client: TestClient, case: tuple[int, int]
) -> None:
    """`duplicate_case` copies a block field by field; one it misses is lost."""
    evidence_id, case_id = case
    block = add_image(client, evidence_id, case_id, raw=_png_bytes(100, 80))
    boxes = [{"x": 5, "y": 5, "w": 30, "h": 20}]
    client.put(boxes_at(evidence_id, case_id, block["id"]), json={"boxes": boxes})

    dup_res = client.post(f"/api/evidence/{evidence_id}/cases/{case_id}/duplicate")
    assert dup_res.status_code == 200
    new_case_id = dup_res.json()["new_case_id"]
    dup_block = client.get(f"/api/evidence/{evidence_id}/cases/{new_case_id}").json()[
        "blocks"
    ][0]
    assert dup_block["boxes"] == boxes

    new_boxes = [{"x": 40, "y": 40, "w": 10, "h": 10}]
    client.put(
        boxes_at(evidence_id, new_case_id, dup_block["id"]), json={"boxes": new_boxes}
    )
    orig = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}").json()
    assert orig["blocks"][0]["boxes"] == boxes

    client.delete(f"/api/evidence/{evidence_id}/cases/{new_case_id}")
    after_del = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}").json()
    assert after_del["blocks"][0]["boxes"] == boxes
