from datetime import datetime

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UtcDateTime


class Bookmark(Base):
    """An entry pointing to a local file or folder — see CONTEXT.md and ADR-0006.

    Bookmark is an entry, not the file itself: multiple bookmarks can point to
    the same path (e.g. across different groups with different names).
    Therefore, path has deliberately no UNIQUE constraint.
    """

    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    is_directory: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
