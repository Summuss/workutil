"""The parts of putting red boxes into a workbook that the export seam cannot reach.

What the boxes look like once exported is asserted through the export API
(`test_evidence_export_api.py`); these are the refusals a well-formed export
never triggers — the guards against pairing boxes with the wrong sheet or the
wrong screenshot — and the shortcut taken when there is nothing to add.
"""

from pathlib import Path

import pytest
from PIL import Image

from app.modules.evidence.box_export import BoxStyle, ImageBoxes, inject_boxes
from app.modules.evidence.layout import build_evidence_workbook
from app.modules.evidence.models import (
    BlockKind,
    Evidence,
    EvidenceBlock,
    EvidenceCase,
)

STYLE = BoxStyle(color="FF0000", line_emu=28575)


def test_a_workbook_without_boxes_comes_back_as_the_same_bytes() -> None:
    raw = b"fake-excel-bytes"
    res = inject_boxes(raw, [[ImageBoxes(src_width=100, src_height=100)]], STYLE)
    assert res is raw


def test_boxes_for_a_different_number_of_sheets_are_refused(tmp_path: Path) -> None:
    ev = Evidence(title="SheetMismatch")
    cases = [
        (
            EvidenceCase(name="Sheet1"),
            [
                EvidenceBlock(
                    kind=BlockKind.TEXT,
                    text="hi",
                    split_lines=True,
                    image_name="",
                    rows=[],
                    has_header=False,
                )
            ],
        )
    ]
    data = build_evidence_workbook(ev, cases, tmp_path)

    # 1 sheet in workbook, but 2 sheets provided
    with pytest.raises(ValueError, match="2 份图片清单"):
        inject_boxes(
            data,
            [
                [
                    ImageBoxes(
                        src_width=10,
                        src_height=10,
                        boxes=[{"x": 0, "y": 0, "w": 5, "h": 5}],
                    )
                ],
                [],
            ],
            STYLE,
        )


def test_boxes_for_a_different_number_of_screenshots_are_refused(
    tmp_path: Path,
) -> None:
    # 1 image in sheet, but 2 ImageBoxes provided with a box
    img_path = tmp_path / "one.png"
    im = Image.new("RGB", (100, 100), color="blue")
    im.save(img_path)

    ev = Evidence(title="AnchorMismatch")
    cases = [
        (
            EvidenceCase(name="Case1"),
            [
                EvidenceBlock(
                    kind=BlockKind.IMAGE,
                    text="",
                    image_name="one.png",
                    rows=[],
                    has_header=False,
                    split_lines=True,
                )
            ],
        )
    ]
    # Build without boxes
    data = build_evidence_workbook(ev, cases, tmp_path)

    with pytest.raises(ValueError, match="却给了 2 张图的红框"):
        inject_boxes(
            data,
            [
                [
                    ImageBoxes(
                        src_width=100,
                        src_height=100,
                        boxes=[{"x": 0, "y": 0, "w": 10, "h": 10}],
                    ),
                    ImageBoxes(src_width=100, src_height=100),
                ]
            ],
            STYLE,
        )
