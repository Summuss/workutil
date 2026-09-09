"""Tests for duplicating an evidence test case."""

import io
from pathlib import Path
from typing import Any

import openpyxl
from fastapi.testclient import TestClient
from PIL import Image as PILImage

from app.modules.evidence.service import SHEET_NAME_MAX_LENGTH, validate_case_name

from .conftest import SAMPLE_PNG, data_url


def make_png(width: int = 10, height: int = 10, color: str = "blue") -> bytes:
    im = PILImage.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def create_evidence(client: TestClient, title: str = "用例复制测试") -> int:
    res = client.post("/api/evidence", json={"title": title})
    assert res.status_code == 201
    return int(res.json()["id"])


def add_case(client: TestClient, evidence_id: int, name: str) -> int:
    res = client.post(f"/api/evidence/{evidence_id}/cases", json={"name": name})
    assert res.status_code == 201
    return int(res.json()["id"])


def test_duplicate_case_response_and_order(client: TestClient) -> None:
    evidence_id = create_evidence(client)
    c1 = add_case(client, evidence_id, "1")
    add_case(client, evidence_id, "2")
    add_case(client, evidence_id, "3")

    dup_res = client.post(f"/api/evidence/{evidence_id}/cases/{c1}/duplicate")
    assert dup_res.status_code == 200
    data = dup_res.json()

    cases = data["cases"]
    new_case_id = data["new_case_id"]

    assert len(cases) == 4
    names = [c["name"] for c in cases]
    assert names == ["1", "1 (2)", "2", "3"]

    # Orders are strictly contiguous from 0
    orders = [c["order"] for c in cases]
    assert orders == [0, 1, 2, 3]

    assert cases[1]["id"] == new_case_id
    assert cases[1]["name"] == "1 (2)"


def test_duplicate_case_blocks_deep_copied(client: TestClient) -> None:
    evidence_id = create_evidence(client)
    case_id = add_case(client, evidence_id, "用例1")

    # Add text block
    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": "一段测试步骤说明", "label": "步骤"},
    )

    # Add image block
    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "image",
            "image": {"data": data_url(SAMPLE_PNG), "filename": "shot.png"},
            "label": "截图",
        },
    )

    # Add table block (via paste endpoint)
    pb = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "paste",
            "text": "col1\tcol2\nval1\tval2",
            "label": "查询结果",
        },
    ).json()
    assert pb["kind"] == "table"

    # Duplicate case
    dup_res = client.post(f"/api/evidence/{evidence_id}/cases/{case_id}/duplicate")
    assert dup_res.status_code == 200
    new_case_id = dup_res.json()["new_case_id"]

    # Read duplicate case detail
    orig_detail = client.get(f"/api/evidence/{evidence_id}/cases/{case_id}").json()
    new_detail = client.get(f"/api/evidence/{evidence_id}/cases/{new_case_id}").json()

    orig_blocks = orig_detail["blocks"]
    new_blocks = new_detail["blocks"]

    assert len(new_blocks) == len(orig_blocks) == 3

    # All blocks have distinct IDs and new timestamps
    for orig_b, new_b in zip(orig_blocks, new_blocks, strict=True):
        assert new_b["id"] != orig_b["id"]
        assert new_b["kind"] == orig_b["kind"]
        assert new_b["label"] == orig_b["label"]
        assert new_b["order"] == orig_b["order"]
        assert new_b["text"] == orig_b["text"]

    # Image block has distinct image URL (pointing to distinct filename)
    assert new_blocks[1]["image_url"] != orig_blocks[1]["image_url"]

    # Table block has identical rows and has_header
    assert new_blocks[2]["rows"] == orig_blocks[2]["rows"]
    assert new_blocks[2]["has_header"] == orig_blocks[2]["has_header"]


