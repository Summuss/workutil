"""What you can do with an Evidence and its Cases. Knows nothing about HTTP."""

import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import images
from app.core.db import utc_now
from app.core.images import IncomingImage
from app.core.ordering import Move as Move
from app.core.ordering import renumber as _renumber
from app.core.ordering import reorder as _reordered
from app.modules.evidence import tables
from app.modules.evidence.layout import (
    DEFAULT_LAYOUT_SETTINGS,
    LayoutSettings,
    build_evidence_workbook,
    sanitize_filename,
)
from app.modules.evidence.models import (
    BlockKind,
    Evidence,
    EvidenceBlock,
    EvidenceCase,
)

#: The list shows the recent past, not the whole archive — there is no paging
#: and, deliberately, no search: ADR-0001 gives "find it again by searching" to
#: Memo. Same shape as memo's `RECENT_MEMO_LIMIT`.
RECENT_EVIDENCE_LIMIT = 200

#: Excel's own limit on a sheet name. openpyxl does *not* enforce it — it emits
#: a `UserWarning` and writes the over-long name into the file anyway (measured
#: on 3.1.5) — so this is the only place the length is caught.
SHEET_NAME_MAX_LENGTH = 31

#: Characters Excel refuses in a sheet name. openpyxl does raise on these, but
#: only at export, by which point the author has already typed them into a
#: dozen cases (design.md §6 F5 Excel 导出).
ILLEGAL_SHEET_NAME_CHARACTERS = frozenset(":\\/?*[]")


class EvidenceNotFound(LookupError):
    """No evidence has that id."""

    code = "evidence.not_found"


class CaseNotFound(LookupError):
    """No case has that id — or it belongs to a different evidence."""

    code = "evidence.case_not_found"


# The messages below are shown to the author verbatim, under the field they
# just typed in, which is why they are in the language the UI speaks. Nothing
# else in the backend is: these are the only ones a person reads.
class InvalidTitle(ValueError):
    """An evidence with no title has no name for its file."""

    code = "evidence.invalid_title"


class InvalidCaseName(ValueError):
    """A case name Excel could not carry as a sheet name."""

    code = "evidence.invalid_case_name"


class BlockNotFound(LookupError):
    """No block has that id — or it belongs to a different case."""

    code = "evidence.block_not_found"


class CellNotFound(LookupError):
    """No such row or column in this table."""

    code = "evidence.cell_not_found"


class EmptyBlockText(ValueError):
    """A text block with nothing in it."""

    code = "evidence.empty_block_text"


class EmptyTable(ValueError):
    """The last row or column of a table, which would leave nothing."""

    code = "evidence.empty_table"


class WrongBlockKind(ValueError):
    """This block does not carry the payload the edit is for."""

    code = "evidence.wrong_block_kind"


class EmptyEvidence(ValueError):
    """An evidence with no cases cannot be exported."""

    code = "evidence.empty_evidence"


class EvidenceListing(NamedTuple):
    """An evidence as the list shows it: the row, plus how many cases it has."""

    evidence: Evidence
    case_count: int


class OpenEvidence(NamedTuple):
    """An evidence with its cases, in the order they will become sheets."""

    evidence: Evidence
    cases: list[EvidenceCase]


def evidence_images_dir(images_dir: Path, evidence_id: int) -> Path:
    """Where one evidence's screenshots live — the only place that decides this.

    Under a literal `evidence/` beside the memo directories, which are named by
    a decimal id and so can never collide with it. That is what lets Evidence
    move in without migrating what is already on disk (design.md §5).
    """
    return images_dir / "evidence" / str(evidence_id)


def evidence_images_url(evidence_id: int) -> str:
    """What a saved screenshot is called from outside — the other half of the
    pair above. Both have to agree with the route in `router.py`, so neither is
    spelled out twice."""
    return f"/api/evidence/{evidence_id}/images"


def _clean_title(title: str) -> str:
    text = title.strip()
    if not text:
        raise InvalidTitle("请给这份 Evidence 起个名字")
    return text


