"""track posts hidden by account suspension

Revision ID: a51d8c2e4f70
Revises: 927a0ac44218
Create Date: 2026-10-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a51d8c2e4f70"
down_revision: Union[str, Sequence[str], None] = "927a0ac44218"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "blogs",
        sa.Column(
            "hidden_by_suspension",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("blogs", "hidden_by_suspension", server_default=None)

    # Posts hidden for accounts already suspended were hidden by the existing
    # suspension flow, which hid every post belonging to the account.
    op.execute(
        sa.text(
            "UPDATE blogs SET hidden_by_suspension = TRUE "
            "FROM users WHERE blogs.user_id = users.id "
            "AND users.is_deleted = TRUE AND blogs.is_hidden = TRUE"
        )
    )


def downgrade() -> None:
    op.drop_column("blogs", "hidden_by_suspension")
