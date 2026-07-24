"""add moderation action to report

Revision ID: ceb91a4eb780
Revises: 4f5c46cb64c4
Create Date: 2026-07-24 10:14:48.534655

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ceb91a4eb780"
down_revision: Union[str, Sequence[str], None] = "4f5c46cb64c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

moderation_action = postgresql.ENUM(
    "NONE",
    "BLOG_SOFT_DELETED",
    "BLOG_HARD_DELETED",
    "AUTHOR_SUSPENDED",
    "AUTHOR_DELETED",
    name="moderationaction",
)


def upgrade() -> None:
    moderation_action.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "reports",
        sa.Column(
            "action",
            moderation_action,
            nullable=False,
            server_default="NONE",
        ),
    )

    op.alter_column(
        "reports",
        "action",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("reports", "action")
    moderation_action.drop(op.get_bind(), checkfirst=True)