def validate_case_name(name: str) -> str:
    """The typed case name, or a refusal — this *is* the sheet name.

    Checked here rather than cleaned at export on purpose: the sheet name is
    part of what gets delivered, and quietly renaming a sheet hands someone a
    file its author never checked (spec Excel 导出).
    """
    text = name.strip()
    if not text:
        raise InvalidCaseName("用例编号不能为空")
    if len(text) > SHEET_NAME_MAX_LENGTH:
        raise InvalidCaseName(
            f"用例编号最多 {SHEET_NAME_MAX_LENGTH} 个字符,现在是 {len(text)} 个"
        )
    illegal = sorted(ILLEGAL_SHEET_NAME_CHARACTERS.intersection(text))
    if illegal:
        raise InvalidCaseName(f"用例编号不能包含 {' '.join(illegal)}")
    return text


def create_evidence(
    session: Session, title: str, images_dir: Path | None = None
) -> Evidence:
    now = utc_now()
    evidence = Evidence(title=_clean_title(title), created_at=now, updated_at=now)
    session.add(evidence)
    session.flush()

    if images_dir is not None:
        # SQLite hands out the id of an evidence that was rolled back or
        # deleted, so a directory can already be sitting here. Whatever left it
        # behind, it is not this one's: a new evidence has no screenshots.
        images.discard(evidence_images_dir(images_dir, evidence.id))

    session.commit()
    return evidence


def list_evidence(session: Session) -> list[EvidenceListing]:
    """The evidence to show, newest first, with each one's case count.

    Ordered by creation and never by last change, so renaming an old workbook
    does not drag it to the top. Ties break on id, so the order never wobbles
    between calls.
    """
    rows = session.execute(
        select(Evidence, func.count(EvidenceCase.id))
        .outerjoin(EvidenceCase, EvidenceCase.evidence_id == Evidence.id)
        .group_by(Evidence.id)
        .order_by(Evidence.created_at.desc(), Evidence.id.desc())
        .limit(RECENT_EVIDENCE_LIMIT)
    ).all()
    return [EvidenceListing(evidence, count) for evidence, count in rows]


def get_evidence(session: Session, evidence_id: int) -> Evidence:
    evidence = session.get(Evidence, evidence_id)
    if evidence is None:
        raise EvidenceNotFound(f"evidence {evidence_id} not found")
    return evidence


def rename_evidence(session: Session, evidence_id: int, title: str) -> Evidence:
    """Give an evidence a new title, recording when it changed.

    Only `updated_at` moves; `created_at` is what the list sorts on.
    """
    text = _clean_title(title)
    evidence = get_evidence(session, evidence_id)
    evidence.title = text
    evidence.updated_at = utc_now()
    session.commit()
    return evidence


def delete_evidence(
    session: Session, evidence_id: int, images_dir: Path | None = None
) -> None:
    """Delete an evidence, its cases, and the screenshots that belonged to it.

    A delivered workbook's screenshots are of no further use, and Evidence's
    references to them are structured rather than parsed out of prose, so there
    is no half-cut state to protect — this is the deliberate exception to
    memo's no-reference-counting rule (design.md §5). Files that will not go
    are not a failure: the evidence is already gone.
    """
    evidence = get_evidence(session, evidence_id)
    session.delete(evidence)
    session.commit()

    if images_dir is not None:
        images.discard(evidence_images_dir(images_dir, evidence_id))


def _cases_in_order(session: Session, evidence_id: int) -> list[EvidenceCase]:
    return list(
        session.scalars(
            select(EvidenceCase)
            .where(EvidenceCase.evidence_id == evidence_id)
            .order_by(EvidenceCase.order, EvidenceCase.id)
        ).all()
    )


def open_evidence(session: Session, evidence_id: int) -> OpenEvidence:
    """One evidence and its cases — everything the detail page opens on.

    One call rather than two, so the evidence is looked up (and its absence
    reported) exactly once.
    """
    evidence = get_evidence(session, evidence_id)
    return OpenEvidence(evidence, _cases_in_order(session, evidence_id))


