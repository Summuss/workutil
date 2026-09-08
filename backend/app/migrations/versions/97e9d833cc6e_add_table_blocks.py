"""add table blocks

Revision ID: 97e9d833cc6e
Revises: 20eeec31d51f
Create Date: 2026-09-08 13:26:24.213247

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '97e9d833cc6e'
down_revision: str | None = '20eeec31d51f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `server_default` is not in the model — new rows get their empty value
    # from Python. It is here for the same reason ticket 05's was: the blocks
    # already written have nothing to put in a NOT NULL column, and adding one
    # without a default fails on any database that is not empty.
    with op.batch_alter_table('evidence_block', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('rows', sa.JSON(), nullable=False, server_default='[]')
        )
        batch_op.add_column(
            sa.Column('has_header', sa.Boolean(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('table_source', sa.Text(), nullable=False, server_default='')
        )


def downgrade() -> None:
    with op.batch_alter_table('evidence_block', schema=None) as batch_op:
        batch_op.drop_column('table_source')
        batch_op.drop_column('has_header')
        batch_op.drop_column('rows')
