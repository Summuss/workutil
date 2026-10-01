"""What a block's note promises: a line for the person recording, never delivered.

A note sits beside the label and differs from it in one thing only: the label
is part of the exported sheet and the note is not (CONTEXT.md 备注). Everything
else — every kind has one, blank means none, a duplicated case keeps it — is
the label's behaviour, pinned here at the HTTP seam (design.md §6 F5 测试接缝).
"""

import io
import zipfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

from .conftest import data_url
from .test_evidence_api import add_case, new_evidence
from .test_evidence_export_api import make_png

NOTE = "ここは 3 のはずが 5 になっている、要確認"


def add_block(client: TestClient, evidence_id: int, case_id: int, kind: str) -> int:
    """One block of `kind`, with a label so the export has something of its own."""
    payloads: dict[str, dict[str, Any]] = {
        "text": {"kind": "text", "text": "実行ログ"},
        "image": {"kind": "image", "image": {"data": data_url(make_png(40, 30))}},
        "table": {"kind": "paste", "text": "id\tname\n1\tfoo"},
    }
    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={**payloads[kind], "label": "小見出し"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["kind"] == kind
    block_id: int = created.json()["id"]
    return block_id


def set_note(
    client: TestClient, evidence_id: int, case_id: int, block_id: int, note: str | None
) -> dict[str, object]:
    res = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/note",
        json={"note": note},
    )
    assert res.status_code == 200, res.text
    body: dict[str, object] = res.json()
    return body


def blocks_of(
    client: TestClient, evidence_id: int, case_id: int
) -> list[dict[str, object]]:
    res = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}")
    assert res.status_code == 200, res.text
    blocks: list[dict[str, object]] = res.json()["blocks"]
    return blocks


@pytest.fixture
def case(client: TestClient) -> tuple[int, int]:
    evidence_id = new_evidence(client)
    return evidence_id, add_case(client, evidence_id, "1")


@pytest.mark.parametrize("kind", ["text", "image", "table"])
def test_every_kind_of_block_takes_a_note(
    client: TestClient, case: tuple[int, int], kind: str
) -> None:
    evidence_id, case_id = case
    block_id = add_block(client, evidence_id, case_id, kind)

    noted = set_note(client, evidence_id, case_id, block_id, NOTE)

    assert noted["note"] == NOTE
    assert blocks_of(client, evidence_id, case_id)[0]["note"] == NOTE


def test_a_new_block_has_no_note(client: TestClient, case: tuple[int, int]) -> None:
    evidence_id, case_id = case
    add_block(client, evidence_id, case_id, "text")

    assert blocks_of(client, evidence_id, case_id)[0]["note"] is None


@pytest.mark.parametrize("cleared", [None, "", "   "])
def test_a_blank_note_is_no_note(
    client: TestClient, case: tuple[int, int], cleared: str | None
) -> None:
    evidence_id, case_id = case
    block_id = add_block(client, evidence_id, case_id, "text")
    set_note(client, evidence_id, case_id, block_id, NOTE)

    emptied = set_note(client, evidence_id, case_id, block_id, cleared)

    assert emptied["note"] is None
    assert blocks_of(client, evidence_id, case_id)[0]["note"] is None


def test_a_note_is_stored_without_its_surrounding_space(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block_id = add_block(client, evidence_id, case_id, "text")

    set_note(client, evidence_id, case_id, block_id, "  要確認  ")

    assert blocks_of(client, evidence_id, case_id)[0]["note"] == "要確認"


def test_the_note_and_the_label_are_set_independently(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block_id = add_block(client, evidence_id, case_id, "text")

    set_note(client, evidence_id, case_id, block_id, NOTE)

    block = blocks_of(client, evidence_id, case_id)[0]
    assert block["label"] == "小見出し"
    assert block["note"] == NOTE


def test_noting_a_nonexistent_block_returns_404(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    res = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/999999/note",
        json={"note": NOTE},
    )

    assert res.status_code == 404


def test_a_duplicated_case_keeps_its_notes_apart(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Copied like everything else in the case, and from then on its own."""
    evidence_id, case_id = case
    block_id = add_block(client, evidence_id, case_id, "image")
    set_note(client, evidence_id, case_id, block_id, NOTE)

    dup = client.post(f"/api/evidence/{evidence_id}/cases/{case_id}/duplicate")
    assert dup.status_code == 200, dup.text
    copy_id = dup.json()["new_case_id"]
    copied = blocks_of(client, evidence_id, copy_id)[0]
    assert copied["note"] == NOTE

    set_note(client, evidence_id, copy_id, int(str(copied["id"])), "副本だけ")

    assert blocks_of(client, evidence_id, case_id)[0]["note"] == NOTE


def test_a_note_never_reaches_the_exported_workbook(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Not as a cell, not as an Excel comment, not anywhere in the file: every
    part of the xlsx is searched, so a note turning up in a new place still
    fails here."""
    evidence_id, case_id = case
    for kind in ("text", "image", "table"):
        block_id = add_block(client, evidence_id, case_id, kind)
        set_note(client, evidence_id, case_id, block_id, NOTE)

    res = client.get(f"/api/evidence/{evidence_id}/export")
    assert res.status_code == 200, res.text

    with zipfile.ZipFile(io.BytesIO(res.content)) as xlsx:
        parts = {name: xlsx.read(name) for name in xlsx.namelist()}
    assert any("小見出し".encode() in data for data in parts.values())
    assert not [name for name, data in parts.items() if NOTE.encode() in data]
