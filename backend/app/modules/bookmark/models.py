from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, UtcDateTime
from app.core.ordering import Ordered


class BookmarkGroup(Ordered, Base):
    """A batch of bookmarks to be opened together — see CONTEXT.md and spec.md.

    Group order decides its place in the list (e.g. 'Daily Essential' on top).
    """

    __tablename__ = "bookmark_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)

    bookmarks: Mapped[list["Bookmark"]] = relationship(
        back_populates="group",
        order_by="Bookmark.order, Bookmark.id",
    )


class Bookmark(Ordered, Base):
    """An entry pointing to a local file or folder — see CONTEXT.md and ADR-0006.

    Bookmark is an entry, not the file itself: multiple bookmarks can point to
    the same path (e.g. across different groups with different names).
    Therefore, path has deliberately no UNIQUE constraint.

    A bookmark belongs to zero or one group (group_id nullable).
    """

    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookmark_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    is_directory: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)

    group: Mapped[BookmarkGroup | None] = relationship(back_populates="bookmarks")
