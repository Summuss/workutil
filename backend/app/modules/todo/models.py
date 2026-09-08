from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime


class Todo(Base):
    """A single task to be done — see CONTEXT.md and spec.md.

    Has deliberately no foreign key to memos when created from memo:
    source_memo_id is just an id, not a constraint (Ticket 04).
    """

    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(
        UtcDateTime, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
