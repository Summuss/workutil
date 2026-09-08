"""HTTP for bookmarks. Forwarding only — the behaviour lives in service.py."""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import SessionDep
from app.modules.bookmark import service
from app.modules.bookmark.schemas import BookmarkCreate, BookmarkRead, BookmarkUpdate

router = APIRouter(prefix="/bookmarks", tags=["bookmark"])


@router.post("", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED)
def create_bookmark(payload: BookmarkCreate, session: SessionDep) -> BookmarkRead:
    try:
        bookmark = service.create_bookmark(session, payload.name, payload.path)
    except service.PathDoesNotExist as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    except service.EmptyName as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return BookmarkRead.model_validate(bookmark)


@router.get("", response_model=list[BookmarkRead])
def list_bookmarks(session: SessionDep) -> list[BookmarkRead]:
    return [BookmarkRead.model_validate(b) for b in service.list_bookmarks(session)]


@router.get("/{bookmark_id}", response_model=BookmarkRead)
def get_bookmark(bookmark_id: int, session: SessionDep) -> BookmarkRead:
    try:
        bookmark = service.get_bookmark(session, bookmark_id)
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    return BookmarkRead.model_validate(bookmark)


@router.patch("/{bookmark_id}", response_model=BookmarkRead)
def update_bookmark(
    bookmark_id: int, payload: BookmarkUpdate, session: SessionDep
) -> BookmarkRead:
    try:
        bookmark = service.update_bookmark(
            session, bookmark_id, name=payload.name, path=payload.path
        )
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except service.PathDoesNotExist as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from err
    except service.EmptyName as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from err
    return BookmarkRead.model_validate(bookmark)


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: int, session: SessionDep) -> None:
    try:
        service.delete_bookmark(session, bookmark_id)
    except service.BookmarkNotFound as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
