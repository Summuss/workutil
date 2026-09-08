"""HTTP for bookmarks and bookmark groups.

Forwarding only — the behaviour lives in service.py.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import PlatformDep, SessionDep
from app.core.platform import UnsupportedPlatformError
from app.modules.bookmark import service
from app.modules.bookmark.schemas import (
    BookmarkActionResponse,
    BookmarkCreate,
    BookmarkGroupCreate,
    BookmarkGroupOpenResponse,
    BookmarkGroupRead,
    BookmarkGroupUpdate,
    BookmarkListResponse,
    BookmarkRead,
    BookmarkUpdate,
    MoveRequest,
)

router = APIRouter()
bookmarks_router = APIRouter(prefix="/bookmarks", tags=["bookmark"])
groups_router = APIRouter(prefix="/bookmark-groups", tags=["bookmark-group"])


# --- Groups ---


@groups_router.post(
    "",
    response_model=BookmarkGroupRead,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    payload: BookmarkGroupCreate, session: SessionDep
) -> BookmarkGroupRead:
    try:
        group = service.create_group(session, payload.name)
    except service.EmptyName as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return BookmarkGroupRead.model_validate(group)


@groups_router.patch("/{group_id}", response_model=BookmarkGroupRead)
def update_group(
    group_id: int, payload: BookmarkGroupUpdate, session: SessionDep
) -> BookmarkGroupRead:
    try:
        group = service.update_group(session, group_id, payload.name)
    except service.GroupNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.EmptyName as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return BookmarkGroupRead.model_validate(group)


@groups_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, session: SessionDep) -> None:
    try:
        service.delete_group(session, group_id)
    except service.GroupNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err


@groups_router.post("/{group_id}/move", response_model=list[BookmarkGroupRead])
def move_group(
    group_id: int, payload: MoveRequest, session: SessionDep
) -> list[BookmarkGroupRead]:
    try:
        groups = service.move_group(session, group_id, payload.to)
    except service.GroupNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    return [BookmarkGroupRead.model_validate(g) for g in groups]


@groups_router.post("/{group_id}/open", response_model=BookmarkGroupOpenResponse)
def open_group(
    group_id: int, session: SessionDep, platform: PlatformDep
) -> BookmarkGroupOpenResponse:
    try:
        return service.open_group(session, group_id, platform)
    except service.GroupNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except UnsupportedPlatformError as err:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(err)) from err


# --- Bookmarks ---


@bookmarks_router.post(
    "",
    response_model=BookmarkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_bookmark(payload: BookmarkCreate, session: SessionDep) -> BookmarkRead:
    try:
        bookmark = service.create_bookmark(
            session, payload.name, payload.path, group_id=payload.group_id
        )
    except service.GroupNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.PathDoesNotExist as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    except service.EmptyName as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return BookmarkRead.model_validate(bookmark)


@bookmarks_router.get("", response_model=BookmarkListResponse)
def list_bookmarks(session: SessionDep) -> BookmarkListResponse:
    groups, loose = service.list_all_bookmarks(session)
    return BookmarkListResponse(
        groups=[BookmarkGroupRead.model_validate(g) for g in groups],
        loose=[BookmarkRead.model_validate(b) for b in loose],
    )


@bookmarks_router.get("/{bookmark_id}", response_model=BookmarkRead)
def get_bookmark(bookmark_id: int, session: SessionDep) -> BookmarkRead:
    try:
        bookmark = service.get_bookmark(session, bookmark_id)
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    return BookmarkRead.model_validate(bookmark)


@bookmarks_router.patch("/{bookmark_id}", response_model=BookmarkRead)
def update_bookmark(
    bookmark_id: int, payload: BookmarkUpdate, session: SessionDep
) -> BookmarkRead:
    update_group_id = "group_id" in payload.model_fields_set
    try:
        bookmark = service.update_bookmark(
            session,
            bookmark_id,
            name=payload.name,
            path=payload.path,
            group_id=payload.group_id,
            update_group_id=update_group_id,
        )
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.GroupNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.PathDoesNotExist as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    except service.EmptyName as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return BookmarkRead.model_validate(bookmark)


@bookmarks_router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: int, session: SessionDep) -> None:
    try:
        service.delete_bookmark(session, bookmark_id)
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err


@bookmarks_router.post("/{bookmark_id}/move", response_model=list[BookmarkRead])
def move_bookmark(
    bookmark_id: int, payload: MoveRequest, session: SessionDep
) -> list[BookmarkRead]:
    try:
        reordered = service.move_bookmark(session, bookmark_id, payload.to)
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    return [BookmarkRead.model_validate(b) for b in reordered]


@bookmarks_router.post("/{bookmark_id}/open", response_model=BookmarkActionResponse)
def open_bookmark(
    bookmark_id: int, session: SessionDep, platform: PlatformDep
) -> BookmarkActionResponse:
    try:
        bookmark = service.open_bookmark(session, bookmark_id, platform)
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.PathDoesNotExist as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    except UnsupportedPlatformError as err:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(err)) from err
    return BookmarkActionResponse(
        ok=True, id=bookmark.id, name=bookmark.name, path=bookmark.path
    )


@bookmarks_router.post("/{bookmark_id}/reveal", response_model=BookmarkActionResponse)
def reveal_bookmark(
    bookmark_id: int, session: SessionDep, platform: PlatformDep
) -> BookmarkActionResponse:
    try:
        bookmark = service.reveal_bookmark(session, bookmark_id, platform)
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.CannotRevealDirectory as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    except service.PathDoesNotExist as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    except UnsupportedPlatformError as err:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(err)) from err
    return BookmarkActionResponse(
        ok=True, id=bookmark.id, name=bookmark.name, path=bookmark.path
    )


router.include_router(bookmarks_router)
router.include_router(groups_router)
