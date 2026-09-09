"""add evidence block split_lines

Revision ID: f2a1b3c4d5e6
Revises: d3e7b1a9c4f2
Create Date: 2026-09-10 01:13:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a1b3c4d5e6"
down_revision: str | None = "d3e7b1a9c4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("evidence_block", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("split_lines", sa.Boolean(), nullable=False, server_default="1")
        )


def downgrade() -> None:
    with op.batch_alter_table("evidence_block", schema=None) as batch_op:
        batch_op.drop_column("split_lines")
