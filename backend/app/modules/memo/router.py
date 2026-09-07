"""HTTP for memos. Forwarding only — the behaviour lives in service.py."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core import images
from app.core.deps import SessionDep, SettingsDep
from app.modules.memo import service
from app.modules.memo.schemas import MemoCreate, MemoRead, MemoUpdate

router = APIRouter(prefix="/memos", tags=["memo"])


@router.post("", response_model=MemoRead, status_code=status.HTTP_201_CREATED)
def create_memo(
    payload: MemoCreate, session: SessionDep, settings: SettingsDep
) -> MemoRead:
    try:
        memo = service.create_memo(
            session, payload.body, settings.images_dir, payload.images
        )
    except service.EmptyMemo as empty:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(empty)
        ) from empty
    except images.InvalidImage as invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)
        ) from invalid
    return MemoRead.of(memo, service.count_images(settings.images_dir, memo.id))


@router.get("", response_model=list[MemoRead])
def list_memos(
    session: SessionDep, settings: SettingsDep, q: str | None = None
) -> list[MemoRead]:
    return [
        MemoRead.of(
            listing.memo,
            listing.image_count,
            listing.snippets,
            listing.snippet_total,
        )
        for listing in service.list_memos(session, settings.images_dir, q or "")
    ]


@router.get("/{memo_id}", response_model=MemoRead)
def get_memo(memo_id: int, session: SessionDep, settings: SettingsDep) -> MemoRead:
    try:
        memo = service.get_memo(session, memo_id)
    except service.MemoNotFound as not_found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(not_found)) from not_found
    return MemoRead.of(memo, service.count_images(settings.images_dir, memo.id))


@router.patch("/{memo_id}", response_model=MemoRead)
def update_memo(
    memo_id: int,
    payload: MemoUpdate,
    session: SessionDep,
    settings: SettingsDep,
) -> MemoRead:
    try:
        memo = service.update_memo(
            session, memo_id, payload.body, settings.images_dir, payload.images
        )
    except service.EmptyMemo as empty:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(empty)
        ) from empty
    except service.MemoNotFound as not_found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(not_found)) from not_found
    except images.InvalidImage as invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)
        ) from invalid
    return MemoRead.of(memo, service.count_images(settings.images_dir, memo.id))


@router.delete("/{memo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memo(memo_id: int, session: SessionDep, settings: SettingsDep) -> None:
    try:
        service.delete_memo(session, memo_id, settings.images_dir)
    except service.MemoNotFound as not_found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(not_found)) from not_found


@router.get("/{memo_id}/images/{filename}")
def get_memo_image(memo_id: int, filename: str, settings: SettingsDep) -> FileResponse:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image not found")

    image_path = service.memo_images_dir(settings.images_dir, memo_id) / filename
    if not image_path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image not found")

    # These bytes came from a paste. Whatever the extension claims, the browser
    # must not go looking for something more interesting in them and end up
    # running a document from this app's own origin (design.md §6 F1).
    return FileResponse(image_path, headers={"X-Content-Type-Options": "nosniff"})
