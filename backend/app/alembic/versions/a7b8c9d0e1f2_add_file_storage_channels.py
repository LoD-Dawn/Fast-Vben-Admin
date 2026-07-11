"""add file storage channels

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "filestoragechannel",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("endpoint_url", sa.String(length=500), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("bucket", sa.String(length=255), nullable=True),
        sa.Column("access_key_id", sa.String(length=255), nullable=True),
        sa.Column("secret_access_key", sa.String(length=500), nullable=True),
        sa.Column("object_prefix", sa.String(length=255), nullable=True),
        sa.Column("addressing_style", sa.String(length=20), nullable=False),
        sa.Column("auto_create_bucket", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_filestoragechannel_code"),
        "filestoragechannel",
        ["code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_filestoragechannel_code"), table_name="filestoragechannel")
    op.drop_table("filestoragechannel")
