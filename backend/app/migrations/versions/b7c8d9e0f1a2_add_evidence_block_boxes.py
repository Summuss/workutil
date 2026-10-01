"""add evidence block boxes

Revision ID: b7c8d9e0f1a2
Revises: f2a1b3c4d5e6
Create Date: 2026-10-01 23:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "f2a1b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("evidence_block", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("boxes", sa.JSON(), nullable=False, server_default="[]")
        )


def downgrade() -> None:
    with op.batch_alter_table("evidence_block", schema=None) as batch_op:
        batch_op.drop_column("boxes")
