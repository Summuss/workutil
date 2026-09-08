"""Excel layout and workbook rendering for evidence.

M2's delivery point: turns an Evidence and its Cases into an Excel workbook.
Centralises layout parameters in `LayoutSettings` (design.md §6 F5).

Hard format limits respected:
- Excel row height caps at 409 pt (= 545 px at 96 DPI). Screenshots exceed this,
  so we never resize row height for images. Instead, row height stays at the
  default 15 pt = 20 px, and we reserve ceil(height / 20) rows so the next block
  starts beneath the floating image.
- Image width is scaled proportionally to at most 900 px without touching the
  original on disk.
- All cells use the '@' text number format so 007, dates, and long IDs stay as
  typed without Excel reinterpreting them (ADR-0004).
- Plain cells are formatted directly: no ListObjects (Excel Tables) that force
  column names to be unique.
- One sheet per case, named after the case.
"""

import io
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import openpyxl
from openpyxl.drawing.image import Image as OpenPyxlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage

from app.modules.evidence.models import (
    BlockKind,
    Evidence,
    EvidenceBlock,
    EvidenceCase,
)

ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')

BorderStyle = Literal[
    "dashDot",
    "dashDotDot",
    "dashed",
    "dotted",
    "double",
    "hair",
    "medium",
    "mediumDashDot",
    "mediumDashDotDot",
    "mediumDashed",
    "slantDashDot",
    "thick",
    "thin",
    "none",
]


@dataclass(frozen=True)
class LayoutSettings:
    """Concentrated layout parameters for Excel export.

    Kept in code rather than a configuration file (design.md §6 F5): the goal in
    the first milestone is centralising the numbers so they are not scattered
    across export routines. A corporate template later can swap the source
    without rewriting the layout logic.
    """

    column_width: float = 18.0
    max_image_width: int = 900
    row_height_px: int = 20
    header_fill_color: str = "87E7AD"
    border_style: BorderStyle = "thin"


DEFAULT_LAYOUT_SETTINGS = LayoutSettings()


def scale_dimensions(width: int, height: int, max_width: int = 900) -> tuple[int, int]:
    """Scale an image proportionally to at most `max_width`.

    If width is already <= max_width, returns original dimensions.
    Very small images are never scaled up.
    Aspect ratio is strictly preserved.
    """
    if width <= 0 or height <= 0:
        return (max(0, width), max(0, height))
    if width <= max_width:
        return (width, height)
    scale = max_width / width
    scaled_height = max(1, round(height * scale))
    return (max_width, scaled_height)


def calculate_reserved_rows(height_px: int, row_height_px: int = 20) -> int:
    """How many Excel rows (at default row height) to reserve for an image.

    Excel row height caps at 409 pt = 545 px, which screenshots easily exceed.
    Setting row height directly is a dead end. Instead, row height stays at the
    default 15 pt = 20 px, and we reserve ceil(height / 20) rows so the next
    block begins cleanly beneath the floating image.
    """
    if height_px <= 0:
        return 0
    return math.ceil(height_px / row_height_px)


def sanitize_filename(title: str) -> str:
    """Replace filesystem-illegal characters with underscores.

    Follows the convention: エビデンス_<title>.xlsx, where any of
    \\ / : * ? " < > | are replaced with _.
    """
    clean_title = ILLEGAL_FILENAME_CHARS.sub("_", title)
    return f"エビデンス_{clean_title}.xlsx"


def build_evidence_workbook(
    evidence: Evidence,
    cases_with_blocks: list[tuple[EvidenceCase, list[EvidenceBlock]]],
    evidence_images_dir: Path,
    settings: LayoutSettings = DEFAULT_LAYOUT_SETTINGS,
) -> bytes:
    """Build an Excel workbook from an evidence and its cases.

    - One case per sheet, named after the case.
    - Single vertical column: blocks go downward starting from column A, separated
      by one empty row.
    - An optional label occupies its own row in bold font.
    - Images reserve rows based on their scaled height, anchoring floating images
      at column A of their start row.
    - Tables format their header in bold + header fill color with thin borders on
      every cell.
    - All cells are typed with '@' text number format.
    """
    wb = openpyxl.Workbook()

    thin_side = Side(style=settings.border_style)
    thin_border = Border(
        left=thin_side, right=thin_side, top=thin_side, bottom=thin_side
    )
    header_fill = PatternFill(
        start_color=settings.header_fill_color,
        end_color=settings.header_fill_color,
        fill_type="solid",
    )

    for case_index, (case, blocks) in enumerate(cases_with_blocks):
        if case_index == 0:
            ws = wb.active
            assert ws is not None
            ws.title = case.name
        else:
            ws = wb.create_sheet(title=case.name)

        # Work out maximum columns in this case for setting uniform column width.
        # Tables in the same case share column widths (design.md §6 F5).
        max_cols = 1
        for block in blocks:
            if block.kind == BlockKind.TABLE and block.rows:
                for row_cells in block.rows:
                    if len(row_cells) > max_cols:
                        max_cols = len(row_cells)

        for col_idx in range(1, max_cols + 1):
            ws.column_dimensions[
                get_column_letter(col_idx)
            ].width = settings.column_width
        ws.sheet_format.defaultColWidth = settings.column_width

        # A case with 0 blocks produces an empty sheet with its name.
        if not blocks:
            continue

        current_row = 1
        for block_index, block in enumerate(blocks):
            # Blocks are separated by one empty row
            if block_index > 0:
                current_row += 1

            # Optional label occupies a single bold row
            if block.label and block.label.strip():
                label_cell = ws.cell(
                    row=current_row, column=1, value=block.label.strip()
                )
                label_cell.font = Font(bold=True)
                label_cell.number_format = "@"
                current_row += 1

            if block.kind == BlockKind.TEXT:
                text_cell = ws.cell(row=current_row, column=1, value=block.text)
                text_cell.number_format = "@"
                text_cell.alignment = Alignment(wrap_text=True, vertical="top")
                current_row += 1

            elif block.kind == BlockKind.IMAGE:
                img_path = evidence_images_dir / block.image_name
                if img_path.is_file():
                    with PILImage.open(img_path) as pil_img:
                        orig_w, orig_h = pil_img.size

                    scaled_w, scaled_h = scale_dimensions(
                        orig_w, orig_h, settings.max_image_width
                    )
                    reserved = calculate_reserved_rows(scaled_h, settings.row_height_px)

                    xl_img = OpenPyxlImage(str(img_path))
                    xl_img.width = scaled_w
                    xl_img.height = scaled_h
                    ws.add_image(xl_img, f"A{current_row}")
                    current_row += reserved
                else:
                    placeholder = ws.cell(
                        row=current_row,
                        column=1,
                        value=f"[图片缺失: {block.image_name}]",
                    )
                    placeholder.number_format = "@"
                    current_row += 1

            elif block.kind == BlockKind.TABLE:
                for r_idx, row_cells in enumerate(block.rows):
                    row_num = current_row + r_idx
                    is_header = r_idx == 0 and block.has_header

                    for c_idx, cell_value in enumerate(row_cells):
                        col_num = c_idx + 1
                        cell = ws.cell(
                            row=row_num, column=col_num, value=str(cell_value)
                        )
                        cell.number_format = "@"
                        cell.border = thin_border
                        if is_header:
                            cell.font = Font(bold=True)
                            cell.fill = header_fill
                        else:
                            cell.font = Font(bold=False)

                current_row += len(block.rows)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
