"""drop unique constraint on account activation email

Revision ID: d3e8b51a7c92
Revises: c73fa9210d5b
Create Date: 2026-10-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d3e8b51a7c92"
down_revision: Union[str, Sequence[str], None] = "c73fa9210d5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # a user may submit a new activation request after an earlier one is processed
    op.drop_constraint(
        "account_activations_email_key", "account_activations", type_="unique"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_unique_constraint(
        "account_activations_email_key", "account_activations", ["email"]
    )
