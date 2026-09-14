"""What a table Block promises: a query result that kept its shape.

The HTTP boundary is the agreed test seam (design.md §6 F5 测试接缝), and this
is the one place it earns its keep twice over: parsing a clipboard is the
biggest pure function in the module — quotes, cells holding a tab or a
newline, CRLF, ragged rows, a trailing blank line — and putting it behind HTTP
is what lets it be tested at all without writing automated tests for the
frontend (spec 表格).

Recognising a table is a guess and will sometimes be wrong, so the other half
of what is pinned down here is the way back: a log that was read as a table
becomes text again with nothing lost.

What a table deliberately cannot do is grow. There is no way to add a row or a
column, because the data came out of a database and a hand-typed row in an
evidence is a fabricated one (spec Out of Scope).
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.evidence.models import EvidenceBlock

from .conftest import workutil_at
from .test_evidence_api import add_case, new_evidence
from .test_evidence_block_api import blocks_of

#: What a DB client puts on the clipboard: a header line and two rows, tab
#: separated, ending in a newline.
QUERY_RESULT = "id\tcode\tname\n1\t007\t山田\n2\t042\t佐藤\n"


def paste(
    client: TestClient,
    evidence_id: int,
    case_id: int,
    text: str,
    html: str | None = None,
    label: str | None = None,
) -> Any:
    """Hand the server what was on the clipboard and let it decide what it is.

    The one door a paste comes through: which kind of block it becomes is the
    server's to work out, so a test asserts on what came back rather than on
    what it asked for.
    """
    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "paste", "text": text, "html": html, "label": label},
    )
    assert created.status_code == 201, created.text
    return created.json()


def rows_of(client: TestClient, evidence_id: int, case_id: int, block_id: int) -> Any:
    (block,) = [
        one for one in blocks_of(client, evidence_id, case_id) if one["id"] == block_id
    ]
    return block["rows"]


def block_at(client: TestClient, evidence_id: int, case_id: int, block_id: int) -> Any:
    (block,) = [
        one for one in blocks_of(client, evidence_id, case_id) if one["id"] == block_id
    ]
    return block


@pytest.fixture
def case(client: TestClient) -> tuple[int, int]:
    """One evidence with one case in it — where a paste lands."""
    evidence_id = new_evidence(client)
    return evidence_id, add_case(client, evidence_id, "1")


@pytest.fixture
def table(client: TestClient, case: tuple[int, int]) -> tuple[int, int, int]:
    """A case holding one recognised table — evidence, case, block."""
    evidence_id, case_id = case
    block = paste(client, evidence_id, case_id, QUERY_RESULT)
    assert block["kind"] == "table"
    return evidence_id, case_id, block["id"]


# --- Recognising a paste ----------------------------------------------------


def test_a_pasted_query_result_becomes_a_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, QUERY_RESULT)

    assert block["kind"] == "table"
    assert block["rows"] == [
        ["id", "code", "name"],
        ["1", "007", "山田"],
        ["2", "042", "佐藤"],
    ]


def test_a_recognised_table_is_read_back_with_its_rows(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    evidence_id, case_id, block_id = table

    assert rows_of(client, evidence_id, case_id, block_id) == [
        ["id", "code", "name"],
        ["1", "007", "山田"],
        ["2", "042", "佐藤"],
    ]


def test_a_paste_with_no_tabs_is_text(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "検索ボタンを押した\n件数は 3 件")

    assert block["kind"] == "text"
    assert block["text"] == "検索ボタンを押した\n件数は 3 件"


def test_a_single_line_is_not_a_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    """One line of tabs, stopping where it does, is a line — 多行 (design.md §6 F5).

    No line ending: the selection ended mid-line, which is what text dragged
    out of an indented log looks like and what a copied row never does. It
    still parses; what it does not do is become a table.
    """
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "id\tcode\tname")

    assert block["kind"] == "text"
    assert block["text"] == "id\tcode\tname"


def test_a_single_row_copied_off_a_grid_is_a_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    """A result set of one record is still a result set.

    What separates it from the line above is where the copy stops: a grid hands
    over whole lines, terminator included, so this one ends in a newline. Under
    the old flat 多行 rule the one-row result was the single case the whole
    feature could not see.
    """
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "1\t007\t山田\n")

    assert block["kind"] == "table"
    assert block["rows"] == [["1", "007", "山田"]]


def test_a_one_row_table_does_not_start_as_all_header(
    client: TestClient, case: tuple[int, int]
) -> None:
    """`has_header` off, and not as a guess: there is nothing under it.

    True would draw the whole block as a bold, green-filled header row with no
    data beneath — which was the objection to reading one row as a table.
    """
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "1\t007\t山田\n")

    assert block["has_header"] is False


def test_a_multi_row_table_still_starts_with_a_header(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, QUERY_RESULT)

    assert block["has_header"] is True


def test_several_plain_lines_are_not_a_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    """含制表符 is doing real work, not restating the rest of the rule.

    Without it, any paste of several lines is a run of one-column rows, all the
    same width — 多行 and 各行列数一致 both satisfied — and every log in the
    world becomes a table.
    """
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "一行目\n二行目\n三行目")

    assert block["kind"] == "text"
    assert block["text"] == "一行目\n二行目\n三行目"


def test_rows_of_different_widths_are_not_a_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Ragged is the giveaway that this was never a result set.

    And the content survives whole: what is refused is the shape, not the
    paste.
    """
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "a\tb\tc\nd\te\n")

    assert block["kind"] == "text"
    assert block["text"] == "a\tb\tc\nd\te"


