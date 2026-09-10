"""Reading a clipboard: is this a query result, and where are its cells?

The largest pure function in the module, and the reason it is on this side of
the wire at all. Cutting a paste into cells is all boundaries — quotes, a cell
holding a tab or a newline, CRLF, rows of different widths, a trailing blank
line — and behind HTTP every one of them is reachable from the agreed test seam
without having to write automated tests for the frontend (design.md §6 F5). The
server listens on `127.0.0.1`, so the round trip a paste costs is not a cost.

TSV is the main path and `text/html` is compatibility: the IDEA database tool
puts only `text/plain` on the clipboard, formatted by whichever data extractor
the result set is set to (the DSV family defaults to tab separated). An HTML
flavour turns up when the copy came from a web page or Excel.

Below the reading is the other half: what can be done to those cells afterwards
— a cell rewritten, a row or a column taken out. Same kind of thing, kept in
the same place: values in, values out.

Nothing here touches the database or knows what a Block is. Which paste becomes
a table, which block an edit lands on, and what a caller is allowed to do at
all, are all `service.py`'s.
"""

import csv
import io
from html.parser import HTMLParser

#: 多行, from the rule in design.md §6 F5 — what a paste of *bare* tab
#: separated text has to clear. One line of tabs, with nothing after it, is a
#: line: a fragment selected out of the middle of an indented log looks exactly
#: like it.
#:
#: A row that came out of a grid does not look like that, and `table_in` says
#: where the difference is: the copy carries the line ending too. Markup does
#: not need the rule at all — `<table>` says outright what tabs only suggest.
MIN_ROWS = 2


def rows_of_tsv(text: str) -> list[list[str]]:
    """Cut tab-separated text into cells, the way the tool that wrote it meant.

    Quoting is the whole reason this is not `text.split("\\t")`: it is what
    lets a value hold a tab or a newline, and those are exactly the values that
    would otherwise silently push every cell after them one place along.

    `newline=""` hands the line endings to the reader rather than to the
    stream, which is what makes a CRLF paste and a quoted cell containing a
    line break both come out right.
    """
    rows = list(
        csv.reader(io.StringIO(text, newline=""), delimiter="\t", quotechar='"')
    )
    return [[_one_line_ending(cell) for cell in row] for row in _trimmed(rows)]


def _one_line_ending(cell: str) -> str:
    """A cell's own line breaks, in one flavour.

    A value holding a newline arrives carrying whichever line ending the
    machine that copied it uses, and a stray `\\r` in the middle of a cell is
    not something anybody meant to deliver.
    """
    return cell.replace("\r\n", "\n").replace("\r", "\n")


def _trimmed(rows: list[list[str]]) -> list[list[str]]:
    """The rows, without the blank lines a paste picks up at either end.

    Only a genuinely empty line goes — a row of empty *cells* is a row of
    values that happen to be NULL, and dropping it would be dropping data. A
    blank line in the middle stays for the same reason it should: nothing that
    came out of a result set has one, and leaving it in is what makes the row
    widths disagree and the guess below come out "not a table".
    """
    start, end = 0, len(rows)
    while start < end and not rows[start]:
        start += 1
    while end > start and not rows[end - 1]:
        end -= 1
    return rows[start:end]


class _OpenTable:
    """One table being read: the rows so far, and the row and cell still open."""

    __slots__ = ("rows", "row", "cell")

    def __init__(self) -> None:
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None


