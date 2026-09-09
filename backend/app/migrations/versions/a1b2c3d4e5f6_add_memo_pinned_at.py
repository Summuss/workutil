"""add_memo_pinned_at

Revision ID: a1b2c3d4e5f6
Revises: e6d3dfcc041d
Create Date: 2026-09-09 17:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "e6d3dfcc041d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("memos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pinned_at", sa.DateTime(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_memos_pinned_at"), ["pinned_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("memos", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_memos_pinned_at"))
        batch_op.drop_column("pinned_at")
