"""add user mfa totp fields

Revision ID: f4a5b6c7d8e9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "user",
        sa.Column("mfa_secret_encrypted", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("mfa_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("user", "mfa_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("user", "mfa_confirmed_at")
    op.drop_column("user", "mfa_secret_encrypted")
    op.drop_column("user", "mfa_enabled")