class _TableReader(HTMLParser):
    """Every table in a fragment of HTML, each as rows of cell text.

    Deliberately small: this is the compatibility path, reading markup that a
    browser or Excel just wrote, not the open web. Cell text is gathered as it
    arrives and entities are already decoded by `HTMLParser`; `<br>` inside a
    cell is the one tag that means something here, because it is a line break
    in a value.

    Two things it has to survive, both of them everyday and both of them
    invisible from a fragment written out by hand:

    - **A fragment that starts inside a table.** On Windows the clipboard's
      HTML flavour is CF_HTML, which marks a *fragment* inside a larger
      document, and Chrome hands over only that fragment. Excel puts the
      marker after the `<table>` tag, and selecting part of a table on a web
      page puts it after one too — so what arrives is a run of bare `<tr>`s
      with no table around them. A row opening with no table open opens one.
    - **A table nested in another.** Layout tables are a habit the web has not
      lost, and the data is the inner one. Each `<table>` is read on its own,
      innermost first, and `table_in` takes the first that is rectangular —
      rather than the outer one, whose only row would be the whole inner table
      squashed into a cell.
    """

    CELLS = frozenset({"td", "th"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._open: list[_OpenTable] = []

    def close(self) -> None:
        """Finish, taking whatever a truncated fragment left half-open."""
        super().close()
        while self._open:
            self._close_table()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._open.append(_OpenTable())
        elif tag == "tr":
            table = self._open_table()
            # A `</tr>` is allowed to be missing, and in generated markup
            # sometimes is; the next `<tr>` ends the one before it.
            self._close_row(table)
            table.row = []
        elif tag in self.CELLS:
            table = self._open_table()
            self._close_cell(table)
            if table.row is None:
                table.row = []
            table.cell = []
        elif tag == "br" and self._open:
            cell = self._open[-1].cell
            if cell is not None:
                cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self._open:
            return
        table = self._open[-1]
        if tag in self.CELLS:
            self._close_cell(table)
        elif tag == "tr":
            self._close_row(table)
        elif tag == "table":
            self._close_table()

    def handle_data(self, data: str) -> None:
        if self._open and self._open[-1].cell is not None:
            self._open[-1].cell.append(data)

    def _open_table(self) -> _OpenTable:
        """The table these rows belong to, opening one if the markup did not."""
        if not self._open:
            self._open.append(_OpenTable())
        return self._open[-1]

    def _close_cell(self, table: _OpenTable) -> None:
        if table.cell is not None and table.row is not None:
            table.row.append("".join(table.cell).strip())
        table.cell = None

    def _close_row(self, table: _OpenTable) -> None:
        self._close_cell(table)
        if table.row:
            table.rows.append(table.row)
        table.row = None

    def _close_table(self) -> None:
        table = self._open.pop()
        self._close_row(table)
        if table.rows:
            self.tables.append(table.rows)


def tables_of_html(html: str) -> list[list[list[str]]]:
    """Every table in this markup, innermost and earliest first."""
    reader = _TableReader()
    reader.feed(html)
    reader.close()
    return reader.tables


def is_a_table(rows: list[list[str]], min_rows: int = MIN_ROWS) -> bool:
    """Enough rows, all the same width — 多行 and 各行列数一致 (design.md §6 F5).

    Half of the rule; the other half is 含制表符, which is asked of the text
    rather than of these rows and so lives in `table_in`. `min_rows` is how
    much of the first half a given flavour has to earn — see `table_in`, which
    is the only place that decides. Both together will still get it wrong: an
    indented log has every one of the three (see the tests), which is why what
    is built on top of this hangs a correction beside the block it made rather
    than trusting the answer.
    """
    if len(rows) < min_rows:
        return False
    width = len(rows[0])
    return all(len(row) == width for row in rows)


def _rows_needed_of(text: str) -> int:
    """How many rows this paste has to have before it can be a table.

    One, when the text ends the way a copied row ends. A grid hands over whole
    lines, terminator included, so a single record copied out of one arrives as
    `a\tb\tc\n` — a table of one row, and refusing it means the one-row
    result set is the one case the whole feature does not cover.

    Two otherwise, which is what keeps that from swallowing everything: text
    dragged out of the middle of a line stops where the selection did. So a
    tab-indented log line picked out by hand is still a line, and only a paste
    that looks like it came off the end of a row gets the benefit.
    """
    return 1 if text.endswith(("\n", "\r")) else MIN_ROWS


def table_in(text: str, html: str | None = None) -> list[list[str]] | None:
    """The table on this clipboard, or `None` if there is not one.

    含制表符 is checked here, against the text as it arrived, and it is doing
    real work rather than restating the cutting below: without it every paste
    of several plain lines is a run of rows one column wide, all the same
    width, and every log in the world becomes a table.

    Tabs first and markup second: the tool this is for puts only `text/plain`
    on the clipboard, and when both flavours are there — a copy out of Excel —
    the tab-separated one is the one that came from a grid. HTML gets its turn
    only when the main path found nothing, which is what a copy from a web page
    looks like: rendered text with no tabs in it, beside real markup.

    Markup needs no row count at all: a `<table>` says outright what the tabs
    only suggest, so one row of it is a table. It can hold more than one, and
    the first rectangular one wins — innermost first, because when tables nest
    the data is the inner one and the outer is a page's layout.
    """
    if "\t" in text:
        rows = rows_of_tsv(text)
        if is_a_table(rows, _rows_needed_of(text)):
            return rows

    if html:
        for rows in tables_of_html(html):
            if is_a_table(rows, min_rows=1):
                return rows

    return None


# --- Changing what was cut ---------------------------------------------------
#
# Everything a table can have done to it once it is in a case, as plain values:
# a cell rewritten, a row or a column taken out. Each answers with a new
# list-of-lists rather than changing the one it was given — partly because a
# fresh list is the only kind of change SQLAlchemy can see in a JSON column,
# and partly because that is what makes these worth having here, away from the
# session and the block.
#
# There is deliberately no counterpart that adds one: see `service.py`, where
# the reason belongs.


def with_cell(
    rows: list[list[str]], row: int, column: int, value: str
) -> list[list[str]]:
    """These rows with one cell holding `value` instead — exactly as given."""
    changed = [list(cells) for cells in rows]
    changed[row][column] = value
    return changed


def without_row(rows: list[list[str]], row: int) -> list[list[str]]:
    """These rows, minus one of them."""
    return [list(cells) for where, cells in enumerate(rows) if where != row]


def without_column(rows: list[list[str]], column: int) -> list[list[str]]:
    """These rows, each minus the same column — a column goes from all of them
    at once or it has not gone."""
    return [
        [cell for where, cell in enumerate(cells) if where != column] for cells in rows
    ]
