"""add image blocks

Revision ID: 20eeec31d51f
Revises: a6aca93cb37f
Create Date: 2026-09-08 12:39:36.037483

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20eeec31d51f'
down_revision: str | None = 'a6aca93cb37f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `server_default` is not in the model — new rows get their empty string
    # from Python. It is here because the blocks already written by ticket 04
    # have nothing to put in a NOT NULL column, and adding one without it
    # fails on any database that is not empty.
    with op.batch_alter_table('evidence_block', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('image_name', sa.Text(), nullable=False, server_default='')
        )


def downgrade() -> None:
    with op.batch_alter_table('evidence_block', schema=None) as batch_op:
        batch_op.drop_column('image_name')