def export_evidence(
    session: Session,
    evidence_id: int,
    images_dir: Path,
    settings: LayoutSettings = DEFAULT_LAYOUT_SETTINGS,
) -> tuple[str, bytes]:
    """Export an evidence as an Excel workbook.

    Returns (filename, bytes).
    Refuses with EmptyEvidence if there are 0 cases (design.md §6 F5).
    """
    evidence = get_evidence(session, evidence_id)
    cases = _cases_in_order(session, evidence_id)
    if not cases:
        raise EmptyEvidence("Evidence 没有任何用例，无法导出")

    cases_with_blocks: list[tuple[EvidenceCase, list[EvidenceBlock]]] = [
        (case, _blocks_in_order(session, case.id)) for case in cases
    ]

    filename = sanitize_filename(evidence.title)
    dir_for_evidence = evidence_images_dir(images_dir, evidence_id)
    content = build_evidence_workbook(
        evidence, cases_with_blocks, dir_for_evidence, settings
    )
    return filename, content


def count_cases(session: Session, evidence_id: int) -> int:
    """How many cases this evidence has, without loading any of them."""
    return (
        session.scalar(
            select(func.count())
            .select_from(EvidenceCase)
            .where(EvidenceCase.evidence_id == evidence_id)
        )
        or 0
    )


def get_case(session: Session, evidence_id: int, case_id: int) -> EvidenceCase:
    """One case of this evidence.

    A case id belonging to a different evidence is not found here, rather than
    quietly reachable through the wrong URL.
    """
    case = session.get(EvidenceCase, case_id)
    if case is None or case.evidence_id != evidence_id:
        raise CaseNotFound(f"case {case_id} not found in evidence {evidence_id}")
    return case


def _refuse_duplicate_name(
    session: Session, evidence_id: int, name: str, except_case_id: int | None = None
) -> None:
    """A workbook cannot hold two sheets whose names differ only in case.

    openpyxl will not stop it either, and here it does not even warn: measured
    on 3.1.5, adding `ABC` beside an existing `abc` silently writes `ABC1`. A
    sheet renamed behind the author's back is the exact thing checking on the
    way in exists to prevent, so the comparison folds case.

    Compared in Python rather than in SQL: SQLite's `NOCASE` folds ASCII only,
    and a case number can be `ケース1`.
    """
    folded = name.casefold()
    for sibling in _cases_in_order(session, evidence_id):
        if sibling.id != except_case_id and sibling.name.casefold() == folded:
            raise InvalidCaseName(f"这份 Evidence 里已经有用例 {sibling.name} 了")


def add_case(session: Session, evidence_id: int, name: str) -> EvidenceCase:
    """Append a case to an evidence, at the end of the existing ones."""
    text = validate_case_name(name)
    get_evidence(session, evidence_id)
    _refuse_duplicate_name(session, evidence_id, text)

    existing = _cases_in_order(session, evidence_id)
    case = EvidenceCase(evidence_id=evidence_id, name=text, order=len(existing))
    session.add(case)
    session.commit()
    return case


def rename_case(
    session: Session, evidence_id: int, case_id: int, name: str
) -> EvidenceCase:
    text = validate_case_name(name)
    case = get_case(session, evidence_id, case_id)
    _refuse_duplicate_name(session, evidence_id, text, except_case_id=case.id)

    case.name = text
    session.commit()
    return case


def _duplicate_image_file(directory: Path, original_name: str) -> str:
    original_path = directory / original_name
    if not original_path.is_file():
        return original_name

    taken = {path.name for path in directory.iterdir() if path.is_file()}
    suffix = Path(original_name).suffix.lower()
    if suffix not in images.IMAGE_EXTENSIONS:
        suffix = ".png"
    index = 1
    while f"img_{index}{suffix}" in taken:
        index += 1
    new_name = f"img_{index}{suffix}"
    shutil.copy2(original_path, directory / new_name)
    return new_name


def _generate_duplicate_case_name(
    session: Session, evidence_id: int, original_name: str
) -> str:
    existing_folded = {
        sibling.name.casefold() for sibling in _cases_in_order(session, evidence_id)
    }
    n = 2
    while True:
        suffix = f" ({n})"
        max_base_len = SHEET_NAME_MAX_LENGTH - len(suffix)
        base = (
            original_name[:max_base_len]
            if len(original_name) > max_base_len
            else original_name
        )
        candidate = f"{base}{suffix}"
        if candidate.casefold() not in existing_folded:
            return validate_case_name(candidate)
        n += 1


