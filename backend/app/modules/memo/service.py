import base64
import shutil
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.memo.models import Memo
from app.modules.memo.schemas import ImageUpload

#: The list shows the recent past, not the whole archive — there is no paging,
#: so this is what "the list" means (spec 前端).
RECENT_MEMO_LIMIT = 200


class EmptyMemo(ValueError):
    """A memo with nothing in it is not a memo."""


class MemoNotFound(LookupError):
    """No memo has that id."""


class InvalidImage(ValueError):
    """Image data is malformed or cannot be decoded."""


def count_images(images_dir: Path, memo_id: int) -> int:
    """Number of image files belonging to this memo on disk."""
    memo_dir = images_dir / str(memo_id)
    if not memo_dir.is_dir():
        return 0
    return sum(1 for p in memo_dir.iterdir() if p.is_file())


def _decode_image_data(data: str) -> bytes:
    try:
        if data.startswith("data:") and ";base64," in data:
            _, b64 = data.split(";base64,", 1)
        else:
            b64 = data
        return base64.b64decode(b64)
    except Exception as e:
        raise InvalidImage(f"invalid base64 image data: {e}") from e


def _save_images(
    images_dir: Path,
    memo_id: int,
    body: str,
    images: Sequence[ImageUpload],
) -> tuple[str, int]:
    if not images:
        return body, count_images(images_dir, memo_id)

    memo_dir = images_dir / str(memo_id)
    memo_dir.mkdir(parents=True, exist_ok=True)

    existing_files = {p.name for p in memo_dir.iterdir() if p.is_file()}
    next_index = len(existing_files) + 1

    for img in images:
        if img.id not in body:
            continue

        raw_bytes = _decode_image_data(img.data)
        ext = Path(img.filename).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}:
            ext = ".png"

        while f"img_{next_index}{ext}" in existing_files:
            next_index += 1
        filename = f"img_{next_index}{ext}"
        existing_files.add(filename)
        next_index += 1

        target_path = memo_dir / filename
        target_path.write_bytes(raw_bytes)

        final_url = f"/api/memos/{memo_id}/images/{filename}"
        body = body.replace(img.id, final_url)

    return body, count_images(images_dir, memo_id)


def create_memo(
    session: Session,
    body: str,
    images_dir: Path | None = None,
    images: Sequence[ImageUpload] = (),
) -> tuple[Memo, int]:
    text = body.strip()
    if not text:
        raise EmptyMemo("a memo needs a body")

    now = utc_now()
    memo = Memo(body=text, created_at=now, updated_at=now)
    session.add(memo)
    session.flush()

    image_count = 0
    if images_dir is not None:
        new_body, image_count = _save_images(images_dir, memo.id, memo.body, images)
        memo.body = new_body

    session.commit()
    return memo, image_count


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
) -> tuple[Memo, int]:
    """Rewrite a memo's body, recording when it changed.

    Only `updated_at` moves; `created_at` is what the list sorts on, so editing
    something old leaves it where it was (see `list_memos`).
    """
    text = body.strip()
    if not text:
        raise EmptyMemo("a memo needs a body")

    memo = get_memo(session, memo_id)

    image_count = 0
    if images_dir is not None:
        text, image_count = _save_images(images_dir, memo.id, text, images)
    else:
        image_count = 0

    memo.body = text
    memo.updated_at = utc_now()
    session.commit()
    return memo, image_count


def delete_memo(session: Session, memo_id: int, images_dir: Path | None = None) -> None:
    """Permanently delete a memo and its image directory.

    Direct deletion without soft-delete or version history (spec Out of Scope).
    Deleting a memo cleans up its images/<memo_id>/ directory on disk.
    """
    memo = get_memo(session, memo_id)
    session.delete(memo)
    session.commit()

    if images_dir is not None:
        memo_dir = images_dir / str(memo_id)
        if memo_dir.is_dir():
            shutil.rmtree(memo_dir)
