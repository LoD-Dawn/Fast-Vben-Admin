"""add oauth2 social management

Revision ID: f3a4b5c6d7e8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth2client",
        sa.Column("client_id", sa.String(length=100), nullable=False),
        sa.Column("client_secret", sa.String(length=500), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("logo", sa.String(length=500), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("access_token_validity_seconds", sa.Integer(), nullable=False),
        sa.Column("refresh_token_validity_seconds", sa.Integer(), nullable=False),
        sa.Column("authorized_grant_types", sa.String(length=500), nullable=False),
        sa.Column("scopes", sa.String(length=500), nullable=True),
        sa.Column("auto_approve_scopes", sa.String(length=500), nullable=True),
        sa.Column("redirect_uris", sa.String(length=1000), nullable=True),
        sa.Column("authorities", sa.String(length=500), nullable=True),
        sa.Column("resource_ids", sa.String(length=500), nullable=True),
        sa.Column("additional_information", sa.String(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oauth2client_client_id"),
        "oauth2client",
        ["client_id"],
        unique=True,
    )

    op.create_table(
        "socialclient",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("social_type", sa.String(length=50), nullable=False),
        sa.Column("user_type", sa.String(length=50), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret", sa.String(length=500), nullable=True),
        sa.Column("agent_id", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "social_type",
            "user_type",
            name="uq_socialclient_social_type_user_type",
        ),
    )
    op.create_index(
        op.f("ix_socialclient_social_type"),
        "socialclient",
        ["social_type"],
        unique=False,
    )

    op.create_table(
        "oauth2accesstoken",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("access_token", sa.String(length=500), nullable=False),
        sa.Column("refresh_token", sa.String(length=500), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("user_full_name", sa.String(length=255), nullable=True),
        sa.Column("client_id", sa.String(length=100), nullable=False),
        sa.Column("scopes", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oauth2accesstoken_access_token"),
        "oauth2accesstoken",
        ["access_token"],
        unique=True,
    )
    op.create_index(
        op.f("ix_oauth2accesstoken_client_id"),
        "oauth2accesstoken",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth2accesstoken_refresh_token"),
        "oauth2accesstoken",
        ["refresh_token"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth2accesstoken_user_id"),
        "oauth2accesstoken",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "socialuser",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("openid", sa.String(length=255), nullable=False),
        sa.Column("unionid", sa.String(length=255), nullable=True),
        sa.Column("nickname", sa.String(length=255), nullable=True),
        sa.Column("avatar", sa.String(length=500), nullable=True),
        sa.Column("token", sa.String(length=1000), nullable=True),
        sa.Column("raw_token_info", sa.String(length=4000), nullable=True),
        sa.Column("raw_user_info", sa.String(length=4000), nullable=True),
        sa.Column("code", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("social_client_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["social_client_id"],
            ["socialclient.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type", "openid", name="uq_socialuser_type_openid"),
    )
    op.create_index(op.f("ix_socialuser_openid"), "socialuser", ["openid"])
    op.create_index(
        op.f("ix_socialuser_social_client_id"),
        "socialuser",
        ["social_client_id"],
    )
    op.create_index(op.f("ix_socialuser_type"), "socialuser", ["type"])
    op.create_index(op.f("ix_socialuser_user_id"), "socialuser", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_socialuser_user_id"), table_name="socialuser")
    op.drop_index(op.f("ix_socialuser_type"), table_name="socialuser")
    op.drop_index(op.f("ix_socialuser_social_client_id"), table_name="socialuser")
    op.drop_index(op.f("ix_socialuser_openid"), table_name="socialuser")
    op.drop_table("socialuser")
    op.drop_index(op.f("ix_oauth2accesstoken_user_id"), table_name="oauth2accesstoken")
    op.drop_index(
        op.f("ix_oauth2accesstoken_refresh_token"),
        table_name="oauth2accesstoken",
    )
    op.drop_index(
        op.f("ix_oauth2accesstoken_client_id"),
        table_name="oauth2accesstoken",
    )
    op.drop_index(
        op.f("ix_oauth2accesstoken_access_token"),
        table_name="oauth2accesstoken",
    )
    op.drop_table("oauth2accesstoken")
    op.drop_index(op.f("ix_socialclient_social_type"), table_name="socialclient")
    op.drop_table("socialclient")
    op.drop_index(op.f("ix_oauth2client_client_id"), table_name="oauth2client")
    op.drop_table("oauth2client")
