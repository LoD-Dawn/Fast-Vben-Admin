"""add oauth2 protocol models

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-07-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("oauth2accesstoken", "access_token", nullable=True)
    op.add_column(
        "oauth2accesstoken",
        sa.Column("access_token_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "oauth2accesstoken",
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "oauth2accesstoken",
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "oauth2accesstoken",
        sa.Column("token_family_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_oauth2accesstoken_access_token_hash"),
        "oauth2accesstoken",
        ["access_token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_oauth2accesstoken_refresh_token_hash"),
        "oauth2accesstoken",
        ["refresh_token_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth2accesstoken_token_family_id"),
        "oauth2accesstoken",
        ["token_family_id"],
        unique=False,
    )
    op.create_table(
        "oauth2authorizationcode",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("client_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("redirect_uri", sa.String(length=1000), nullable=False),
        sa.Column("scopes", sa.String(length=500), nullable=True),
        sa.Column("code_challenge", sa.String(length=128), nullable=False),
        sa.Column("code_challenge_method", sa.String(length=10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oauth2authorizationcode_code_hash"),
        "oauth2authorizationcode",
        ["code_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_oauth2authorizationcode_client_id"),
        "oauth2authorizationcode",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth2authorizationcode_user_id"),
        "oauth2authorizationcode",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_oauth2authorizationcode_user_id"), table_name="oauth2authorizationcode")
    op.drop_index(op.f("ix_oauth2authorizationcode_client_id"), table_name="oauth2authorizationcode")
    op.drop_index(op.f("ix_oauth2authorizationcode_code_hash"), table_name="oauth2authorizationcode")
    op.drop_table("oauth2authorizationcode")
    op.drop_index(op.f("ix_oauth2accesstoken_token_family_id"), table_name="oauth2accesstoken")
    op.drop_index(op.f("ix_oauth2accesstoken_refresh_token_hash"), table_name="oauth2accesstoken")
    op.drop_index(op.f("ix_oauth2accesstoken_access_token_hash"), table_name="oauth2accesstoken")
    op.drop_column("oauth2accesstoken", "token_family_id")
    op.drop_column("oauth2accesstoken", "refresh_expires_at")
    op.drop_column("oauth2accesstoken", "refresh_token_hash")
    op.drop_column("oauth2accesstoken", "access_token_hash")
    op.alter_column("oauth2accesstoken", "access_token", nullable=False)
