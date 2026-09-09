from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.images import IncomingImage
from app.core.ordering import MoveRequest as MoveRequest
from app.modules.evidence.models import (
    BlockKind,
    Evidence,
    EvidenceBlock,
    EvidenceCase,
)
from app.modules.evidence.service import evidence_images_url


class EvidenceCreate(BaseModel):
    title: str


class EvidenceRename(BaseModel):
    title: str


class CaseCreate(BaseModel):
    name: str


class CaseRename(BaseModel):
    name: str


class TextBlockCreate(BaseModel):
    """A new paragraph. A log is one of these — there is no separate kind."""

    kind: Literal[BlockKind.TEXT]
    text: str
    label: str | None = None


class ImageBlockCreate(BaseModel):
    """A new screenshot. One block holds one image, so this carries one.

    A paste of three arrives as three of these requests, which is what makes
    each of them a block that can be labelled and moved on its own
    (design.md §6 F5).
    """

    kind: Literal[BlockKind.IMAGE]
    image: IncomingImage
    label: str | None = None


class PastedBlockCreate(BaseModel):
    """Whatever was on the clipboard, for the server to make sense of.

    `paste` is not one of the three kinds — it is the absence of one. Cutting a
    clipboard into cells is where the kind is decided, and that parsing is on
    this side of the wire (design.md §6 F5), so the frontend says what it has
    rather than what it wants and reads the kind off the block that comes back.

    `html` is the compatibility flavour, present when the copy came from a web
    page or Excel. The tool this is for puts only `text/plain` on the
    clipboard, which is why tabs are the main path and this is the fallback.

    Screenshots do not arrive this way: an image is known to be one before it
    leaves the browser, and it travels as `ImageBlockCreate`.
    """

    kind: Literal["paste"]
    text: str
    html: str | None = None
    label: str | None = None


#: The ways a block can be created, told apart by `kind`. A block claiming a
#: kind with no payload behind it is refused here rather than in the service.
#:
#: There is no `table` member, and that is not an omission: a table is never
#: asked for, only recognised. It has exactly one origin — a paste the server
#: read as a query result — and letting a caller declare one would mean letting
#: it hand over rows nothing ever cut.
BlockCreate = Annotated[
    TextBlockCreate | ImageBlockCreate | PastedBlockCreate,
    Field(discriminator="kind"),
]


class BlockTextEdit(BaseModel):
    """New words for a text block."""

    text: str


class BlockLabelEdit(BaseModel):
    """A block's small heading. Absent, null and blank all mean "no heading"."""

    label: str | None = None


class TableCellEdit(BaseModel):
    """A new value for one cell, stored exactly as it is typed."""

    value: str


class TableHeaderEdit(BaseModel):
    """Whether a table's first row is column names.

    Stated rather than toggled, so the answer does not depend on what the
    screen believed when it asked.
    """

    has_header: bool


class BlockRead(BaseModel):
    """A block as the case shows it.

    Every kind is read through this one shape, each leaving the payloads that
    are not its own empty: `text` for a paragraph, `image_url` for a
    screenshot, `rows` and `has_header` for a query result. The screen switches
    on `kind`, not on which field is filled.

    The URL is built here rather than left to the browser to assemble out of an
    id and a filename: where an image is reachable is the server's to say, the
    way it is for a memo (`service.evidence_images_url`).

    The paste a table was cut from is deliberately not here. It is kept so a
    wrong guess can be taken back (`EvidenceBlock.table_source`), and the way
    to take it back is to ask for that — not to re-send the text.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: BlockKind
    order: int
    label: str | None
    text: str
    image_url: str | None = None
    rows: list[list[str]] = []
    has_header: bool = False

    @classmethod
    def of(cls, block: EvidenceBlock, evidence_id: int) -> "BlockRead":
        return cls(
            id=block.id,
            kind=block.kind,
            order=block.order,
            label=block.label,
            text=block.text,
            image_url=(
                f"{evidence_images_url(evidence_id)}/{block.image_name}"
                if block.kind is BlockKind.IMAGE
                else None
            ),
            rows=block.rows,
            has_header=block.has_header,
        )


class CaseRead(BaseModel):
    """A case as the tab bar sees it. `order` is its place among its siblings —
    sent so the UI can show a position, not so it can compute the next one."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    order: int


class EvidenceRead(BaseModel):
    """An evidence as the list shows it: no cases, only how many.

    The list is a way back into a workbook, not a preview of it (spec User
    Stories 7), so it stays cheap however many cases have piled up.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    case_count: int = 0

    @classmethod
    def of(cls, evidence: Evidence, case_count: int = 0) -> "EvidenceRead":
        return cls(
            id=evidence.id,
            title=evidence.title,
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
            case_count=case_count,
        )


class EvidenceDetail(EvidenceRead):
    """One evidence with its cases — what the detail page opens on."""

    cases: list[CaseRead] = []

    @classmethod
    def with_cases(
        cls, evidence: Evidence, cases: list[EvidenceCase]
    ) -> "EvidenceDetail":
        return cls(
            **EvidenceRead.of(evidence, len(cases)).model_dump(),
            cases=[CaseRead.model_validate(case) for case in cases],
        )


class CaseDetail(CaseRead):
    """One case with what is in it — what the content area opens on."""

    blocks: list[BlockRead] = []

    @classmethod
    def with_blocks(
        cls, case: EvidenceCase, blocks: list[EvidenceBlock]
    ) -> "CaseDetail":
        return cls(
            **CaseRead.model_validate(case).model_dump(),
            blocks=[BlockRead.of(block, case.evidence_id) for block in blocks],
        )
