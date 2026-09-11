"""Excel layout and workbook rendering for evidence.

M2's delivery point: turns an Evidence and its Cases into an Excel workbook.
Centralises layout parameters in `LayoutSettings` (design.md §6 F5).

Hard format limits respected:
- Excel row height caps at 409 pt (= 545 px at 96 DPI). Screenshots exceed this,
  so we never resize row height for images. Instead, each reserved row is
  written at 15 pt = 20 px, and we reserve ceil(height / 20) of them so the next
  block starts beneath the floating image. The height is written rather than
  left to the default on purpose — see `_reserve_rows_for_image`.
- Image width is scaled proportionally to at most 900 px without touching the
  original on disk.
- What is embedded is scaled down too, not just what is displayed — see
  `_picture_for`. The stored screenshot stays the original either way.
- All cells use the '@' text number format so 007, dates, and long IDs stay as
  typed without Excel reinterpreting them (ADR-0004). '@' alone does not stop
  openpyxl from reading a leading '=' as a formula, so every cell also has its
  `data_type` forced back to 's' after assignment (see `_text_cell`).
- Plain cells are formatted directly: no ListObjects (Excel Tables) that force
  column names to be unique.
- One sheet per case, named after the case.
- A missing image file refuses the whole export rather than writing a
  placeholder in its place — see `MissingImageFile`.
"""

import io
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import openpyxl
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE, Cell
from openpyxl.drawing.image import Image as OpenPyxlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from PIL import Image as PILImage

from app.modules.evidence.models import (
    BlockKind,
    Evidence,
    EvidenceBlock,
    EvidenceCase,
)

ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