def duplicate_case(
    session: Session,
    evidence_id: int,
    case_id: int,
    images_dir: Path | None = None,
) -> tuple[list[EvidenceCase], int]:
    """Duplicate a case with all its blocks, files, and renumbered ordering.

    Inserts the duplicate immediately following the original case,
    renumbering all following cases so order remains strictly contiguous.
    Returns the whole cases list and the new case's id.
    """
    case = get_case(session, evidence_id, case_id)
    new_name = _generate_duplicate_case_name(session, evidence_id, case.name)

    existing_cases = _cases_in_order(session, evidence_id)
    orig_idx = next(i for i, c in enumerate(existing_cases) if c.id == case.id)

    new_case = EvidenceCase(
        evidence_id=evidence_id,
        name=new_name,
        order=orig_idx + 1,
    )
    session.add(new_case)
    session.flush()

    existing_cases.insert(orig_idx + 1, new_case)
    _renumber(existing_cases)
    session.flush()

    img_dir = (
        evidence_images_dir(images_dir, evidence_id) if images_dir is not None else None
    )
    orig_blocks = _blocks_in_order(session, case.id)
    for block in orig_blocks:
        new_image_name = ""
        if block.kind is BlockKind.IMAGE and block.image_name:
            if img_dir is not None:
                new_image_name = _duplicate_image_file(img_dir, block.image_name)
            else:
                new_image_name = f"copy_{block.image_name}"

        new_rows = [list(row) for row in block.rows] if block.rows else []

        new_block = EvidenceBlock(
            case_id=new_case.id,
            kind=block.kind,
            label=block.label,
            text=block.text,
            image_name=new_image_name,
            rows=new_rows,
            has_header=block.has_header,
            table_source=block.table_source,
            order=block.order,
        )
        session.add(new_block)

    session.commit()
    return _cases_in_order(session, evidence_id), new_case.id


def delete_case(
    session: Session, evidence_id: int, case_id: int, images_dir: Path | None = None
) -> None:
    """Drop a case, its blocks, and the screenshots those blocks were.

    Renumbering rather than leaving a hole keeps `order` meaning "which sheet",
    so nothing downstream has to reason about gaps.

    The files go one by one rather than by directory: every case of an evidence
    keeps its screenshots in the same one, so removing it would take the other
    cases' with it.
    """
    case = get_case(session, evidence_id, case_id)
    doomed = _image_names(_blocks_in_order(session, case.id))

    session.delete(case)
    session.flush()
    _renumber(_cases_in_order(session, evidence_id))
    session.commit()

    _discard_images(images_dir, evidence_id, doomed)


def move_case(
    session: Session, evidence_id: int, case_id: int, to: Move | int
) -> list[EvidenceCase]:
    """Move a case among its siblings and hand back the whole new order.

    The whole list, because that is what the tab bar redraws — and because a
    move that hit an end changed nothing, which the caller should not have to
    work out from the request it sent.
    """
    case = get_case(session, evidence_id, case_id)
    cases = _reordered(_cases_in_order(session, evidence_id), case, to)
    session.commit()
    return cases


# --- Blocks -----------------------------------------------------------------
#
# The bottom layer: what is actually inside a case. Labelling, ordering,
# finding and deleting a block are the same for all three kinds — only the
# payload each carries, and the way it is edited, differ.


class CaseContent(NamedTuple):
    """One case and what is in it, in the order it will be written down."""

    case: EvidenceCase
    blocks: list[EvidenceBlock]


def _clean_block_text(text: str) -> str:
    """The text as it was pasted, minus the blank edges a paste brings.

    Blank lines at either end go, whether they are empty or only look it, and
    so does trailing space. The indent of the first line that has something on
    it stays: a plain `strip()` would take that indent off line one alone and
    leave every line under it hanging, and a log is a text block rather than a
    kind of its own (design.md §6 F5).
    """
    lines = text.rstrip().splitlines()
    while lines and not lines[0].strip():
        del lines[0]
    if not lines:
        raise EmptyBlockText("这一段是空的 —— 不要的话删掉它")
    return "\n".join(lines)


