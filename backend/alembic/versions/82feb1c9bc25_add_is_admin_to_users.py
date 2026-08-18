"""add is_admin to users

Adds `User.is_admin` (default False), required by the Admin Panel module's
`get_current_admin_user` gate — `app/models/user.py` did not have a role
flag until now.

Revision ID: 82feb1c9bc25
Revises: 6ee5ae0e1446
Create Date: 2026-07-28 23:09:20.661665

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "82feb1c9bc25"
down_revision: str | Sequence[str] | None = "6ee5ae0e1446"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Drop the server_default after backfilling existing rows so future
    # inserts rely on the ORM-level default instead of a DB-level one.
    op.alter_column("users", "is_admin", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_admin")
