"""add enterprise oidc models

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-07-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8e9f0a1b2c3"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enterpriseoidcauthorizationstate",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_enterpriseoidcauthorizationstate_state_hash"),
        "enterpriseoidcauthorizationstate",
        ["state_hash"],
        unique=True,
    )
    op.create_table(
        "enterpriseoidcidentity",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "subject", name="uq_enterpriseoidcidentity_provider_subject"),
    )
    op.create_index(
        op.f("ix_enterpriseoidcidentity_user_id"),
        "enterpriseoidcidentity",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "enterpriseoidcloginticket",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ticket_hash", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_enterpriseoidcloginticket_ticket_hash"),
        "enterpriseoidcloginticket",
        ["ticket_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_enterpriseoidcloginticket_user_id"),
        "enterpriseoidcloginticket",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_enterpriseoidcloginticket_user_id"),
        table_name="enterpriseoidcloginticket",
    )
    op.drop_index(
        op.f("ix_enterpriseoidcloginticket_ticket_hash"),
        table_name="enterpriseoidcloginticket",
    )
    op.drop_table("enterpriseoidcloginticket")
    op.drop_index(
        op.f("ix_enterpriseoidcidentity_user_id"), table_name="enterpriseoidcidentity"
    )
    op.drop_table("enterpriseoidcidentity")
    op.drop_index(
        op.f("ix_enterpriseoidcauthorizationstate_state_hash"),
        table_name="enterpriseoidcauthorizationstate",
    )
    op.drop_table("enterpriseoidcauthorizationstate")
