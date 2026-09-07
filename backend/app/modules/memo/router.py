"""HTTP for memos. Forwarding only — the behaviour lives in service.py."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.deps import SessionDep, SettingsDep
from app.modules.memo import service
from app.modules.memo.schemas import MemoCreate, MemoRead, MemoUpdate

router = APIRouter(prefix="/memos", tags=["memo"])


@router.post("", response_model=MemoRead, status_code=status.HTTP_201_CREATED)
def create_memo(
    payload: MemoCreate,
    session: SessionDep,
    settings: SettingsDep,
) -> MemoRead:
    try:
        memo, image_count = service.create_memo(
            session, payload.body, settings.images_dir, payload.images
        )
        return MemoRead(
            id=memo.id,
            body=memo.body,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            image_count=image_count,
        )
    except service.EmptyMemo as empty:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(empty)
        ) from empty
    except service.InvalidImage as invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)
        ) from invalid


@router.get("", response_model=list[MemoRead])
def list_memos(session: SessionDep, settings: SettingsDep) -> list[MemoRead]:
    return [
        MemoRead(
            id=memo.id,
            body=memo.body,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            image_count=service.count_images(settings.images_dir, memo.id),
        )
        for memo in service.list_memos(session)
    ]


@router.get("/{memo_id}", response_model=MemoRead)
def get_memo(memo_id: int, session: SessionDep, settings: SettingsDep) -> MemoRead:
    try:
        memo = service.get_memo(session, memo_id)
        return MemoRead(
            id=memo.id,
            body=memo.body,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            image_count=service.count_images(settings.images_dir, memo.id),
        )
    except service.MemoNotFound as not_found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(not_found)) from not_found


@router.patch("/{memo_id}", response_model=MemoRead)
def update_memo(
    memo_id: int,
    payload: MemoUpdate,
    session: SessionDep,
    settings: SettingsDep,
) -> MemoRead:
    try:
        memo, image_count = service.update_memo(
            session, memo_id, payload.body, settings.images_dir, payload.images
        )
        return MemoRead(
            id=memo.id,
            body=memo.body,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            image_count=image_count,
        )
    except service.EmptyMemo as empty:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(empty)
        ) from empty
    except service.MemoNotFound as not_found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(not_found)) from not_found
    except service.InvalidImage as invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)
        ) from invalid


@router.delete("/{memo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memo(memo_id: int, session: SessionDep, settings: SettingsDep) -> None:
    try:
        service.delete_memo(session, memo_id, settings.images_dir)
    except service.MemoNotFound as not_found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(not_found)) from not_found


@router.get("/{memo_id}/images/{filename}")
def get_memo_image(
    memo_id: int,
    filename: str,
    settings: SettingsDep,
) -> FileResponse:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image not found")

    image_path = settings.images_dir / str(memo_id) / filename
    if not image_path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image not found")

    return FileResponse(image_path)
