"""add location to blogs

Revision ID: c73fa9210d5b
Revises: b62e9a1f3c40
Create Date: 2026-10-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c73fa9210d5b"
down_revision: Union[str, Sequence[str], None] = "b62e9a1f3c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("blogs", sa.Column("location", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("blogs", "location")
