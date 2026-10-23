"""add is_delete field in user model

Revision ID: 206888332232
Revises: 7f0085d69349
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "206888332232"
down_revision: Union[str, Sequence[str], None] = "7f0085d69349"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.alter_column(
        "users",
        "is_deleted",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("users", "is_deleted")