def test_an_empty_paste_is_refused(client: TestClient, case: tuple[int, int]) -> None:
    evidence_id, case_id = case

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "paste", "text": "   \n  \n"},
    )

    assert refused.status_code == 422
    assert blocks_of(client, evidence_id, case_id) == []


def test_a_pasted_table_can_be_given_a_label(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(
        client, evidence_id, case_id, QUERY_RESULT, label="事前準備の DB データ"
    )

    assert block["kind"] == "table"
    assert block["label"] == "事前準備の DB データ"


# --- The parsing boundaries -------------------------------------------------
#
# The matrix design.md §6 F5 put behind HTTP on purpose. Every case here is one
# a real DB client produces.


def test_carriage_returns_do_not_become_cells(
    client: TestClient, case: tuple[int, int]
) -> None:
    """A clipboard filled on Windows ends its lines with CRLF."""
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "id\tname\r\n1\t山田\r\n")

    assert block["rows"] == [["id", "name"], ["1", "山田"]]


def test_a_quoted_cell_arrives_without_its_quotes(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, 'id\tname\n1\t"山田 太郎"\n')

    assert block["rows"] == [["id", "name"], ["1", "山田 太郎"]]


def test_a_doubled_quote_inside_a_cell_becomes_one(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, 'id\tnote\n1\t"say ""hi"""\n')

    assert block["rows"] == [["id", "note"], ["1", 'say "hi"']]


