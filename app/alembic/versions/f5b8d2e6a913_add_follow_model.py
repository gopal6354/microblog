"""add follow model

Revision ID: f5b8d2e6a913
Revises: e1a4c7b92d10
Create Date: 2026-10-26 12:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f5b8d2e6a913"
down_revision: Union[str, Sequence[str], None] = "e1a4c7b92d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "follows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followed_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["followed_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("follower_id", "followed_id", name="uq_follower_followed"),
        sa.CheckConstraint("follower_id != followed_id", name="ck_no_self_follow"),
    )
    op.create_index("ix_follows_followed_id", "follows", ["followed_id"])


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_follows_followed_id", table_name="follows")
    op.drop_table("follows")
