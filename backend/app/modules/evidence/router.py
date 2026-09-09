"""HTTP for evidence. Forwarding only — the behaviour lives in service.py."""

from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import quote

from fastapi import APIRouter, status
from fastapi.responses import FileResponse, Response

from app.core import images
from app.core.deps import SessionDep, SettingsDep
from app.core.errors import http_error
from app.modules.evidence import layout, service
from app.modules.evidence.schemas import (
    BlockCreate,
    BlockLabelEdit,
    BlockRead,
    BlockTextEdit,
    CaseCreate,
    CaseDetail,
    CaseRead,
    CaseRename,
    DuplicateCaseResponse,
    EvidenceCreate,
    EvidenceDetail,
    EvidenceRead,
    EvidenceRename,
    ImageBlockCreate,
    MoveRequest,
    PastedBlockCreate,
    TableCellEdit,
    TableHeaderEdit,
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
        service.CellNotFound,
    ) as missing:
        raise http_error(status.HTTP_404_NOT_FOUND, missing) from missing
    except (
        service.InvalidTitle,
        service.InvalidCaseName,
        service.EmptyBlockText,
        service.EmptyTable,
        service.WrongBlockKind,
        service.EmptyEvidence,
        images.InvalidImage,
        layout.MissingImageFile,
    ) as invalid:
        raise http_error(status.HTTP_422_UNPROCESSABLE_CONTENT, invalid) from invalid


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


@router.get("/{evidence_id}/export")
def export_evidence(
    evidence_id: int, session: SessionDep, settings: SettingsDep
) -> Response:
    """Download the evidence as an Excel workbook (.xlsx).

    Refuses with 422 if the evidence has no cases (design.md §6 F5).
    Uses RFC 5987 filename* in Content-Disposition for non-ASCII safety.
    """
    with _as_http_error():
        filename, content = service.export_evidence(
            session, evidence_id, settings.images_dir
        )
    encoded = quote(filename)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


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
def delete_case(
    evidence_id: int, case_id: int, session: SessionDep, settings: SettingsDep
) -> None:
    with _as_http_error():
        service.delete_case(session, evidence_id, case_id, settings.images_dir)


@router.post("/{evidence_id}/cases/{case_id}/move", response_model=list[CaseRead])
def move_case(
    evidence_id: int, case_id: int, payload: MoveRequest, session: SessionDep
) -> list[CaseRead]:
    """Answers with the whole new order — a move that hit an end changed
    nothing, and the tab bar redraws from this either way."""
    with _as_http_error():
        cases = service.move_case(session, evidence_id, case_id, payload.to)
    return [CaseRead.model_validate(case) for case in cases]


@router.post(
    "/{evidence_id}/cases/{case_id}/duplicate",
    response_model=DuplicateCaseResponse,
)
def duplicate_case(
    evidence_id: int,
    case_id: int,
    session: SessionDep,
    settings: SettingsDep,
) -> DuplicateCaseResponse:
    with _as_http_error():
        cases, new_case_id = service.duplicate_case(
            session, evidence_id, case_id, settings.images_dir
        )
    return DuplicateCaseResponse(
        cases=[CaseRead.model_validate(case) for case in cases],
        new_case_id=new_case_id,
    )


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
    evidence_id: int,
    case_id: int,
    payload: BlockCreate,
    session: SessionDep,
    settings: SettingsDep,
) -> BlockRead:
    """Append a block to a case — one door for every kind, and for a paste.

    Which kind is in the body, and the union it is validated against refuses a
    kind with no payload behind it before this runs (see `BlockCreate`). A
    paste says only that it is a paste: what it becomes is worked out in the
    service, and the answer is the `kind` of the block that comes back.
    """
    with _as_http_error():
        if isinstance(payload, ImageBlockCreate):
            block = service.add_image_block(
                session,
                evidence_id,
                case_id,
                settings.images_dir,
                payload.image,
                payload.label,
            )
        elif isinstance(payload, PastedBlockCreate):
            block = service.add_pasted_block(
                session,
                evidence_id,
                case_id,
                payload.text,
                payload.html,
                payload.label,
            )
        else:
            block = service.add_text_block(
                session, evidence_id, case_id, payload.text, payload.label
            )
    return BlockRead.of(block, evidence_id)


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
    return BlockRead.of(block, evidence_id)


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
    return BlockRead.of(block, evidence_id)


@router.post(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}/as-text", response_model=BlockRead
)
def turn_block_into_text(
    evidence_id: int, case_id: int, block_id: int, session: SessionDep
) -> BlockRead:
    """Take back a table the server guessed wrong — this was a log all along.

    No body: the paste it was made of is already here, which is the only way
    the correction can hand back every character of it (spec 粘贴时的类型判别).
    """
    with _as_http_error():
        block = service.turn_block_into_text(session, evidence_id, case_id, block_id)
    return BlockRead.of(block, evidence_id)


@router.put(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}/header",
    response_model=BlockRead,
)
def set_table_header(
    evidence_id: int,
    case_id: int,
    block_id: int,
    payload: TableHeaderEdit,
    session: SessionDep,
) -> BlockRead:
    with _as_http_error():
        block = service.set_table_header(
            session, evidence_id, case_id, block_id, payload.has_header
        )
    return BlockRead.of(block, evidence_id)


@router.put(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}/cells/{row}/{column}",
    response_model=BlockRead,
)
def set_table_cell(
    evidence_id: int,
    case_id: int,
    block_id: int,
    row: int,
    column: int,
    payload: TableCellEdit,
    session: SessionDep,
) -> BlockRead:
    with _as_http_error():
        block = service.set_table_cell(
            session, evidence_id, case_id, block_id, row, column, payload.value
        )
    return BlockRead.of(block, evidence_id)


# A DELETE here and no POST, deliberately — the reason is in `service.py`, over
# the section these forward to.
@router.delete(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}/rows/{row}",
    response_model=BlockRead,
)
def delete_table_row(
    evidence_id: int, case_id: int, block_id: int, row: int, session: SessionDep
) -> BlockRead:
    """Answers with the whole table, the way a move answers with the whole order."""
    with _as_http_error():
        block = service.delete_table_row(session, evidence_id, case_id, block_id, row)
    return BlockRead.of(block, evidence_id)


@router.delete(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}/columns/{column}",
    response_model=BlockRead,
)
def delete_table_column(
    evidence_id: int, case_id: int, block_id: int, column: int, session: SessionDep
) -> BlockRead:
    with _as_http_error():
        block = service.delete_table_column(
            session, evidence_id, case_id, block_id, column
        )
    return BlockRead.of(block, evidence_id)


@router.delete(
    "/{evidence_id}/cases/{case_id}/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_block(
    evidence_id: int,
    case_id: int,
    block_id: int,
    session: SessionDep,
    settings: SettingsDep,
) -> None:
    with _as_http_error():
        service.delete_block(
            session, evidence_id, case_id, block_id, settings.images_dir
        )


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
    return [BlockRead.of(block, evidence_id) for block in blocks]


@router.get("/{evidence_id}/images/{filename}")
def get_evidence_image(
    evidence_id: int, filename: str, settings: SettingsDep
) -> FileResponse:
    """One screenshot out of an evidence's directory.

    Per evidence rather than per case: a screenshot outlives the case it was
    pasted into only for as long as that case does, but the file it is named
    against sits beside every other case's (`service.evidence_images_dir`).

    The traversal guard and the `nosniff` these bytes need are `images.serve`'s,
    shared with memo so the two cannot drift apart (design.md §6 F1).
    """
    return images.serve(
        service.evidence_images_dir(settings.images_dir, evidence_id), filename
    )
