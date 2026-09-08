"""What you can do with bookmarks. Knows nothing about HTTP."""

from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utc_now
from app.modules.bookmark.models import Bookmark


class PathDoesNotExist(ValueError):
    """The specified path does not exist on the machine."""


class EmptyName(ValueError):
    """A bookmark must have a non-empty name."""


class BookmarkNotFound(LookupError):
    """No bookmark has that id."""


def _clean_path(raw_path: str) -> str:
    # Windows "Copy as Path" (Shift+Right Click) wraps paths in double quotes,
    # and users might paste leading/trailing quotes or whitespace.
    return raw_path.strip().strip('"').strip("'")


def validate_path(raw_path: str) -> tuple[str, bool]:
    """Validate that the path exists on disk, and determine if it is a directory.

    Returns the cleaned path string and whether it is a directory.
    Raises PathDoesNotExist with user-facing message if absent.
    """
    cleaned = _clean_path(raw_path)
    if not cleaned:
        raise PathDoesNotExist("这个路径现在不存在")

    target = Path(cleaned)
    if not target.exists():
        raise PathDoesNotExist("这个路径现在不存在")

    return cleaned, target.is_dir()


def _clean_name(raw_name: str) -> str:
    name = raw_name.strip()
    if not name:
        raise EmptyName("书签名称不能为空")
    return name


def create_bookmark(session: Session, name: str, path: str) -> Bookmark:
    cleaned_name = _clean_name(name)
    cleaned_path, is_dir = validate_path(path)

    now = utc_now()
    bookmark = Bookmark(
        name=cleaned_name,
        path=cleaned_path,
        is_directory=is_dir,
        created_at=now,
        updated_at=now,
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


def list_bookmarks(session: Session) -> Sequence[Bookmark]:
    stmt = select(Bookmark).order_by(Bookmark.id.desc())
    return session.scalars(stmt).all()


def get_bookmark(session: Session, bookmark_id: int) -> Bookmark:
    bookmark = session.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise BookmarkNotFound(f"Bookmark {bookmark_id} not found")
    return bookmark


def update_bookmark(
    session: Session,
    bookmark_id: int,
    name: str | None = None,
    path: str | None = None,
) -> Bookmark:
    bookmark = get_bookmark(session, bookmark_id)

    if name is not None:
        bookmark.name = _clean_name(name)

    if path is not None:
        cleaned_path, is_dir = validate_path(path)
        bookmark.path = cleaned_path
        bookmark.is_directory = is_dir

    bookmark.updated_at = utc_now()
    session.commit()
    session.refresh(bookmark)
    return bookmark


def delete_bookmark(session: Session, bookmark_id: int) -> None:
    bookmark = get_bookmark(session, bookmark_id)
    session.delete(bookmark)
    session.commit()