def test_duplicate_case_naming_rules(client: TestClient) -> None:
    evidence_id = create_evidence(client)
    c1 = add_case(client, evidence_id, "1")

    # First duplicate -> 1 (2)
    d1 = client.post(f"/api/evidence/{evidence_id}/cases/{c1}/duplicate").json()
    assert d1["cases"][1]["name"] == "1 (2)"

    # Second duplicate of original -> 1 (3)
    d2 = client.post(f"/api/evidence/{evidence_id}/cases/{c1}/duplicate").json()
    dup_names = [c["name"] for c in d2["cases"]]
    assert "1 (3)" in dup_names

    # Casefold collision: sibling case "CASE 1 (4)" prevents "case 1 (4)"
    c_folded = add_case(client, evidence_id, "case 1")
    add_case(client, evidence_id, "CASE 1 (2)")
    d3 = client.post(f"/api/evidence/{evidence_id}/cases/{c_folded}/duplicate").json()
    new_name = next(c["name"] for c in d3["cases"] if c["id"] == d3["new_case_id"])
    assert new_name == "case 1 (3)"

    # Long name truncation: 31 chars
    long_name = "A" * SHEET_NAME_MAX_LENGTH
    c_long = add_case(client, evidence_id, long_name)
    d_long = client.post(f"/api/evidence/{evidence_id}/cases/{c_long}/duplicate").json()
    long_dup_name = next(
        c["name"] for c in d_long["cases"] if c["id"] == d_long["new_case_id"]
    )
    assert len(long_dup_name) <= SHEET_NAME_MAX_LENGTH
    assert long_dup_name.endswith(" (2)")
    assert validate_case_name(long_dup_name) == long_dup_name


def test_duplicate_case_not_found_returns_404(client: TestClient) -> None:
    evidence_id = create_evidence(client)
    other_evidence_id = create_evidence(client, "另一份 Evidence")
    other_case_id = add_case(client, other_evidence_id, "用例X")

    # Nonexistent case
    assert (
        client.post(f"/api/evidence/{evidence_id}/cases/99999/duplicate").status_code
        == 404
    )

    # Case belongs to other evidence
    assert (
        client.post(
            f"/api/evidence/{evidence_id}/cases/{other_case_id}/duplicate"
        ).status_code
        == 404
    )


def test_duplicate_image_file_on_disk_and_deletion_safety(
    client: TestClient, data_dir: Path
) -> None:
    evidence_id = create_evidence(client)
    case_id = add_case(client, evidence_id, "原用例")

    # Add image block
    ib = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "image",
            "image": {"data": data_url(SAMPLE_PNG), "filename": "shot.png"},
            "label": "原截图",
        },
    ).json()

    # Extract original file name from URL:
    # "/api/evidence/1/images/img_1.png" -> "img_1.png"
    orig_file_name = ib["image_url"].rsplit("/", 1)[-1]
    orig_file_path = (
        data_dir / "images" / "evidence" / str(evidence_id) / orig_file_name
    )
    assert orig_file_path.is_file()
    orig_bytes = orig_file_path.read_bytes()

    # Duplicate case
    dup_res = client.post(f"/api/evidence/{evidence_id}/cases/{case_id}/duplicate")
    assert dup_res.status_code == 200
    new_case_id = dup_res.json()["new_case_id"]

    new_detail = client.get(f"/api/evidence/{evidence_id}/cases/{new_case_id}").json()
    dup_ib = new_detail["blocks"][0]
    dup_file_name = dup_ib["image_url"].rsplit("/", 1)[-1]
    dup_file_path = data_dir / "images" / "evidence" / str(evidence_id) / dup_file_name

    # Two distinct filenames on disk
    assert dup_file_name != orig_file_name
    assert dup_file_path.is_file()
    assert dup_file_path.read_bytes() == orig_bytes

    # CORE SAFETY CHECK: Delete the duplicate case
    del_res = client.delete(f"/api/evidence/{evidence_id}/cases/{new_case_id}")
    assert del_res.status_code == 204

    # Duplicate file is gone, original file is PRESERVED!
    assert not dup_file_path.exists()
    assert orig_file_path.is_file()


def test_export_excel_with_duplicated_case(client: TestClient) -> None:
    evidence_id = create_evidence(client, "导出测试")
    case_id = add_case(client, evidence_id, "Case 1")

    # Add text, image, and table
    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": "步骤内容"},
    )
    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "image",
            "image": {"data": data_url(make_png()), "filename": "shot.png"},
        },
    )
    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "paste", "text": "h1\th2\nv1\tv2"},
    )

    # Duplicate case
    dup_res = client.post(f"/api/evidence/{evidence_id}/cases/{case_id}/duplicate")
    assert dup_res.status_code == 200

    # Export workbook
    exp_res = client.get(f"/api/evidence/{evidence_id}/export")
    assert exp_res.status_code == 200

    wb = openpyxl.load_workbook(io.BytesIO(exp_res.content))
    assert wb.sheetnames == ["Case 1", "Case 1 (2)"]

    ws1: Any = wb["Case 1"]
    ws2: Any = wb["Case 1 (2)"]

    # Both sheets have images
    assert len(ws1._images) == 1
    assert len(ws2._images) == 1

    # Both sheets have same cell content
    assert ws1["B3"].value == ws2["B3"].value
