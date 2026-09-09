"""What you can do with bookmarks and bookmark groups. Knows nothing about HTTP."""

import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import utc_now
from app.core.ordering import Move, renumber, reorder
from app.core.platform import Platform
from app.modules.bookmark.models import Bookmark, BookmarkGroup
from app.modules.bookmark.schemas import (
    BookmarkCheckItem,
    BookmarkCheckResponse,
    BookmarkGroupOpenResponse,
    OpenedBookmark,
    SkippedBookmark,
)


class PathDoesNotExist(ValueError):
    """The specified path does not exist on the machine."""

    code = "bookmark.path_not_found"


class EmptyName(ValueError):
    """A bookmark or group must have a non-empty name."""

    code = "bookmark.empty_name"


class BookmarkNotFound(LookupError):
    """No bookmark has that id."""

    code = "bookmark.not_found"


class GroupNotFound(LookupError):
    """No bookmark group has that id."""

    code = "bookmark.group_not_found"


class CannotRevealDirectory(ValueError):
    """A directory cannot be revealed because doing so reveals its parent."""

    code = "bookmark.cannot_reveal_directory"


def _clean_path(raw_path: str) -> str:
    # Windows "Copy as Path" (Shift+Right Click) wraps paths in double quotes,
    # and users might paste leading/trailing quotes or whitespace.
    return raw_path.strip().strip('"').strip("'")


def validate_path(raw_path: str) -> tuple[str, bool]:
    """Validate that the path exists on disk, and determine if it is a directory.

    Returns the cleaned path string and whether it is a directory.
    Raises PathDoesNotExist with user-facing message if absent.

    Requires an absolute path: a relative one resolves against whatever the
    backend process's current working directory happens to be at open-time,
    which is not something registration can promise stays fixed (a bookmark
    is meant to survive a restart, not just the session it was made in).
    """
    cleaned = _clean_path(raw_path)
    if not cleaned:
        raise PathDoesNotExist("这个路径现在不存在")

    target = Path(cleaned)
    if not target.is_absolute():
        raise PathDoesNotExist("请粘贴绝对路径，不支持相对路径")
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


def move_group(session: Session, group_id: int, to: Move | int) -> list[BookmarkGroup]:
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


def move_bookmark(session: Session, bookmark_id: int, to: Move | int) -> list[Bookmark]:
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


def open_bookmark(session: Session, bookmark_id: int, platform: Platform) -> Bookmark:
    bookmark = get_bookmark(session, bookmark_id)
    if not Path(bookmark.path).exists():
        raise PathDoesNotExist("这个路径现在不存在")
    platform.open(bookmark.path)
    return bookmark


def reveal_bookmark(session: Session, bookmark_id: int, platform: Platform) -> Bookmark:
    bookmark = get_bookmark(session, bookmark_id)
    if bookmark.is_directory:
        raise CannotRevealDirectory("文件夹书签不支持定位所在文件夹")
    if not Path(bookmark.path).exists():
        raise PathDoesNotExist("这个路径现在不存在")
    platform.reveal(bookmark.path)
    return bookmark


def open_group(
    session: Session,
    group_id: int,
    platform: Platform,
    interval_seconds: float = 0.2,
) -> BookmarkGroupOpenResponse:
    group = get_group(session, group_id)
    members = _bookmarks_in_group(session, group.id)
    opened: list[OpenedBookmark] = []
    skipped: list[SkippedBookmark] = []

    for member in members:
        if not Path(member.path).exists():
            skipped.append(
                SkippedBookmark(
                    id=member.id,
                    name=member.name,
                    path=member.path,
                    reason="路径不存在",
                )
            )
            continue

        if opened and interval_seconds > 0:
            time.sleep(interval_seconds)

        try:
            platform.open(member.path)
        except OSError as exc:
            # A real machine refusing to open a given path (no application
            # associated, permission denied, a dangling shortcut, ...) is the
            # same "skip it, keep going" story as a stale path — the button
            # promises the other members get opened, not a clean transaction.
            skipped.append(
                SkippedBookmark(
                    id=member.id,
                    name=member.name,
                    path=member.path,
                    reason=str(exc),
                )
            )
            continue

        opened.append(
            OpenedBookmark(
                id=member.id,
                name=member.name,
                path=member.path,
            )
        )

    return BookmarkGroupOpenResponse(opened=opened, skipped=skipped)


def _check_path_exists(raw_path: str) -> bool:
    try:
        return Path(raw_path).exists()
    except OSError:
        return False


def check_bookmarks(
    session: Session,
    bookmark_ids: list[int] | None = None,
) -> BookmarkCheckResponse:
    stmt = select(Bookmark)
    if bookmark_ids is not None:
        stmt = stmt.where(Bookmark.id.in_(bookmark_ids))
    stmt = stmt.order_by(Bookmark.id)
    bookmarks = list(session.scalars(stmt).all())

    items: list[BookmarkCheckItem] = []
    for b in bookmarks:
        items.append(
            BookmarkCheckItem(
                id=b.id,
                exists=_check_path_exists(b.path),
            )
        )
    return BookmarkCheckResponse(items=items)
