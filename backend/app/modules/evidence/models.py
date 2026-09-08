from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, UtcDateTime


class BlockKind(StrEnum):
    """The three things a case is made of (CONTEXT.md).

    A log is `TEXT`, not a fourth kind — it needs no typesetting of its own
    (design.md §6 F5). The domain is closed and the export dispatches on it,
    which is why it is the column's type rather than a convention about a
    string.
    """

    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"


class Ordered:
    """A row that sits in an explicit place among its siblings.

    Cases within an evidence and blocks within a case are ordered the same
    way, by the same four buttons, so they carry the same column and share the
    reordering in `service.py`.
    """

    #: Where this row sits among its siblings. Contiguous from 0 and rewritten
    #: whenever the order changes, so "the third sheet" is a countable thing
    #: rather than something inferred from gaps.
    order: Mapped[int] = mapped_column()


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


class EvidenceCase(Ordered, Base):
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

    evidence: Mapped[Evidence] = relationship(back_populates="cases")
    blocks: Mapped[list["EvidenceBlock"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="EvidenceBlock.order, EvidenceBlock.id",
    )


class EvidenceBlock(Ordered, Base):
    """One piece of a case: a paragraph, a screenshot, a query result.

    The pieces of a case stand side by side rather than 1→2→3: numbering them
    would mean renumbering everything below the one you insert, and a case is
    not a procedure (ADR-0003). `label` is the optional small heading that says
    what a piece is ("事前準備の DB データ"); most blocks do without one.

    One table holds all three kinds, each carrying the payload its own kind
    needs and leaving the others empty: `text` for `TEXT`, `image_name` for
    `IMAGE`. The table block brings its own in ticket 06.
    """

    __tablename__ = "evidence_block"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_case.id", ondelete="CASCADE"), index=True
    )
    # Stored as its own value in a plain VARCHAR, not as a database enum:
    # `values_callable` because SQLAlchemy writes an enum's *name* by default,
    # which would put `TEXT` in the column and in everything read back from it.
    # The domain is held at the edges — the API refuses an unknown kind, and
    # loading one raises here — the way a case name's rules are, rather than by
    # a constraint baked into a SQLite table.
    kind: Mapped[BlockKind] = mapped_column(
        Enum(
            BlockKind,
            native_enum=False,
            values_callable=lambda kinds: [kind.value for kind in kinds],
        )
    )
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, default="")
    #: The file this block *is*, named within its evidence's image directory —
    #: a name and not a path, so the whole data directory stays movable
    #: (design.md §5) and one column cannot address another evidence's files.
    #: The directory is shared by every case of the evidence, so a name is only
    #: unique within it, which is why deleting a case deletes files one by one
    #: rather than the directory.
    image_name: Mapped[str] = mapped_column(Text, default="")

    case: Mapped[EvidenceCase] = relationship(back_populates="blocks")
