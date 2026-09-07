"""What you can do with memos. Knows nothing about HTTP."""

from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import images
from app.core.db import utc_now
from app.core.images import ImageUpload
from app.modules.memo.models import Memo
from app.modules.memo.snippets import extract_snippets

#: The list shows the recent past, not the whole archive — there is no paging,
#: so this is what "the list" means (spec 前端). Search answers from the same
#: window, so a query can never return more rows than browsing does.
RECENT_MEMO_LIMIT = 200


class EmptyMemo(ValueError):
    """A memo with nothing in it is not a memo."""


class MemoNotFound(LookupError):
    """No memo has that id."""


class MemoListing(NamedTuple):
    """A memo as the list shows it: the memo, plus what is said about it."""

    memo: Memo
    image_count: int
    snippets: list[str]
    snippet_total: int


def memo_images_dir(images_dir: Path, memo_id: int) -> Path:
    """Where one memo's screenshots live — the only place that decides this.

    Memo directories are named by a decimal id and nothing else, which is what
    lets Evidence sit beside them under a literal `evidence/` without a
    migration (design.md §5).
    """
    return images_dir / str(memo_id)


def _memo_images_url(memo_id: int) -> str:
    """What a saved screenshot is called from inside a memo body.

    The other half of the pair above: `core.images` writes the file, this says
    how the body points back at it. They have to agree with the route in
    `router.py`, so neither is spelled out twice.
    """
    return f"/api/memos/{memo_id}/images"


def count_images(images_dir: Path, memo_id: int) -> int:
    """Number of image files this memo has on disk."""
    return images.count(memo_images_dir(images_dir, memo_id))


def create_memo(
    session: Session,
    body: str,
    images_dir: Path | None = None,
    uploads: Sequence[ImageUpload] = (),
) -> Memo:
    text = body.strip()
    if not text:
        raise EmptyMemo("a memo needs a body")

    now = utc_now()
    memo = Memo(body=text, created_at=now, updated_at=now)
    session.add(memo)
    session.flush()

    if images_dir is not None:
        memo_dir = memo_images_dir(images_dir, memo.id)
        # SQLite hands out the id of a memo that was rolled back or deleted, so
        # a directory can already be sitting here. Whatever left it, it is not
        # this memo's: a memo being created has never had an image.
        images.discard(memo_dir)
        memo.body = images.save_and_link(
            memo_dir, _memo_images_url(memo.id), memo.body, uploads
        )

    session.commit()
    return memo


def _recent(session: Session) -> Sequence[Memo]:
    return session.scalars(
        select(Memo)
        .order_by(Memo.created_at.desc(), Memo.id.desc())
        .limit(RECENT_MEMO_LIMIT)
    ).all()


def _matching(session: Session, query: str) -> Sequence[Memo]:
    """Memos containing `query` anywhere in the body, newest first.

    Substring matching, never FTS5: its tokenizers cannot find a two-character
    Japanese or Chinese word, which is most of what gets written here
    (ADR-0002). The guardrail tests in `tests/test_memo_api.py` fail the moment
    someone "optimises" this.
    """
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return session.scalars(
        select(Memo)
        .where(Memo.body.like(f"%{escaped}%", escape="\\"))
        .order_by(Memo.created_at.desc(), Memo.id.desc())
        .limit(RECENT_MEMO_LIMIT)
    ).all()


def list_memos(
    session: Session, images_dir: Path, query: str = ""
) -> list[MemoListing]:
    """The memos to show: the recent ones, or the ones matching a search.

    Ordered by creation, never by last change, so editing an old memo does not
    drag it to the top and break "I wrote that around last month" as a way of
    finding things. Ties break on id, so the order never wobbles between calls.
    """
    q = query.strip()
    memos = _matching(session, q) if q else _recent(session)

    listings = []
    for memo in memos:
        snippets, total = extract_snippets(memo.body, q) if q else ([], 0)
        listings.append(
            MemoListing(memo, count_images(images_dir, memo.id), snippets, total)
        )
    return listings


def get_memo(session: Session, memo_id: int) -> Memo:
    memo = session.get(Memo, memo_id)
    if memo is None:
        raise MemoNotFound(f"memo {memo_id} not found")
    return memo


def update_memo(
    session: Session,
    memo_id: int,
    body: str,
    images_dir: Path | None = None,
    uploads: Sequence[ImageUpload] = (),
) -> Memo:
    """Rewrite a memo's body, recording when it changed.

    Only `updated_at` moves; `created_at` is what the list sorts on, so editing
    something old leaves it where it was (see `list_memos`).
    """
    text = body.strip()
    if not text:
        raise EmptyMemo("a memo needs a body")

    memo = get_memo(session, memo_id)
    if images_dir is not None:
        text = images.save_and_link(
            memo_images_dir(images_dir, memo.id),
            _memo_images_url(memo.id),
            text,
            uploads,
        )

    memo.body = text
    memo.updated_at = utc_now()
    session.commit()
    return memo


def delete_memo(session: Session, memo_id: int, images_dir: Path | None = None) -> None:
    """Delete a memo and the screenshots that belonged to it.

    Outright, with no soft delete and no version history (spec Out of Scope).
    """
    memo = get_memo(session, memo_id)
    session.delete(memo)
    session.commit()

    if images_dir is not None:
        images.discard(memo_images_dir(images_dir, memo_id))
