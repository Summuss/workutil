"""What you can do with memos. Knows nothing about HTTP."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.memo.models import Memo

#: The list shows the recent past, not the whole archive — there is no paging,
#: so this is what "the list" means (spec 前端).
RECENT_MEMO_LIMIT = 200


class EmptyMemo(ValueError):
    """A memo with nothing in it is not a memo."""


class MemoNotFound(Exception):
    """Raised when acting on a memo that does not exist."""


def create_memo(session: Session, body: str) -> Memo:
    text = body.strip()
    if not text:
        raise EmptyMemo("a memo needs a body")

    now = utc_now()
    memo = Memo(body=text, created_at=now, updated_at=now)
    session.add(memo)
    session.commit()
    return memo


def list_memos(session: Session) -> Sequence[Memo]:
    """The most recent memos, newest first.

    Ordered by creation, never by last change, so editing an old memo does not
    drag it to the top and break "I wrote that around last month" as a way of
    finding things. Ties break on id, so the order never wobbles between calls.
    """
    return session.scalars(
        select(Memo)
        .order_by(Memo.created_at.desc(), Memo.id.desc())
        .limit(RECENT_MEMO_LIMIT)
    ).all()


def get_memo(session: Session, memo_id: int) -> Memo | None:
    return session.get(Memo, memo_id)


def update_memo(session: Session, memo_id: int, body: str) -> Memo:
    text = body.strip()
    if not text:
        raise EmptyMemo("a memo needs a body")

    memo = session.get(Memo, memo_id)
    if memo is None:
        raise MemoNotFound(f"memo {memo_id} not found")

    memo.body = text
    memo.updated_at = utc_now()
    session.commit()
    return memo