class MissingImageFile(ValueError):
    """An image block points at a file that is not on disk.

    Raised rather than papered over with placeholder text: the exported
    workbook is the deliverable, and silently swapping a screenshot for a
    sentence would hand someone a file they never got to check — the same
    reasoning design.md gives for validating a sheet name on the way in
    (§6 F5 Excel 导出).
    """

    code = "evidence.missing_image_file"


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
    #: How much bigger than it is drawn a screenshot may travel, in pixels of
    #: width per pixel displayed. 1.0 embeds exactly what is shown and holds
    #: the least; above that is detail kept back for zooming into and for
    #: screens that draw the 900 px at 125% or 150%. Turn it *down* if 「この
    #: 画像は表示できません」 ever comes back — it is the only number in here
    #: that decides how much bitmap Excel has to hold at once (`_picture_for`).
    embedded_image_scale: float = 2.0
    row_height_px: int = 20
    header_fill_color: str = "87E7AD"
    border_style: BorderStyle = "thin"
    font_name: str = "游ゴシック"
    font_size: int = 11
    literal_colors: dict[str, str] = field(
        default_factory=lambda: {"\u226a NULL \u226b": "808080"}
    )

    @property
    def row_height_pt(self) -> float:
        """The reserved row height in the unit Excel stores it in.

        A point is 1/72 inch and a pixel 1/96, which is where 0.75 comes from
        and the only place the two units meet.
        """
        return self.row_height_px * 0.75


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
    Making one row as tall as the image is therefore a dead end. Instead each
    row is a known 15 pt = 20 px and we reserve ceil(height / 20) of them, so
    the next block begins cleanly beneath the floating image.

    Known, and not merely assumed: `_reserve_rows_for_image` writes that height
    onto every row it counts here.

    A degenerate height (<= 0) still reserves one row rather than zero: an
    image placed and then given no room at all is exactly the overlap this
    function exists to prevent. Real images never hit this branch — PIL never
    reports a non-positive size for a file that opened at all — but the
    invariant ("placing an image always claims at least one row") should hold
    regardless of what a caller hands in.
    """
    if height_px <= 0:
        return 1
    return math.ceil(height_px / row_height_px)


#: The modes a screenshot can be resampled and then written back as a PNG in.
#: Anything else — a palette, CMYK, 1-bit — is converted first: `resize` quietly
#: drops to nearest-neighbour on a palette image, which on a screenshot full of
#: text looks like damage.
_RESAMPLED_MODES = frozenset({"RGB", "RGBA", "L", "LA"})


def _picture_for(
    path: Path, displayed_width: int, settings: LayoutSettings
) -> OpenPyxlImage:
    """The copy of a screenshot that actually travels inside the workbook.

    openpyxl embeds the file as it found it and writes the display size beside
    it, so a 3840 px screenshot drawn 900 px wide still ships all 8.3 million
    of its pixels — and Excel decodes every one of them to draw those 900.
    A case full of 4K screenshots is a gigabyte of bitmap, and Excel does not
    say so: it draws 「この画像は表示できません」 over whichever pictures lost,
    a different set on each open, which is exactly how this was reported.

    So the copy that goes in is scaled to `embedded_image_scale` × the width it
    is drawn at, which cuts the memory by the square of that ratio while
    leaving something to zoom into. Nothing is written back to disk: the stored
    screenshot is still the untouched original (design.md §5), and this copy
    lives only as long as the save.

    An image already inside that width is passed through as its own file.
    Re-encoding it could only lose something.
    """
    limit = max(1, round(displayed_width * settings.embedded_image_scale))

    with PILImage.open(path) as original:
        if original.width <= limit:
            return OpenPyxlImage(str(path))

        width, height = scale_dimensions(original.width, original.height, limit)
        source = (
            original if original.mode in _RESAMPLED_MODES else original.convert("RGBA")
        )
        embedded = io.BytesIO()
        resized = source.resize((width, height), PILImage.Resampling.LANCZOS)
        resized.save(embedded, format="PNG")

    embedded.seek(0)
    return OpenPyxlImage(embedded)


def _reserve_rows_for_image(
    ws: Worksheet,
    first_row: int,
    count: int,
    settings: LayoutSettings,
) -> None:
    """Write the height of the rows an image is about to float over.

    The reservation is exact — `ceil(height / 20)` rows of 20 px is the image's
    own height, to the pixel, with nothing to spare — so it only holds while a
    row really is 20 px. Left to the default, one is not always: Excel reads
    `defaultRowHeight` as a suggestion when nothing marks it as custom and
    recomputes the standard height from the Normal font's metrics at the
    current display scaling. At 125% on Windows that comes out 14.4 pt rather
    than 15, every reserved row loses 4% of its height, and the bottom of the
    screenshot lands on top of whatever block came after it. macOS keeps 15 pt,
    which is why this only ever showed up on the work machine.

    Writing the height marks it `customHeight`, and Excel then honours it as
    given on either platform.
    """
    for offset in range(count):
        ws.row_dimensions[first_row + offset].height = settings.row_height_pt


def sanitize_filename(title: str) -> str:
    """Replace filesystem-illegal characters with underscores.

    Follows the convention: エビデンス_<title>.xlsx, where any of
    \\ / : * ? " < > | are replaced with _.
    """
    clean_title = ILLEGAL_FILENAME_CHARS.sub("_", title)
    return f"エビデンス_{clean_title}.xlsx"


def _text_cell(
    ws: Worksheet,
    row: int,
    column: int,
    value: str,
    settings: LayoutSettings = DEFAULT_LAYOUT_SETTINGS,
    bold: bool = False,
    color: str | None = None,
) -> Cell:
    """Write `value` into a cell as genuine, verbatim text.

    Two things openpyxl does regardless of `number_format`:

    - A string starting with `=` is read as a formula at assignment time
      (`data_type` becomes `'f'`), and `@` does nothing to stop it — `=1+1`
      would show as `2`, and anything Excel cannot parse as a formula (a log
      line starting `==>`, say) corrupts the file outright. `data_type` is
      forced back to `'s'` after assignment so the cell holds the string, not
      a formula.
    - Control characters (`\\x00`-`\\x08`, `\\x0b`-`\\x0c`, `\\x0e`-`\\x1f` —
      not `\\t \\n \\r`, which are legal) are illegal in OOXML and raise
      `IllegalCharacterError`. The DB dumps and terminal logs a case pastes in
      sometimes carry them (ANSI escapes, stray control bytes), so they are
      stripped rather than left to blow up the export.

    Every cell workutil writes goes through here for exactly this reason:
    `007` must stay `"007"`, and so must everything else, whatever shape it
    arrives in.
    """
    cleaned = ILLEGAL_CHARACTERS_RE.sub("", value)
    cell = ws.cell(row=row, column=column, value=cleaned)
    cell.data_type = "s"
    cell.number_format = "@"
    cell.font = Font(
        name=settings.font_name,
        size=settings.font_size,
        bold=bold,
        color=color,
    )
    return cell


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

    Raises `MissingImageFile` if an image block's file is not under
    `evidence_images_dir` — a partial workbook is not a deliverable.
    """
    wb = openpyxl.Workbook()
    wb.properties.title = evidence.title

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
                _text_cell(
                    ws,
                    current_row,
                    1,
                    block.label.strip(),
                    settings=settings,
                    bold=True,
                )
                current_row += 1

            if block.kind == BlockKind.TEXT:
                if block.split_lines:
                    lines = block.text.split("\n")
                    for line_idx, line in enumerate(lines):
                        _text_cell(
                            ws,
                            current_row + line_idx,
                            1,
                            line,
                            settings=settings,
                        )
                    current_row += len(lines)
                else:
                    text_cell = _text_cell(
                        ws, current_row, 1, block.text, settings=settings
                    )
                    text_cell.alignment = Alignment(wrap_text=True, vertical="top")
                    current_row += 1

            elif block.kind == BlockKind.IMAGE:
                img_path = evidence_images_dir / block.image_name
                if not img_path.is_file():
                    raise MissingImageFile(
                        f"用例「{case.name}」缺少图片文件：{block.image_name}"
                    )

                with PILImage.open(img_path) as pil_img:
                    orig_w, orig_h = pil_img.size

                scaled_w, scaled_h = scale_dimensions(
                    orig_w, orig_h, settings.max_image_width
                )
                reserved = calculate_reserved_rows(scaled_h, settings.row_height_px)

                xl_img = _picture_for(img_path, scaled_w, settings)
                xl_img.width = scaled_w
                xl_img.height = scaled_h
                ws.add_image(xl_img, f"A{current_row}")
                _reserve_rows_for_image(ws, current_row, reserved, settings)
                current_row += reserved

            elif block.kind == BlockKind.TABLE:
                for r_idx, row_cells in enumerate(block.rows):
                    row_num = current_row + r_idx
                    is_header = r_idx == 0 and block.has_header

                    for c_idx, cell_value in enumerate(row_cells):
                        col_num = c_idx + 1
                        str_val = str(cell_value)
                        color: str | None = None
                        if not is_header:
                            color = settings.literal_colors.get(str_val)

                        cell = _text_cell(
                            ws,
                            row_num,
                            col_num,
                            str_val,
                            settings=settings,
                            bold=is_header,
                            color=color,
                        )
                        cell.border = thin_border
                        if is_header:
                            cell.fill = header_fill
                            cell.alignment = Alignment(
                                wrap_text=True, vertical="center"
                            )

                current_row += len(block.rows)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