def _clean_label(label: str | None) -> str | None:
    """A small heading, or nothing at all.

    Blank and absent are the same thing: an empty label would export as a blank
    line above the block, which is not what clearing a heading means.
    """
    text = (label or "").strip()
    return text or None


def _blocks_in_order(session: Session, case_id: int) -> list[EvidenceBlock]:
    return list(
        session.scalars(
            select(EvidenceBlock)
            .where(EvidenceBlock.case_id == case_id)
            .order_by(EvidenceBlock.order, EvidenceBlock.id)
        ).all()
    )


def open_case(session: Session, evidence_id: int, case_id: int) -> CaseContent:
    """One case with its blocks — what the content area shows.

    Read a case at a time rather than with the whole evidence: only the open
    case is on screen, and a workbook's other cases can be carrying every
    screenshot of a day's verification.
    """
    case = get_case(session, evidence_id, case_id)
    return CaseContent(case, _blocks_in_order(session, case.id))


def get_block(
    session: Session, evidence_id: int, case_id: int, block_id: int
) -> EvidenceBlock:
    """One block of this case of this evidence.

    Both halves of the path are checked, so a block is never reachable through
    another case's URL — the same rule `get_case` holds one level up.
    """
    case = get_case(session, evidence_id, case_id)
    block = session.get(EvidenceBlock, block_id)
    if block is None or block.case_id != case.id:
        raise BlockNotFound(f"block {block_id} not found in case {case_id}")
    return block


def add_text_block(
    session: Session,
    evidence_id: int,
    case_id: int,
    text: str,
    label: str | None = None,
) -> EvidenceBlock:
    """Append a paragraph of text to a case, after what is already there."""
    # The case is found first: a request naming one that is not there is a 404
    # whatever its payload turns out to say.
    case = get_case(session, evidence_id, case_id)
    content = _clean_block_text(text)

    block = EvidenceBlock(
        case_id=case.id,
        kind=BlockKind.TEXT,
        text=content,
        label=_clean_label(label),
        order=len(_blocks_in_order(session, case.id)),
    )
    session.add(block)
    session.commit()
    return block


def add_image_block(
    session: Session,
    evidence_id: int,
    case_id: int,
    images_dir: Path,
    image: IncomingImage,
    label: str | None = None,
) -> EvidenceBlock:
    """Append one pasted screenshot to a case, after what is already there.

    One block holds one image; a paste of three arrives as three of these, in
    the order they were pasted (design.md §6 F5). The file is written before
    the row exists, so a screenshot that will not decode is refused with
    nothing saved — the reverse would leave a block pointing at no file.
    """
    case = get_case(session, evidence_id, case_id)
    (name,) = images.save(evidence_images_dir(images_dir, evidence_id), [image])

    block = EvidenceBlock(
        case_id=case.id,
        kind=BlockKind.IMAGE,
        image_name=name,
        label=_clean_label(label),
        order=len(_blocks_in_order(session, case.id)),
    )
    session.add(block)
    session.commit()
    return block


def add_table_block(
    session: Session,
    evidence_id: int,
    case_id: int,
    rows: list[list[str]],
    source: str,
    label: str | None = None,
) -> EvidenceBlock:
    """Append a query result to a case, keeping its rows and columns.

    `has_header` starts true because it has to start somewhere and cannot be
    worked out: whether a DB client copies the column names is a setting inside
    that client (design.md §6 F5). It is one click to flip.

    `source` is the paste these rows were cut from, kept so that a wrong guess
    can be taken back whole — see `turn_block_into_text`.
    """
    case = get_case(session, evidence_id, case_id)

    block = EvidenceBlock(
        case_id=case.id,
        kind=BlockKind.TABLE,
        rows=rows,
        has_header=True,
        table_source=source,
        label=_clean_label(label),
        order=len(_blocks_in_order(session, case.id)),
    )
    session.add(block)
    session.commit()
    return block


