"""Explicit ordering among siblings. Shared between Evidence and Bookmark."""

from collections.abc import Sequence
from enum import StrEnum

from sqlalchemy.orm import Mapped, mapped_column


class Move(StrEnum):
    """Where a row is being sent among its siblings. Not a drag: four buttons.

    Up and down are the everyday correction; top and bottom exist because
    walking something up eight places one click at a time is not reordering, it
    is clicking (design.md §6 F5).
    """

    UP = "up"
    DOWN = "down"
    TOP = "top"
    BOTTOM = "bottom"


class Ordered:
    """A row that sits in an explicit place among its siblings.

    Siblings are ordered contiguously from 0 and rewritten whenever the order
    changes, so positions are countable rather than inferred from gaps.
    """

    order: Mapped[int] = mapped_column()


def reorder[RowT: Ordered](rows: list[RowT], row: RowT, to: Move) -> list[RowT]:
    """`rows` with `row` sent where `to` says, renumbered from 0.

    A move off either end is not an error and not a different kind of answer:
    the row was already there, so this is the same list back.
    """
    was = rows.index(row)
    now = {
        Move.UP: was - 1,
        Move.DOWN: was + 1,
        Move.TOP: 0,
        Move.BOTTOM: len(rows) - 1,
    }[to]
    if 0 <= now < len(rows):
        rows.insert(now, rows.pop(was))
        renumber(rows)
    return rows


def renumber(rows: Sequence[Ordered]) -> None:
    for position, row in enumerate(rows):
        row.order = position
