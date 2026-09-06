from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime


class Memo(Base):
    """A scrap of information saved in one go — see CONTEXT.md.

    There is deliberately no title column: having to name a memo is friction,
    and the line shown in the list is cut from the body by whoever displays it.
    """

    __tablename__ = "memos"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