def test_a_quote_in_the_middle_of_a_cell_is_just_a_quote(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Only a quote that opens a cell quotes it; anywhere else it is a value."""
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, 'id\tnote\n1\t12"inch\n')

    assert block["rows"] == [["id", "note"], ["1", '12"inch']]


def test_a_cell_holding_a_tab_stays_one_cell(
    client: TestClient, case: tuple[int, int]
) -> None:
    """The reason rows are settled at paste time (design.md §6 F5).

    A text column in a database can hold a tab. Once this text is stored as
    text and cut up later, that cell is two cells and every row below is one
    column wider than the header.
    """
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, 'id\tnote\n1\t"a\tb"\n')

    assert block["rows"] == [["id", "note"], ["1", "a\tb"]]


def test_a_cell_holding_a_newline_stays_one_cell(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, 'id\tnote\n1\t"first\nsecond"\n')

    assert block["rows"] == [["id", "note"], ["1", "first\nsecond"]]


def test_a_newline_inside_a_cell_is_not_left_as_crlf(
    client: TestClient, case: tuple[int, int]
) -> None:
    """One line ending inside a value, whichever platform the paste came from."""
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, 'id\tnote\r\n1\t"first\r\nsecond"\r\n')

    assert block["rows"] == [["id", "note"], ["1", "first\nsecond"]]


def test_a_trailing_blank_line_does_not_add_a_row(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "id\tname\n1\t山田\n\n")

    assert block["rows"] == [["id", "name"], ["1", "山田"]]


def test_an_empty_last_cell_is_still_a_cell(
    client: TestClient, case: tuple[int, int]
) -> None:
    """A NULL in the last column leaves a line ending in a tab.

    Trimming the paste's trailing whitespace before cutting it up would eat
    that cell and make every such result set ragged.
    """
    evidence_id, case_id = case

    block = paste(client, evidence_id, case_id, "id\tname\n1\t\n")

    assert block["kind"] == "table"
    assert block["rows"] == [["id", "name"], ["1", ""]]


# --- Compatibility with text/html -------------------------------------------


def test_a_table_copied_as_html_is_recognised(
    client: TestClient, case: tuple[int, int]
) -> None:
    """The compatibility path: a table copied out of a web page or Excel.

    Its `text/plain` is the rendered text and carries no tabs, so the main path
    finds nothing — see design.md §6 F5.
    """
    evidence_id, case_id = case

    block = paste(
        client,
        evidence_id,
        case_id,
        "id name\n1 山田",
        html="<table><tr><th>id</th><th>name</th></tr>"
        "<tr><td>1</td><td>山田</td></tr></table>",
    )

    assert block["kind"] == "table"
    assert block["rows"] == [["id", "name"], ["1", "山田"]]


def test_html_entities_come_back_as_characters(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(
        client,
        evidence_id,
        case_id,
        "a b",
        html="<table><tr><td>a &amp; b</td><td>&lt;x&gt;</td></tr>"
        "<tr><td>c</td><td>d</td></tr></table>",
    )

    assert block["rows"] == [["a & b", "<x>"], ["c", "d"]]


def test_the_markup_excel_actually_writes_is_read(
    client: TestClient, case: tuple[int, int]
) -> None:
    """The compatibility path against a real payload, not a tidy one.

    What Excel puts on the clipboard is a style block, a `<col>`, and every
    cell wrapped in attributes and a `<font>`. It is also the reason a paste is
    asked about tables before it is asked about images: Excel offers a PNG of
    the same cells, and answering "image" first turns a spreadsheet into a
    screenshot (design.md §6 F5).
    """
    evidence_id, case_id = case

    block = paste(
        client,
        evidence_id,
        case_id,
        "id code",
        html=(
            '<html xmlns:x="urn:schemas-microsoft-com:office:excel">'
            '<head><style>.xl65 {mso-number-format:"\\@";}</style></head><body>'
            "<!--StartFragment-->"
            "<table border=0 cellspacing=0 style='border-collapse:collapse'>"
            "<col width=64 span=2>"
            "<tr height=20 style='height:15.0pt'>"
            '<td height=20 class=xl65><font face="Calibri">id</font></td>'
            "<td class=xl65>name&nbsp;</td></tr>"
            "<tr height=20><td class=xl65>1</td>"
            "<td class=xl65>山田&amp;佐藤</td></tr>"
            "</table><!--EndFragment--></body></html>"
        ),
    )

    assert block["kind"] == "table"
    assert block["rows"] == [["id", "name"], ["1", "山田&佐藤"]]


def test_tabs_win_over_html(client: TestClient, case: tuple[int, int]) -> None:
    """TSV is the main path; `text/html` is what it falls back to (spec 表格)."""
    evidence_id, case_id = case

    block = paste(
        client,
        evidence_id,
        case_id,
        QUERY_RESULT,
        html="<table><tr><td>wrong</td><td>wrong</td></tr>"
        "<tr><td>wrong</td><td>wrong</td></tr></table>",
    )

    assert block["rows"][0] == ["id", "code", "name"]


def test_a_fragment_that_starts_inside_a_table_is_read(
    client: TestClient, case: tuple[int, int]
) -> None:
    """What Windows actually hands over, which is not always a whole table.

    The clipboard's HTML flavour there is CF_HTML: a fragment marked inside a
    larger document, and Chrome hands over the fragment alone. Excel's marker
    sits after the `<table>` tag, and selecting part of a table on a web page
    starts inside one too — so the markup arrives as bare rows, with no table
    element anywhere in it. Nothing on macOS looks like this, which is why it
    only ever showed up on the work machine.
    """
    evidence_id, case_id = case

    block = paste(
        client,
        evidence_id,
        case_id,
        "id name\n1 山田\n",
        html=(
            "<col width=64 span=2>"
            "<tr height=20><td>id</td><td>name</td></tr>"
            "<tr height=20><td>1</td><td>山田</td></tr>"
        ),
    )

    assert block["kind"] == "table"
    assert block["rows"] == [["id", "name"], ["1", "山田"]]


def test_the_data_table_wins_over_the_layout_table_around_it(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Nested tables: the inner one is the data, the outer one is a page.

    Reading only the outermost would give a single cell holding the whole inner
    table — one row, and not a table at all.
    """
    evidence_id, case_id = case

    block = paste(
        client,
        evidence_id,
        case_id,
        "id name\n1 山田\n",
        html=(
            "<table><tr><td>"
            "<table><tr><th>id</th><th>name</th></tr>"
            "<tr><td>1</td><td>山田</td></tr></table>"
            "</td></tr></table>"
        ),
    )

    assert block["kind"] == "table"
    assert block["rows"] == [["id", "name"], ["1", "山田"]]


def test_one_row_of_markup_is_a_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Markup needs no row count: `<table>` says outright what tabs suggest."""
    evidence_id, case_id = case

    block = paste(
        client,
        evidence_id,
        case_id,
        "1 山田",
        html="<table><tr><td>1</td><td>山田</td></tr></table>",
    )

    assert block["kind"] == "table"
    assert block["rows"] == [["1", "山田"]]


def test_html_that_holds_no_table_is_ignored(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case

    block = paste(
        client, evidence_id, case_id, "just words", html="<p>just <b>words</b></p>"
    )

    assert block["kind"] == "text"
    assert block["text"] == "just words"


# --- Getting it wrong, and getting back -------------------------------------


def test_an_indented_log_read_as_a_table_becomes_text_with_nothing_lost(
    client: TestClient, case: tuple[int, int]
) -> None:
    """The guard on the whole guess (spec 粘贴时的类型判别).

    A log indented with tabs has every mark of a table — several lines, tabs,
    the same count on each — and it is not one. The way back has to hand the
    paste over exactly as it arrived, or the one click that fixes a wrong guess
    costs more than the guess saved.
    """
    evidence_id, case_id = case
    log = "\tat Foo.bar(Foo.java:31)\n\tat Baz.qux(Baz.java:12)"

    block = paste(client, evidence_id, case_id, log)
    assert block["kind"] == "table"

    corrected = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/as-text"
    )

    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["kind"] == "text"
    assert corrected.json()["text"] == log
    assert block_at(client, evidence_id, case_id, block["id"])["text"] == log


def test_correcting_a_guess_keeps_the_block_where_it_was(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Correcting the kind is not re-pasting: the label and the place stay."""
    evidence_id, case_id = case
    first = paste(client, evidence_id, case_id, "先に書いた一段")
    block = paste(client, evidence_id, case_id, QUERY_RESULT, label="ログ")
    paste(client, evidence_id, case_id, "後に書いた一段")

    corrected = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/as-text"
    )

    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["id"] == block["id"]
    assert corrected.json()["label"] == "ログ"
    listed = blocks_of(client, evidence_id, case_id)
    assert [one["id"] for one in listed[:2]] == [first["id"], block["id"]]
    assert [one["order"] for one in listed] == [0, 1, 2]


