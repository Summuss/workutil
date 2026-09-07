"""What you can do with memos. Knows nothing about HTTP."""

import base64
import binascii
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.memo.models import Memo
from app.modules.memo.schemas import ImageUpload
from app.modules.memo.snippets import extract_snippets

#: The list shows the recent past, not the whole archive — there is no paging,
#: so this is what "the list" means (spec 前端). Search answers from the same
#: window, so a query can never return more rows than browsing does.
RECENT_MEMO_LIMIT = 200

#: What a screenshot may be saved as. SVG is deliberately absent: it is a
#: scriptable document, and it would be served from this app's own origin,
#: which is the chain design.md §6 F1 exists to cut. Anything else is stored
#: as .png — the bytes are untouched either way, only the name is decided here.
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})

#: A screenshot is big; 25 MB of it is a mistake, not a memo. The whole body
#: and every image travel in one request, so this bounds that request too.
MAX_IMAGE_BYTES = 25 * 1024 * 1024


class EmptyMemo(ValueError):
    """A memo with nothing in it is not a memo."""


class MemoNotFound(LookupError):
    """No memo has that id."""


class InvalidImage(ValueError):
    """Image data is malformed, unreadable, or too large."""


class MemoListing(NamedTuple):
    """A memo as the list shows it: the memo, plus what is said about it."""

    memo: Memo
    image_count: int
    snippets: list[str]
    snippet_total: int


def count_images(images_dir: Path, memo_id: int) -> int:
    """Number of image files this memo has on disk.

    Derived from the directory rather than stored, so the files are the single
    truth and nothing can drift out of sync with them. `create_memo` is what
    keeps that honest — see `_discard_images`.
    """
    memo_dir = images_dir / str(memo_id)
    if not memo_dir.is_dir():
        return 0
    return sum(1 for path in memo_dir.iterdir() if path.is_file())


def _discard_images(images_dir: Path, memo_id: int) -> None:
    """Throw away a memo's images, tolerating a file that will not go.

    On Windows a screenshot open in a viewer cannot be unlinked. That must not
    turn into a failed delete: the memo itself is already gone, and a refusal
    would say otherwise. What is left behind is picked up when the id comes
    round again.
    """
    memo_dir = images_dir / str(memo_id)
    if memo_dir.is_dir():
        shutil.rmtree(memo_dir, ignore_errors=True)


def _decode_image(image: ImageUpload) -> bytes:
    """The bytes behind a data URL, or a refusal.

    Every image is decoded before any of them is written, so one bad image
    fails the whole save instead of leaving half of them on disk.
    """
    data = image.data
    encoded = data.split(";base64,", 1)[1] if ";base64," in data else data
    try:
        raw = base64.b64decode("".join(encoded.split()), validate=True)
    except (binascii.Error, ValueError) as bad:
        raise InvalidImage(f"image {image.filename} is not valid base64") from bad

    if len(raw) > MAX_IMAGE_BYTES:
        raise InvalidImage(
            f"image {image.filename} is larger than "
            f"{MAX_IMAGE_BYTES // (1024 * 1024)} MB"
        )
    return raw


def _save_images(
    images_dir: Path,
    memo_id: int,
    body: str,
    images: Sequence[ImageUpload],
) -> str:
    """Put the images this body still refers to on disk, and point it at them.

    An image whose placeholder was deleted while writing is not saved: the text
    decides what the memo contains, right up to the moment it is sent.
    """
    wanted = [image for image in images if image.id in body]
    if not wanted:
        return body

    decoded = [(image, _decode_image(image)) for image in wanted]

    memo_dir = images_dir / str(memo_id)
    is_new_dir = not memo_dir.exists()
    memo_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    try:
        taken = {path.name for path in memo_dir.iterdir() if path.is_file()}
        index = 1
        for image, raw in decoded:
            suffix = Path(image.filename).suffix.lower()
            if suffix not in IMAGE_EXTENSIONS:
                suffix = ".png"
            while f"img_{index}{suffix}" in taken:
                index += 1
            name = f"img_{index}{suffix}"
            taken.add(name)

            path = memo_dir / name
            path.write_bytes(raw)
            written.append(path)
            body = body.replace(image.id, f"/api/memos/{memo_id}/images/{name}")
    except OSError:
        # Half a memo's screenshots is worse than none: the body that would
        # have named them is about to be rolled back with the rest of the save.
        for path in written:
            path.unlink(missing_ok=True)
        if is_new_dir:
            shutil.rmtree(memo_dir, ignore_errors=True)
        raise

    return body


def create_memo(
    session: Session,
    body: str,
    images_dir: Path | None = None,
    images: Sequence[ImageUpload] = (),
) -> Memo:
    text = body.strip()
    if not text:
        raise EmptyMemo("a memo needs a body")

    now = utc_now()
    memo = Memo(body=text, created_at=now, updated_at=now)
    session.add(memo)
    session.flush()

    if images_dir is not None:
        # SQLite hands out the id of a memo that was rolled back or deleted, so
        # a directory can already be sitting here. Whatever left it, it is not
        # this memo's: a memo being created has never had an image.
        _discard_images(images_dir, memo.id)
        memo.body = _save_images(images_dir, memo.id, memo.body, images)

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
    images: Sequence[ImageUpload] = (),
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
        text = _save_images(images_dir, memo.id, text, images)

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
        _discard_images(images_dir, memo_id)
