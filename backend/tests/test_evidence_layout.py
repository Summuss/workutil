"""Unit tests for pure layout functions.

Tested in isolation from openpyxl and the database: image scaling, row
reservation, and filename sanitisation are pure calculations with clear
boundaries (design.md §6 F5, Testing Decisions).
"""

from app.modules.evidence.layout import (
    LayoutSettings,
    calculate_reserved_rows,
    sanitize_filename,
    scale_dimensions,
)


def test_scale_dimensions_leaves_small_and_exact_images_untouched() -> None:
    # Exactly max width
    assert scale_dimensions(900, 500, max_width=900) == (900, 500)
    # Narrower than max width: never scaled up
    assert scale_dimensions(600, 400, max_width=900) == (600, 400)


def test_scale_dimensions_scales_wide_images_proportionally() -> None:
    # 2:1 aspect ratio
    assert scale_dimensions(1800, 900, max_width=900) == (900, 450)
    # 16:9 4K
    assert scale_dimensions(3840, 2160, max_width=900) == (900, 506)


def test_scale_dimensions_handles_tall_images() -> None:
    # Tall portrait narrower than max width stays original size
    assert scale_dimensions(800, 1080, max_width=900) == (800, 1080)
    # Tall portrait wider than max width scales down proportionally
    assert scale_dimensions(1200, 2400, max_width=900) == (900, 1800)


def test_scale_dimensions_handles_tiny_images() -> None:
    # 1x1 pixel
    assert scale_dimensions(1, 1, max_width=900) == (1, 1)
    # Small snippet
    assert scale_dimensions(32, 16, max_width=900) == (32, 16)
    # Very wide 1px strip still keeps at least 1px height
    assert scale_dimensions(3000, 1, max_width=900) == (900, 1)


def test_calculate_reserved_rows_by_height() -> None:
    # Zero (or negative) height is unreachable via the real pipeline — PIL
    # never reports a non-positive size for a file that opened at all — but
    # placing an image always claims at least one row, never zero, so a
    # degenerate input can't produce an overlap either.
    assert calculate_reserved_rows(0, row_height_px=20) == 1
    assert calculate_reserved_rows(-5, row_height_px=20) == 1
    # Exactly one row
    assert calculate_reserved_rows(20, row_height_px=20) == 1
    # 1 px over one row requires 2 rows
    assert calculate_reserved_rows(21, row_height_px=20) == 2
    # Excel max row height limit is 545px at 96 DPI
    assert calculate_reserved_rows(545, row_height_px=20) == 28
    # 1080p full height screenshot requires 54 rows
    assert calculate_reserved_rows(1080, row_height_px=20) == 54


def test_sanitize_filename_replaces_illegal_characters() -> None:
    # Plain ascii and japanese
    assert sanitize_filename("受注一覧") == "エビデンス_受注一覧.xlsx"
    # All illegal characters: \ / : * ? " < > |
    raw = r'a\b/c:d*e?f"g<h>i|j'
    expected = "エビデンス_a_b_c_d_e_f_g_h_i_j.xlsx"
    assert sanitize_filename(raw) == expected


def test_layout_settings_has_expected_defaults() -> None:
    settings = LayoutSettings()
    assert settings.column_width == 18.0
    assert settings.max_image_width == 900
    assert settings.embedded_image_scale == 2.0
    assert settings.row_height_px == 20
    assert settings.header_fill_color == "87E7AD"
    assert settings.border_style == "thin"
    assert settings.font_name == "游ゴシック"
    assert settings.font_size == 11
    assert settings.literal_colors == {"\u226a NULL \u226b": "808080"}