def add_pasted_block(
    session: Session,
    evidence_id: int,
    case_id: int,
    text: str,
    html: str | None = None,
    label: str | None = None,
) -> EvidenceBlock:
    """Append whatever was on the clipboard, as whichever kind it turns out be.

    The one place the kind of a pasted block is decided. Screenshots do not
    come through here — the browser knows an image when it holds one — so what
    is left is the guess between a query result and a paragraph, and that guess
    belongs on this side of the wire with the parsing (design.md §6 F5).

    A paste with nothing in it is refused before the guess rather than after:
    text that is only tabs and newlines is technically a table of empty cells,
    and an empty block of either kind is a block to delete, not to make.
    """
    if not text.strip():
        raise EmptyBlockText("剪贴板里什么都没有")

    rows = tables.table_in(text, html)
    if rows is None:
        return add_text_block(session, evidence_id, case_id, text, label)
    return add_table_block(session, evidence_id, case_id, rows, text, label)


def _image_names(blocks: Sequence[EvidenceBlock]) -> list[str]:
    """The files these blocks are, ignoring the ones that are not images.

    Asked of `kind` and not of whether `image_name` happens to be filled: which
    payload a block carries is what its kind means, and the table kind lands in
    the same fork in ticket 06.
    """
    return [block.image_name for block in blocks if block.kind is BlockKind.IMAGE]


def _discard_images(
    images_dir: Path | None, evidence_id: int, names: Sequence[str]
) -> None:
    """Throw away named screenshots of one evidence, tolerating a locked file.

    Deleting is done after the rows are committed and never reported: on
    Windows a screenshot held open by a viewer cannot be unlinked, and the
    block it belonged to is already gone, so an error would be a lie (spec 图片).

    A caller with no images directory — a test driving the service alone — asks
    for nothing here rather than guarding at each call.
    """
    if images_dir is None:
        return

    directory = evidence_images_dir(images_dir, evidence_id)
    for name in names:
        images.discard_file(directory / name)


def set_block_text(
    session: Session, evidence_id: int, case_id: int, block_id: int, text: str
) -> EvidenceBlock:
    """Rewrite what a text block says.

    Text is the payload of one kind. Image and table blocks carry their own,
    edited their own way, and neither comes through here.
    """
    block = get_block(session, evidence_id, case_id, block_id)
    if block.kind is not BlockKind.TEXT:
        raise WrongBlockKind("这一段不是文字,改不了它的正文")

    block.text = _clean_block_text(text)
    session.commit()
    return block


def set_block_label(
    session: Session,
    evidence_id: int,
    case_id: int,
    block_id: int,
    label: str | None,
) -> EvidenceBlock:
    """Give a block its small heading, or take it away.

    Unlike the payload, this belongs to every kind: it is what tells the reader
    of the delivered sheet which part of the case they are looking at.
    """
    block = get_block(session, evidence_id, case_id, block_id)
    block.label = _clean_label(label)
    session.commit()
    return block


def delete_block(
    session: Session,
    evidence_id: int,
    case_id: int,
    block_id: int,
    images_dir: Path | None = None,
) -> None:
    """Drop a block, closing the gap it leaves in the order.

    An image block *is* one screenshot, so dropping it takes the file: there is
    no half-cut state in which the reference is temporarily gone, which is what
    stops memo from doing the same (design.md §5).
    """
    block = get_block(session, evidence_id, case_id, block_id)
    doomed = _image_names([block])

    session.delete(block)
    session.flush()
    _renumber(_blocks_in_order(session, case_id))
    session.commit()

    _discard_images(images_dir, evidence_id, doomed)


# --- Inside a table ---------------------------------------------------------
#
# What can be done to a query result once it is in a case: mask a cell, take
# out a column that should not be delivered, say whether the first row is
# column names.
#
# What cannot be done, anywhere in this codebase, is add a row or a column. The
# rows came out of a database; a tool that can add one is a tool that can put a
# value into an evidence that no system ever produced, which is the one thing an
# evidence must not be able to say (spec Out of Scope). This is the only place
# that reason is written down — everywhere else the absence is what says it.
#
# The cutting itself is in `tables.py`, as values in and values out. Each of
# these assigns the new list it gets back rather than changing the one that is
# there: SQLAlchemy tracks a JSON column by identity, so a cell changed in
# place is a change it cannot see and would never write down.


