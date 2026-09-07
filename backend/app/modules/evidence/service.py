"""What you can do with an Evidence and its Cases. Knows nothing about HTTP."""

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import images
from app.core.db import utc_now
from app.modules.evidence.models import Evidence, EvidenceCase

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


class CaseMove(StrEnum):
    """Where a case is being sent. Not a drag: just the four buttons.

    Up and down are the everyday correction; top and bottom exist because
    walking a case up eight places one click at a time is not reordering, it is
    clicking (design.md §6 F5).
    """

    UP = "up"
    DOWN = "down"
    TOP = "top"
    BOTTOM = "bottom"


class EvidenceNotFound(LookupError):
    """No evidence has that id."""


class CaseNotFound(LookupError):
    """No case has that id — or it belongs to a different evidence."""


# The messages below are shown to the author verbatim, under the field they
# just typed in, which is why they are in the language the UI speaks. Nothing
# else in the backend is: these are the only ones a person reads.
class InvalidTitle(ValueError):
    """An evidence with no title has no name for its file."""


class InvalidCaseName(ValueError):
    """A case name Excel could not carry as a sheet name."""


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


def delete_case(session: Session, evidence_id: int, case_id: int) -> None:
    """Drop a case, closing the gap it leaves in the order.

    Renumbering rather than leaving a hole keeps `order` meaning "which sheet",
    so nothing downstream has to reason about gaps.
    """
    case = get_case(session, evidence_id, case_id)
    session.delete(case)
    session.flush()
    _renumber(_cases_in_order(session, evidence_id))
    session.commit()


def move_case(
    session: Session, evidence_id: int, case_id: int, to: CaseMove
) -> list[EvidenceCase]:
    """Move a case among its siblings and hand back the whole new order.

    The whole list, because that is what the tab bar redraws — and because a
    move that hit an end changed nothing, which the caller should not have to
    work out from the request it sent.
    """
    case = get_case(session, evidence_id, case_id)
    cases = _cases_in_order(session, evidence_id)

    was = cases.index(case)
    now = {
        CaseMove.UP: was - 1,
        CaseMove.DOWN: was + 1,
        CaseMove.TOP: 0,
        CaseMove.BOTTOM: len(cases) - 1,
    }[to]
    if not 0 <= now < len(cases):
        return cases

    cases.insert(now, cases.pop(was))
    _renumber(cases)
    session.commit()
    return cases


def _renumber(cases: Sequence[EvidenceCase]) -> None:
    for position, case in enumerate(cases):
        case.order = position
