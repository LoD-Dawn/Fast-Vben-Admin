"""add sms management

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "smschannel",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("signature", sa.String(length=100), nullable=False),
        sa.Column("api_key", sa.String(length=500), nullable=True),
        sa.Column("api_secret", sa.String(length=500), nullable=True),
        sa.Column("callback_url", sa.String(length=500), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_smschannel_code"), "smschannel", ["code"], unique=True)

    op.create_table(
        "smstemplate",
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("content", sa.String(length=1000), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("api_template_id", sa.String(length=100), nullable=True),
        sa.Column("channel_id", sa.UUID(), nullable=True),
        sa.Column("channel_code", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("params", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["smschannel.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_smstemplate_code"), "smstemplate", ["code"], unique=True)
    op.create_index("ix_smstemplate_channel_id", "smstemplate", ["channel_id"])

    op.create_table(
        "smslog",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.UUID(), nullable=True),
        sa.Column("channel_code", sa.String(length=100), nullable=True),
        sa.Column("template_id", sa.UUID(), nullable=True),
        sa.Column("template_code", sa.String(length=100), nullable=True),
        sa.Column("template_name", sa.String(length=100), nullable=True),
        sa.Column("template_content", sa.String(length=1000), nullable=False),
        sa.Column("template_params", sa.String(length=2000), nullable=True),
        sa.Column("mobile", sa.String(length=32), nullable=False),
        sa.Column("send_status", sa.String(length=20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("api_send_code", sa.String(length=100), nullable=True),
        sa.Column("api_send_message", sa.String(length=1000), nullable=True),
        sa.Column("api_request_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["smschannel.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["smstemplate.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_smslog_mobile"), "smslog", ["mobile"])
    op.create_index("ix_smslog_created_at", "smslog", ["created_at"])
    op.create_index("ix_smslog_sent_at", "smslog", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_smslog_sent_at", table_name="smslog")
    op.drop_index("ix_smslog_created_at", table_name="smslog")
    op.drop_index(op.f("ix_smslog_mobile"), table_name="smslog")
    op.drop_table("smslog")
    op.drop_index("ix_smstemplate_channel_id", table_name="smstemplate")
    op.drop_index(op.f("ix_smstemplate_code"), table_name="smstemplate")
    op.drop_table("smstemplate")
    op.drop_index(op.f("ix_smschannel_code"), table_name="smschannel")
    op.drop_table("smschannel")