def _table_block(
    session: Session, evidence_id: int, case_id: int, block_id: int
) -> EvidenceBlock:
    """One table of this case — or a refusal, if that block is another kind."""
    block = get_block(session, evidence_id, case_id, block_id)
    if block.kind is not BlockKind.TABLE:
        raise WrongBlockKind("这一段不是表格")
    return block


def _refuse_missing(at: int, count: int) -> None:
    """Stop here unless there really is a row or a column at `at`.

    A path carries whatever number was put in it, negative ones included, and
    Python would happily read `rows[-1]` as the last row rather than as the
    mistake it is.
    """
    if not 0 <= at < count:
        raise CellNotFound(f"no row or column {at} in a table of {count}")


def set_table_cell(
    session: Session,
    evidence_id: int,
    case_id: int,
    block_id: int,
    row: int,
    column: int,
    value: str,
) -> EvidenceBlock:
    """Rewrite one cell — masking what should not be delivered, mostly.

    Stored exactly as typed, spaces and all: an evidence says what was seen.
    """
    block = _table_block(session, evidence_id, case_id, block_id)
    _refuse_missing(row, len(block.rows))
    _refuse_missing(column, len(block.rows[row]))

    block.rows = tables.with_cell(block.rows, row, column, value)
    session.commit()
    return block


def delete_table_row(
    session: Session, evidence_id: int, case_id: int, block_id: int, row: int
) -> EvidenceBlock:
    """Take one row out, header row included.

    `has_header` says how to draw the first row, not which row is pinned down:
    dropping the header leaves the row below it as the new first row, which is
    what deleting a header of column names you did not want should do.
    """
    block = _table_block(session, evidence_id, case_id, block_id)
    _refuse_missing(row, len(block.rows))
    if len(block.rows) <= 1:
        raise EmptyTable("表格不能一行都不剩 —— 整段不要的话删掉它")

    block.rows = tables.without_row(block.rows, row)
    session.commit()
    return block


def delete_table_column(
    session: Session, evidence_id: int, case_id: int, block_id: int, column: int
) -> EvidenceBlock:
    """Take one column out of every row at once.

    The everyday reason a table is edited at all: a result set carries columns
    nobody outside the team should see, and they go from the whole table or
    they have not gone.
    """
    block = _table_block(session, evidence_id, case_id, block_id)
    _refuse_missing(column, len(block.rows[0]))
    if len(block.rows[0]) <= 1:
        raise EmptyTable("表格不能一列都不剩 —— 整段不要的话删掉它")

    block.rows = tables.without_column(block.rows, column)
    session.commit()
    return block


def set_table_header(
    session: Session, evidence_id: int, case_id: int, block_id: int, has_header: bool
) -> EvidenceBlock:
    """Say whether the first row is column names.

    Set rather than toggled, so saying it twice says the same thing — and so
    the answer does not depend on what the screen believed when it asked.
    """
    block = _table_block(session, evidence_id, case_id, block_id)
    block.has_header = has_header
    session.commit()
    return block


def turn_block_into_text(
    session: Session, evidence_id: int, case_id: int, block_id: int
) -> EvidenceBlock:
    """Take back a wrong guess: this was never a table, it was a log.

    The paste comes back exactly as it arrived, because that is what was kept
    for this (`EvidenceBlock.table_source`) — rebuilding it out of the cells
    could not, since unquoting is not something that runs backwards.

    The block stays the same block: its heading and its place among the others
    were not part of the mistake.
    """
    block = _table_block(session, evidence_id, case_id, block_id)

    block.kind = BlockKind.TEXT
    block.text = _clean_block_text(block.table_source)
    block.table_source = ""
    block.has_header = False
    block.rows = []
    session.commit()
    return block


def move_block(
    session: Session, evidence_id: int, case_id: int, block_id: int, to: Move | int
) -> list[EvidenceBlock]:
    """Move a block among the others and hand back the whole new order.

    Reordering here is nearly always a nudge — blocks are appended as the work
    happens — with top and bottom for the screenshot that was taken last and
    belongs first.
    """
    block = get_block(session, evidence_id, case_id, block_id)
    blocks = _reordered(_blocks_in_order(session, case_id), block, to)
    session.commit()
    return blocks
