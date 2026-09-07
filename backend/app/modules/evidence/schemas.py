from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.evidence.models import Evidence, EvidenceCase
from app.modules.evidence.service import CaseMove


class EvidenceCreate(BaseModel):
    title: str


class EvidenceRename(BaseModel):
    title: str


class CaseCreate(BaseModel):
    name: str


class CaseRename(BaseModel):
    name: str


class CaseMoveRequest(BaseModel):
    to: CaseMove


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
