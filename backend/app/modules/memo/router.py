"""HTTP for memos. Forwarding only — the behaviour lives in service.py."""

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status

from app.core.deps import SessionDep
from app.modules.memo import service
from app.modules.memo.models import Memo
from app.modules.memo.schemas import MemoCreate, MemoRead

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