def test_a_corrected_table_keeps_no_rows(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    evidence_id, case_id, block_id = table

    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-text"
    )

    assert rows_of(client, evidence_id, case_id, block_id) == []


def test_only_a_table_can_be_corrected(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Text is already text, and as-text requires a table."""
    evidence_id, case_id = case
    block = paste(client, evidence_id, case_id, "ただの文字")

    refused = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/as-text"
    )

    assert refused.status_code == 422


# --- Turning text into table (two-way) --------------------------------------


def test_a_corrected_table_can_be_turned_back_into_a_table(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """A table turned into text can be turned back into a table without loss."""
    evidence_id, case_id, block_id = table
    original_rows = rows_of(client, evidence_id, case_id, block_id)

    # 1. Turn to text
    text_res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-text"
    )
    assert text_res.status_code == 200
    assert text_res.json()["kind"] == "text"

    # 2. Turn back to table
    table_res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-table"
    )
    assert table_res.status_code == 200
    assert table_res.json()["kind"] == "table"
    assert table_res.json()["rows"] == original_rows
    assert table_res.json()["has_header"] is True


def test_a_tsv_log_never_recognised_can_be_turned_into_a_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    """A TSV text block created as text can be turned into a table."""
    evidence_id, case_id = case
    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": "col1\tcol2\nval1\tval2\n"},
    )
    assert created.status_code == 201
    block_id = created.json()["id"]

    res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-table"
    )
    assert res.status_code == 200
    assert res.json()["kind"] == "table"
    assert res.json()["rows"] == [["col1", "col2"], ["val1", "val2"]]
    assert res.json()["has_header"] is True


def test_turning_into_table_cuts_the_current_text_after_edit(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """Editing the text block before turning back cuts the edited text."""
    evidence_id, case_id, block_id = table
    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-text"
    )
    edited_text = "newA\tnewB\n100\t200\n"
    client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}",
        json={"text": edited_text},
    )

    res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-table"
    )
    assert res.status_code == 200
    assert res.json()["kind"] == "table"
    assert res.json()["rows"] == [["newA", "newB"], ["100", "200"]]


def test_turning_into_table_keeps_label_and_order(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    first = paste(client, evidence_id, case_id, "先に書いた一段")
    block = paste(client, evidence_id, case_id, QUERY_RESULT, label="ログ")
    paste(client, evidence_id, case_id, "後に書いた一段")

    client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/as-text"
    )
    res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/as-table"
    )
    assert res.status_code == 200
    assert res.json()["id"] == block["id"]
    assert res.json()["label"] == "ログ"

    listed = blocks_of(client, evidence_id, case_id)
    assert [one["id"] for one in listed[:2]] == [first["id"], block["id"]]
    assert [one["order"] for one in listed] == [0, 1, 2]


def test_single_row_table_has_header_false(
    client: TestClient, case: tuple[int, int], session: Session
) -> None:
    evidence_id, case_id = case
    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": "only_one\trow"},
    )
    block_id = created.json()["id"]

    # Pre-condition: arrange the text with a trailing newline, which is the
    # marker that tells table_in that a single row is a complete row (design.md §6 F5).
    db_block = session.get(EvidenceBlock, block_id)
    assert db_block is not None
    db_block.text = "only_one\trow\n"
    session.commit()

    res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-table"
    )
    assert res.status_code == 200
    assert res.json()["kind"] == "table"
    assert res.json()["rows"] == [["only_one", "row"]]
    assert res.json()["has_header"] is False


def test_text_that_cannot_be_parsed_as_table_is_refused(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    created = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={"kind": "text", "text": "foo\tbar"},
    )
    block_id = created.json()["id"]

    res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-table"
    )
    assert res.status_code == 422
    assert res.json()["code"] == "evidence.cannot_turn_into_table"

    block = block_at(client, evidence_id, case_id, block_id)
    assert block["kind"] == "text"
    assert block["text"] == "foo\tbar"


def test_only_text_block_can_be_turned_into_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    table_block = paste(client, evidence_id, case_id, QUERY_RESULT)
    res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{table_block['id']}/as-table"
    )
    assert res.status_code == 422
    assert res.json()["code"] == "evidence.wrong_block_kind"


def test_image_block_cannot_be_turned_into_table(
    client: TestClient, case: tuple[int, int]
) -> None:
    from .conftest import SAMPLE_PNG, data_url

    evidence_id, case_id = case
    img_block = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks",
        json={
            "kind": "image",
            "image": {"data": data_url(SAMPLE_PNG), "filename": "test.png"},
        },
    ).json()

    res = client.post(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{img_block['id']}/as-table"
    )
    assert res.status_code == 422
    assert res.json()["code"] == "evidence.wrong_block_kind"


def test_turning_back_and_forth_five_times_does_not_degrade_content(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    evidence_id, case_id, block_id = table
    original_rows = rows_of(client, evidence_id, case_id, block_id)

    for _ in range(5):
        to_text = client.post(
            f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-text"
        )
        assert to_text.status_code == 200
        assert to_text.json()["kind"] == "text"

        to_table = client.post(
            f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-table"
        )
        assert to_table.status_code == 200
        assert to_table.json()["kind"] == "table"
        assert to_table.json()["rows"] == original_rows


# --- The header row ---------------------------------------------------------


def test_a_recognised_table_starts_with_a_header(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """Default `true`, because it cannot be worked out (design.md §6 F5).

    Whether a DB client copies the column names depends on a setting in that
    client, and nothing in the paste says which way it was set.
    """
    evidence_id, case_id, block_id = table

    assert block_at(client, evidence_id, case_id, block_id)["has_header"] is True


def test_the_header_can_be_turned_off_and_on_again(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    evidence_id, case_id, block_id = table
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/header"

    off = client.put(at, json={"has_header": False})

    assert off.status_code == 200, off.text
    assert off.json()["has_header"] is False
    assert block_at(client, evidence_id, case_id, block_id)["has_header"] is False

    on = client.put(at, json={"has_header": True})

    assert on.json()["has_header"] is True


def test_turning_the_header_off_keeps_every_row(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """The flag says how to draw the first row, not whether to keep it."""
    evidence_id, case_id, block_id = table

    client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/header",
        json={"has_header": False},
    )

    assert rows_of(client, evidence_id, case_id, block_id)[0] == ["id", "code", "name"]


def test_only_a_table_has_a_header(client: TestClient, case: tuple[int, int]) -> None:
    evidence_id, case_id = case
    block = paste(client, evidence_id, case_id, "ただの文字")

    refused = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/header",
        json={"has_header": True},
    )

    assert refused.status_code == 422


# --- Editing a cell ---------------------------------------------------------


def test_a_cell_can_be_changed(client: TestClient, table: tuple[int, int, int]) -> None:
    """Masking a value that should not be delivered (spec User Stories 16)."""
    evidence_id, case_id, block_id = table

    edited = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/cells/1/2",
        json={"value": "＊＊＊"},
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["rows"][1] == ["1", "007", "＊＊＊"]
    assert rows_of(client, evidence_id, case_id, block_id)[2] == ["2", "042", "佐藤"]


def test_a_cell_can_be_emptied(client: TestClient, table: tuple[int, int, int]) -> None:
    evidence_id, case_id, block_id = table

    edited = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/cells/1/1",
        json={"value": ""},
    )

    assert edited.json()["rows"][1] == ["1", "", "山田"]


def test_a_cell_is_stored_exactly_as_typed(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """No trimming: an evidence says what was seen, spaces and all."""
    evidence_id, case_id, block_id = table

    edited = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/cells/1/1",
        json={"value": "  007  "},
    )

    assert edited.json()["rows"][1][1] == "  007  "


def test_a_cell_outside_the_table_is_not_found(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    evidence_id, case_id, block_id = table
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/cells"

    assert client.put(f"{at}/9/0", json={"value": "x"}).status_code == 404
    assert client.put(f"{at}/0/9", json={"value": "x"}).status_code == 404


def test_only_a_table_has_cells(client: TestClient, case: tuple[int, int]) -> None:
    evidence_id, case_id = case
    block = paste(client, evidence_id, case_id, "ただの文字")

    refused = client.put(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/cells/0/0",
        json={"value": "x"},
    )

    assert refused.status_code == 422


# --- Taking rows and columns out --------------------------------------------


def test_a_row_can_be_deleted(client: TestClient, table: tuple[int, int, int]) -> None:
    evidence_id, case_id, block_id = table

    deleted = client.delete(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/rows/1"
    )

    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["rows"] == [["id", "code", "name"], ["2", "042", "佐藤"]]
    assert rows_of(client, evidence_id, case_id, block_id) == [
        ["id", "code", "name"],
        ["2", "042", "佐藤"],
    ]


def test_a_column_can_be_deleted(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """A column that should not be delivered goes from every row at once."""
    evidence_id, case_id, block_id = table

    deleted = client.delete(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/columns/1"
    )

    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["rows"] == [["id", "name"], ["1", "山田"], ["2", "佐藤"]]


def test_the_header_row_can_be_deleted_like_any_other(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """The flag draws the first row; it does not pin it down."""
    evidence_id, case_id, block_id = table

    deleted = client.delete(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}/rows/0"
    )

    assert deleted.json()["rows"] == [["1", "007", "山田"], ["2", "042", "佐藤"]]
    assert deleted.json()["has_header"] is True


def test_a_row_outside_the_table_is_not_found(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    evidence_id, case_id, block_id = table
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}"

    assert client.delete(f"{at}/rows/9").status_code == 404
    assert client.delete(f"{at}/columns/9").status_code == 404


def test_the_last_row_cannot_be_deleted(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """A table with nothing in it is not a table — delete the block instead.

    The same rule a text block lives by: emptying it is refused, because "I do
    not want this" is spelled by deleting it (design.md §6 F5).
    """
    evidence_id, case_id, block_id = table
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}"

    assert client.delete(f"{at}/rows/0").status_code == 200
    assert client.delete(f"{at}/rows/0").status_code == 200
    refused = client.delete(f"{at}/rows/0")

    assert refused.status_code == 422
    assert len(rows_of(client, evidence_id, case_id, block_id)) == 1


def test_the_last_column_cannot_be_deleted(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    evidence_id, case_id, block_id = table
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}"

    assert client.delete(f"{at}/columns/0").status_code == 200
    assert client.delete(f"{at}/columns/0").status_code == 200
    refused = client.delete(f"{at}/columns/0")

    assert refused.status_code == 422
    assert rows_of(client, evidence_id, case_id, block_id)[0] == ["name"]


def test_only_a_table_has_rows_to_take_out(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    block = paste(client, evidence_id, case_id, "ただの文字")
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}"

    assert client.delete(f"{at}/rows/0").status_code == 422
    assert client.delete(f"{at}/columns/0").status_code == 422


# --- What a table cannot do -------------------------------------------------


def test_there_is_no_way_to_add_a_row_or_a_column(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """Deliberately absent, not forgotten (spec Out of Scope).

    The rows came out of a database. A tool that can add one is a tool that can
    put a value into an evidence that no system ever produced.
    """
    evidence_id, case_id, block_id = table
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}"

    added_row = client.post(f"{at}/rows", json={"row": ["3", "099", "鈴木"]})
    added_column = client.post(f"{at}/columns", json={"name": "extra"})

    assert added_row.status_code in (404, 405)
    assert added_column.status_code in (404, 405)
    assert rows_of(client, evidence_id, case_id, block_id) == [
        ["id", "code", "name"],
        ["1", "007", "山田"],
        ["2", "042", "佐藤"],
    ]


def test_the_text_of_a_table_cannot_be_rewritten(
    client: TestClient, table: tuple[int, int, int]
) -> None:
    """Each kind is edited its own way — text is not this one's payload."""
    evidence_id, case_id, block_id = table

    refused = client.patch(
        f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block_id}",
        json={"text": "書き換え"},
    )

    assert refused.status_code == 422


