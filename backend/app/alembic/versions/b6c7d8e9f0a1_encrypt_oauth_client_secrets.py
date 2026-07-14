"""encrypt oauth and social client secrets

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-07-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.mfa import encrypt_secret

revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _encrypt_column(table_name: str) -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(f"SELECT id, client_secret FROM {table_name} WHERE client_secret IS NOT NULL")
    ).mappings()
    for row in rows:
        connection.execute(
            sa.text(f"UPDATE {table_name} SET client_secret = :client_secret WHERE id = :id"),
            {"id": row["id"], "client_secret": encrypt_secret(row["client_secret"])},
        )


def upgrade() -> None:
    _encrypt_column("oauth2client")
    _encrypt_column("socialclient")


def downgrade() -> None:
    # Secrets are deliberately not decrypted during rollback.
    pass
