"""add_todo_description_and_drop_source_memo_id

Revision ID: d3e7b1a9c4f2
Revises: a1b2c3d4e5f6
Create Date: 2026-09-10 00:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e7b1a9c4f2"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add description column
    with op.batch_alter_table("todos", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("description", sa.Text(), nullable=False, server_default="")
        )

    # 2. Backfill description for todos that have an existing source_memo_id
    todos_table = sa.table(
        "todos",
        sa.column("id", sa.Integer),
        sa.column("source_memo_id", sa.Integer),
        sa.column("description", sa.Text),
    )
    memos_table = sa.table(
        "memos",
        sa.column("id", sa.Integer),
    )
    bind = op.get_bind()
    existing_memo_ids = {row[0] for row in bind.execute(sa.select(memos_table.c.id))}
    todo_rows = bind.execute(
        sa.select(
            todos_table.c.id, todos_table.c.source_memo_id, todos_table.c.description
        ).where(todos_table.c.source_memo_id.is_not(None))
    ).all()

    for todo_id, source_memo_id, desc in todo_rows:
        if source_memo_id in existing_memo_ids:
            link = f"[原 memo](/memo/{source_memo_id})"
            new_desc = f"{desc}\n\n{link}" if desc else link
            bind.execute(
                todos_table.update()
                .where(todos_table.c.id == todo_id)
                .values(description=new_desc)
            )

    # 3. Drop source_memo_id column and index
    with op.batch_alter_table("todos", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_todos_source_memo_id"))
        batch_op.drop_column("source_memo_id")


def downgrade() -> None:
    with op.batch_alter_table("todos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_memo_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_todos_source_memo_id"), ["source_memo_id"], unique=False
        )
        batch_op.drop_column("description")