# --- A table among the other kinds ------------------------------------------


def test_a_table_can_be_labelled_moved_and_deleted(
    client: TestClient, case: tuple[int, int]
) -> None:
    """Everything a block is, a table is too — only the payload differs."""
    evidence_id, case_id = case
    first = paste(client, evidence_id, case_id, "一段目")
    block = paste(client, evidence_id, case_id, QUERY_RESULT)
    at = f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}"

    labelled = client.put(f"{at}/label", json={"label": "DB 更新後の結果"})
    assert labelled.status_code == 200, labelled.text
    assert labelled.json()["label"] == "DB 更新後の結果"

    moved = client.post(f"{at}/move", json={"to": "top"})
    assert moved.status_code == 200, moved.text
    assert [one["id"] for one in moved.json()] == [block["id"], first["id"]]

    assert client.delete(at).status_code == 204
    assert [one["id"] for one in blocks_of(client, evidence_id, case_id)] == [
        first["id"]
    ]


def test_a_table_cannot_be_reached_through_another_case(
    client: TestClient, case: tuple[int, int]
) -> None:
    evidence_id, case_id = case
    other_case_id = add_case(client, evidence_id, "2")
    block = paste(client, evidence_id, case_id, QUERY_RESULT)

    wrong = client.put(
        f"/api/evidence/{evidence_id}/cases/{other_case_id}"
        f"/blocks/{block['id']}/header",
        json={"has_header": False},
    )

    assert wrong.status_code == 404


def test_a_table_survives_a_restart(data_dir: Path) -> None:
    """Rows are stored, not re-cut from the paste every time it is read."""
    with workutil_at(data_dir) as client:
        evidence_id = new_evidence(client)
        case_id = add_case(client, evidence_id, "1")
        block = paste(client, evidence_id, case_id, QUERY_RESULT)
        client.put(
            f"/api/evidence/{evidence_id}/cases/{case_id}/blocks/{block['id']}/header",
            json={"has_header": False},
        )

    with workutil_at(data_dir) as client:
        reopened = block_at(client, evidence_id, case_id, block["id"])

    assert reopened["kind"] == "table"
    assert reopened["has_header"] is False
    assert reopened["rows"] == [
        ["id", "code", "name"],
        ["1", "007", "山田"],
        ["2", "042", "佐藤"],
    ]
