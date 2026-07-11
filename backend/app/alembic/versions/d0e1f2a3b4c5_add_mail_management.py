"""add mail management

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mailaccount",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password", sa.String(length=500), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("ssl_enable", sa.Boolean(), nullable=False),
        sa.Column("starttls_enable", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mailaccount_code"), "mailaccount", ["code"], unique=True)

    op.create_table(
        "mailtemplate",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("nickname", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.String(length=20_000), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_code", sa.String(length=100), nullable=True),
        sa.Column("params", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["mailaccount.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mailtemplate_code"), "mailtemplate", ["code"], unique=True)
    op.create_index("ix_mailtemplate_account_id", "mailtemplate", ["account_id"])

    op.create_table(
        "maillog",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("account_code", sa.String(length=100), nullable=True),
        sa.Column("account_name", sa.String(length=100), nullable=True),
        sa.Column("template_id", sa.UUID(), nullable=True),
        sa.Column("template_code", sa.String(length=100), nullable=True),
        sa.Column("template_name", sa.String(length=100), nullable=True),
        sa.Column("from_email", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=100), nullable=True),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.String(length=20_000), nullable=False),
        sa.Column("template_params", sa.String(length=4000), nullable=True),
        sa.Column("send_status", sa.String(length=20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("send_code", sa.String(length=100), nullable=True),
        sa.Column("send_message", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["mailaccount.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["mailtemplate.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_maillog_to_email"), "maillog", ["to_email"])
    op.create_index("ix_maillog_created_at", "maillog", ["created_at"])
    op.create_index("ix_maillog_sent_at", "maillog", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_maillog_sent_at", table_name="maillog")
    op.drop_index("ix_maillog_created_at", table_name="maillog")
    op.drop_index(op.f("ix_maillog_to_email"), table_name="maillog")
    op.drop_table("maillog")
    op.drop_index("ix_mailtemplate_account_id", table_name="mailtemplate")
    op.drop_index(op.f("ix_mailtemplate_code"), table_name="mailtemplate")
    op.drop_table("mailtemplate")
    op.drop_index(op.f("ix_mailaccount_code"), table_name="mailaccount")
    op.drop_table("mailaccount")
