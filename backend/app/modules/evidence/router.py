"""HTTP for evidence. Forwarding only — the behaviour lives in service.py."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, status

from app.core.deps import SessionDep, SettingsDep
from app.modules.evidence import service
from app.modules.evidence.schemas import (
    BlockCreate,
    BlockLabelEdit,
    BlockRead,
    BlockTextEdit,
    CaseCreate,
    CaseDetail,
    CaseRead,
    CaseRename,
    EvidenceCreate,
    EvidenceDetail,
    EvidenceRead,
    EvidenceRename,
    MoveRequest,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])


@contextmanager
def _as_http_error() -> Iterator[None]:
    """Service refusals as their HTTP equivalents.

    Every endpoint here shares the same handful of refusals, and spelling the
    mapping out at each one buries the forwarding under it. A rejected name is
    a 422 rather than a 409 even when the reason is a sibling with that name:
    to whoever typed it, all the rules are the same field coming back with a
    reason under it.
    """
    try:
        yield
    except (
        service.EvidenceNotFound,
        service.CaseNotFound,
        service.BlockNotFound,
    ) as missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(missing)) from missing
    except (
        service.InvalidTitle,
        service.InvalidCaseName,
        service.EmptyBlockText,
    ) as invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(invalid)
        ) from invalid


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate, session: SessionDep, settings: SettingsDep
) -> EvidenceRead:
    with _as_http_error():
        evidence = service.create_evidence(session, payload.title, settings.images_dir)
    return EvidenceRead.of(evidence)


@router.get("", response_model=list[EvidenceRead])
def list_evidence(session: SessionDep) -> list[EvidenceRead]:
    return [
        EvidenceRead.of(listing.evidence, listing.case_count)
        for listing in service.list_evidence(session)
    ]


@router.get("/{evidence_id}", response_model=EvidenceDetail)
def get_evidence(evidence_id: int, session: SessionDep) -> EvidenceDetail:
    with _as_http_error():
        opened = service.open_evidence(session, evidence_id)
    return EvidenceDetail.with_cases(opened.evidence, opened.cases)


@router.patch("/{evidence_id}", response_model=EvidenceRead)
def rename_evidence(
    evidence_id: int, payload: EvidenceRename, session: SessionDep
) -> EvidenceRead:
    with _as_http_error():
        evidence = service.rename_evidence(session, evidence_id, payload.title)
        case_count = service.count_cases(session, evidence_id)
    return EvidenceRead.of(evidence, case_count)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: int, session: SessionDep, settings: SettingsDep
) -> None:
    with _as_http_error():
        service.delete_evidence(session, evidence_id, settings.images_dir)


@router.post(
    "/{evidence_id}/cases",
    response_model=CaseRead,
    status_code=status.HTTP_201_CREATED,
)
def add_case(evidence_id: int, payload: CaseCreate, session: SessionDep) -> CaseRead:
    with _as_http_error():
        case = service.add_case(session, evidence_id, payload.name)
    return CaseRead.model_validate(case)


@router.patch("/{evidence_id}/cases/{case_id}", response_model=CaseRead)
def rename_case(
    evidence_id: int, case_id: int, payload: CaseRename, session: SessionDep
) -> CaseRead:
    with _as_http_error():
        case = service.rename_case(session, evidence_id, case_id, payload.name)
    return CaseRead.model_validate(case)


@router.delete("/{evidence_id}/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(evidence_id: int, case_id: int, session: SessionDep) -> None:
    with _as_http_error():
        service.delete_case(session, evidence_id, case_id)


@router.post("/{evidence_id}/cases/{case_id}/move", response_model=list[CaseRead])
def move_case(
    evidence_id: int, case_id: int, payload: MoveRequest, session: SessionDep
) -> list[CaseRead]:
    """Answers with the whole new order — a move that hit an end changed
    nothing, and the tab bar redraws from this either way."""
    with _as_http_error():
        cases = service.move_case(session, evidence_id, case_id, payload.to)
    return [CaseRead.model_validate(case) for case in cases]


@router.get("/{evidence_id}/cases/{case_id}", response_model=CaseDetail)
def get_case(evidence_id: int, case_id: int, session: SessionDep) -> CaseDetail:
    with _as_http_error():
        opened = service.open_case(session, evidence_id, case_id)
    return CaseDetail.with_blocks(opened.case, opened.blocks)


@router.post(
    "/{evidence_id}/cases/{case_id}/blocks",
    response_model=BlockRead,
    status_code=status.HTTP_201_CREATED,
)
def add_block(
    evidence_id: int, case_id: int, payload: BlockCreate, session: SessionDep
) -> BlockRead:
    """Append a block to a case. Only `text` so far — see `BlockCreate`."""
    with _as_http_error():
        block = service.add_text_block(
            session, evidence_id, case_id, payload.text, payload.label
        )
    return BlockRead.model_validate(block)


@router.patch(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}", response_model=BlockRead
)
def edit_block_text(
    evidence_id: int,
    case_id: int,
    block_id: int,
    payload: BlockTextEdit,
    session: SessionDep,
) -> BlockRead:
    with _as_http_error():
        block = service.set_block_text(
            session, evidence_id, case_id, block_id, payload.text
        )
    return BlockRead.model_validate(block)


@router.put(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}/label", response_model=BlockRead
)
def set_block_label(
    evidence_id: int,
    case_id: int,
    block_id: int,
    payload: BlockLabelEdit,
    session: SessionDep,
) -> BlockRead:
    """Set or clear a block's heading.

    Its own endpoint rather than a field of the edit above: the heading belongs
    to every kind of block, while the payload belongs to one of them.
    """
    with _as_http_error():
        block = service.set_block_label(
            session, evidence_id, case_id, block_id, payload.label
        )
    return BlockRead.model_validate(block)


@router.delete(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_block(
    evidence_id: int, case_id: int, block_id: int, session: SessionDep
) -> None:
    with _as_http_error():
        service.delete_block(session, evidence_id, case_id, block_id)


@router.post(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}/move",
    response_model=list[BlockRead],
)
def move_block(
    evidence_id: int,
    case_id: int,
    block_id: int,
    payload: MoveRequest,
    session: SessionDep,
) -> list[BlockRead]:
    """Answers with the whole new order, the way moving a case does."""
    with _as_http_error():
        blocks = service.move_block(session, evidence_id, case_id, block_id, payload.to)
    return [BlockRead.model_validate(block) for block in blocks]
