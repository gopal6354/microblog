"""add is_hidden boolean field in blog model

Revision ID: 7f0085d69349
Revises: ceb91a4eb780
Create Date: 2026-07-24 12:09:28.814850
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f0085d69349"
down_revision: Union[str, Sequence[str], None] = "ceb91a4eb780"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "blogs",
        sa.Column(
            "is_hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.alter_column(
        "blogs",
        "is_hidden",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("blogs", "is_hidden")
