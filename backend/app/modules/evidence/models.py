from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, UtcDateTime


class Evidence(Base):
    """One round of verification, delivered as one xlsx file — see CONTEXT.md.

    The title is what the exported file is named after, and unlike a case name
    it is not delivered content: illegal filename characters are replaced when
    the file is built, not refused here (design.md §6 F5 Excel 导出).
    """

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)

    cases: Mapped[list["EvidenceCase"]] = relationship(
        back_populates="evidence",
        cascade="all, delete-orphan",
        order_by="EvidenceCase.order, EvidenceCase.id",
    )


class EvidenceCase(Base):
    """One test case inside an Evidence, exported as one sheet.

    `name` is the case number the author types (`1`, `2~5`), and it is also the
    sheet name — which is why it is validated on the way in rather than cleaned
    on the way out. The rules live in `service.validate_case_name`.
    """

    __tablename__ = "evidence_case"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    #: Where this case sits among its siblings. Contiguous from 0 and rewritten
    #: whenever the order changes, so "the third sheet" is a countable thing
    #: rather than something inferred from gaps.
    order: Mapped[int] = mapped_column()

    evidence: Mapped[Evidence] = relationship(back_populates="cases")
