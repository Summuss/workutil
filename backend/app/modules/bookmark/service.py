"""What you can do with bookmarks and bookmark groups. Knows nothing about HTTP."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import utc_now
from app.core.ordering import Move, renumber, reorder
from app.modules.bookmark.models import Bookmark, BookmarkGroup


class PathDoesNotExist(ValueError):
    """The specified path does not exist on the machine."""


class EmptyName(ValueError):
    """A bookmark or group must have a non-empty name."""


class BookmarkNotFound(LookupError):
    """No bookmark has that id."""


class GroupNotFound(LookupError):
    """No bookmark group has that id."""


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


def _clean_name(raw_name: str, message: str = "书签名称不能为空") -> str:
    name = raw_name.strip()
    if not name:
        raise EmptyName(message)
    return name


def _groups_in_order(session: Session) -> list[BookmarkGroup]:
    stmt = (
        select(BookmarkGroup)
        .options(selectinload(BookmarkGroup.bookmarks))
        .order_by(BookmarkGroup.order, BookmarkGroup.id)
    )
    return list(session.scalars(stmt).all())


def _bookmarks_in_group(session: Session, group_id: int) -> list[Bookmark]:
    stmt = (
        select(Bookmark)
        .where(Bookmark.group_id == group_id)
        .order_by(Bookmark.order, Bookmark.id)
    )
    return list(session.scalars(stmt).all())


def _loose_bookmarks_in_order(session: Session) -> list[Bookmark]:
    stmt = (
        select(Bookmark)
        .where(Bookmark.group_id.is_(None))
        .order_by(Bookmark.order, Bookmark.id)
    )
    return list(session.scalars(stmt).all())


# --- Groups -----------------------------------------------------------------


def create_group(session: Session, name: str) -> BookmarkGroup:
    cleaned = _clean_name(name, "组名称不能为空")
    groups = _groups_in_order(session)
    now = utc_now()
    group = BookmarkGroup(
        name=cleaned,
        order=len(groups),
        created_at=now,
        updated_at=now,
    )
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


def get_group(session: Session, group_id: int) -> BookmarkGroup:
    group = session.get(BookmarkGroup, group_id)
    if group is None:
        raise GroupNotFound(f"Bookmark group {group_id} not found")
    return group


def update_group(session: Session, group_id: int, name: str) -> BookmarkGroup:
    group = get_group(session, group_id)
    group.name = _clean_name(name, "组名称不能为空")
    group.updated_at = utc_now()
    session.commit()
    session.refresh(group)
    return group


def delete_group(session: Session, group_id: int) -> None:
    """Delete a group without deleting its member bookmarks.

    Members become loose bookmarks (group_id=None) and append to the end of
    loose bookmarks. Remaining groups are renumbered without gaps.
    """
    group = get_group(session, group_id)
    members = _bookmarks_in_group(session, group_id)
    loose = _loose_bookmarks_in_order(session)
    loose_count = len(loose)

    for i, member in enumerate(members):
        member.group_id = None
        member.order = loose_count + i

    session.delete(group)
    remaining_groups = [g for g in _groups_in_order(session) if g.id != group_id]
    renumber(remaining_groups)
    session.commit()


def move_group(session: Session, group_id: int, to: Move) -> list[BookmarkGroup]:
    group = get_group(session, group_id)
    groups = reorder(_groups_in_order(session), group, to)
    session.commit()
    return groups


# --- Bookmarks --------------------------------------------------------------


def create_bookmark(
    session: Session,
    name: str,
    path: str,
    group_id: int | None = None,
) -> Bookmark:
    cleaned_name = _clean_name(name, "书签名称不能为空")
    cleaned_path, is_dir = validate_path(path)

    if group_id is not None:
        get_group(session, group_id)
        siblings = _bookmarks_in_group(session, group_id)
    else:
        siblings = _loose_bookmarks_in_order(session)

    now = utc_now()
    bookmark = Bookmark(
        name=cleaned_name,
        path=cleaned_path,
        is_directory=is_dir,
        group_id=group_id,
        order=len(siblings),
        created_at=now,
        updated_at=now,
    )
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


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
    group_id: int | None = None,
    update_group_id: bool = False,
) -> Bookmark:
    bookmark = get_bookmark(session, bookmark_id)

    if name is not None:
        bookmark.name = _clean_name(name, "书签名称不能为空")

    if path is not None:
        cleaned_path, is_dir = validate_path(path)
        bookmark.path = cleaned_path
        bookmark.is_directory = is_dir

    if update_group_id and group_id != bookmark.group_id:
        if group_id is not None:
            get_group(session, group_id)
            new_siblings = _bookmarks_in_group(session, group_id)
        else:
            new_siblings = _loose_bookmarks_in_order(session)

        old_group_id = bookmark.group_id
        if old_group_id is not None:
            old_siblings = [
                b
                for b in _bookmarks_in_group(session, old_group_id)
                if b.id != bookmark.id
            ]
        else:
            old_siblings = [
                b for b in _loose_bookmarks_in_order(session) if b.id != bookmark.id
            ]
        renumber(old_siblings)

        bookmark.group_id = group_id
        bookmark.order = len(new_siblings)

    bookmark.updated_at = utc_now()
    session.commit()
    session.refresh(bookmark)
    return bookmark


def delete_bookmark(session: Session, bookmark_id: int) -> None:
    bookmark = get_bookmark(session, bookmark_id)
    group_id = bookmark.group_id
    if group_id is not None:
        siblings = [
            b for b in _bookmarks_in_group(session, group_id) if b.id != bookmark.id
        ]
    else:
        siblings = [
            b for b in _loose_bookmarks_in_order(session) if b.id != bookmark.id
        ]

    session.delete(bookmark)
    renumber(siblings)
    session.commit()


def move_bookmark(session: Session, bookmark_id: int, to: Move) -> list[Bookmark]:
    bookmark = get_bookmark(session, bookmark_id)
    if bookmark.group_id is not None:
        siblings = _bookmarks_in_group(session, bookmark.group_id)
    else:
        siblings = _loose_bookmarks_in_order(session)

    reordered = reorder(siblings, bookmark, to)
    session.commit()
    return reordered


def list_all_bookmarks(
    session: Session,
) -> tuple[list[BookmarkGroup], list[Bookmark]]:
    groups = _groups_in_order(session)
    loose = _loose_bookmarks_in_order(session)
    return groups, loose
