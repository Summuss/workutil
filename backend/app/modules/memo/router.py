"""HTTP for memos. Forwarding only — the behaviour lives in service.py."""

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status

from app.core.deps import SessionDep
from app.modules.memo import service
from app.modules.memo.models import Memo
from app.modules.memo.schemas import MemoCreate, MemoRead, MemoUpdate

router = APIRouter(prefix="/memos", tags=["memo"])


@router.post("", response_model=MemoRead, status_code=status.HTTP_201_CREATED)
def create_memo(payload: MemoCreate, session: SessionDep) -> Memo:
    try:
        return service.create_memo(session, payload.body)
    except service.EmptyMemo as empty:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(empty)
        ) from empty


@router.get("", response_model=list[MemoRead])
def list_memos(session: SessionDep) -> Sequence[Memo]:
    return service.list_memos(session)


@router.get("/{memo_id}", response_model=MemoRead)
def get_memo(memo_id: int, session: SessionDep) -> Memo:
    memo = service.get_memo(session, memo_id)
    if memo is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"memo {memo_id} not found"
        )
    return memo


@router.patch("/{memo_id}", response_model=MemoRead)
def update_memo(
    memo_id: int, payload: MemoUpdate, session: SessionDep
) -> Memo:
    try:
        return service.update_memo(session, memo_id, payload.body)
    except service.EmptyMemo as empty:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(empty)
        ) from empty
    except service.MemoNotFound as not_found:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, str(not_found)
        ) from not_found

