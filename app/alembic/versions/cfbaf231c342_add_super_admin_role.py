"""add super admin role

Revision ID: cfbaf231c342
Revises: 19ca27ec29f2
Create Date: 2026-07-22 10:29:35.116721

"""

from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "cfbaf231c342"
down_revision: Union[str, Sequence[str], None] = "19ca27ec29f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
