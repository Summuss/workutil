from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.evidence.models import (
    BlockKind,
    Evidence,
    EvidenceBlock,
    EvidenceCase,
)
from app.modules.evidence.service import Move


class EvidenceCreate(BaseModel):
    title: str


class EvidenceRename(BaseModel):
    title: str


class CaseCreate(BaseModel):
    name: str


class CaseRename(BaseModel):
    name: str


class MoveRequest(BaseModel):
    """Where to send a case, or a block. The same four words for both."""

    to: Move


class BlockCreate(BaseModel):
    """A new block, and which of the three kinds it is.

    `kind` is required and can so far only be `text`: the other two carry a
    payload that does not exist yet, and a block claiming to be an image with
    no image behind it is worse than a refusal. Tickets 05 and 06 turn this
    into a union discriminated on `kind`.
    """

    kind: Literal[BlockKind.TEXT]
    text: str
    label: str | None = None


class BlockTextEdit(BaseModel):
    """New words for a text block."""

    text: str


class BlockLabelEdit(BaseModel):
    """A block's small heading. Absent, null and blank all mean "no heading"."""

    label: str | None = None


class BlockRead(BaseModel):
    """A block as the case shows it.

    `text` is empty for the kinds that carry something else — see the model.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: BlockKind
    order: int
    label: str | None
    text: str


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
            blocks=[BlockRead.model_validate(block) for block in blocks],
        )
