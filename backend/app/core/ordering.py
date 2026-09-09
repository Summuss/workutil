"""Explicit ordering among siblings. Shared across Todo, Bookmark, and Evidence."""

from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column


class Move(StrEnum):
    """Boundary jumps for rows among siblings."""

    TOP = "top"
    BOTTOM = "bottom"


class MoveRequest(BaseModel):
    """Where a row is sent: boundary jump ("top"/"bottom") or target index."""

    to: Move | int


class Ordered:
    """A row that sits in an explicit place among its siblings.

    Siblings are ordered contiguously from 0 and rewritten whenever the order
    changes, so positions are countable rather than inferred from gaps.
    """

    order: Mapped[int] = mapped_column()


def reorder[RowT: Ordered](rows: list[RowT], row: RowT, to: Move | int) -> list[RowT]:
    """`rows` with `row` sent where `to` says, renumbered from 0.

    `to` can be:
    - Move.TOP: jump to index 0
    - Move.BOTTOM: jump to index len(rows) - 1
    - int: absolute target index, clamped to [0, len(rows) - 1]

    A move to the current position or past either end is not an error:
    the row stays or is clamped to boundary, and the renumbered list is returned.
    """
    was = rows.index(row)
    if isinstance(to, Move):
        now = 0 if to == Move.TOP else len(rows) - 1
    else:
        now = max(0, min(to, len(rows) - 1))

    if was != now:
        rows.insert(now, rows.pop(was))
        renumber(rows)
    return rows


def renumber(rows: Sequence[Ordered]) -> None:
    for position, row in enumerate(rows):
        row.order = position
