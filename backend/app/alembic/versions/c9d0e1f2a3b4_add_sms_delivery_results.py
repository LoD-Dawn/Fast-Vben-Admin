"""add sms delivery results

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("smslog", sa.Column("template_type", sa.String(length=50), nullable=True))
    op.add_column(
        "smslog",
        sa.Column("api_template_id", sa.String(length=100), nullable=True),
    )
    op.add_column("smslog", sa.Column("api_serial_no", sa.String(length=100), nullable=True))
    op.add_column(
        "smslog",
        sa.Column(
            "receive_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("smslog", sa.Column("received_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "smslog",
        sa.Column("api_receive_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "smslog",
        sa.Column("api_receive_message", sa.String(length=1000), nullable=True),
    )
    op.alter_column("smslog", "receive_status", server_default=None)
    op.create_index("ix_smslog_api_request_id", "smslog", ["api_request_id"])


def downgrade() -> None:
    op.drop_index("ix_smslog_api_request_id", table_name="smslog")
    op.drop_column("smslog", "api_receive_message")
    op.drop_column("smslog", "api_receive_code")
    op.drop_column("smslog", "received_at")
    op.drop_column("smslog", "receive_status")
    op.drop_column("smslog", "api_serial_no")
    op.drop_column("smslog", "api_template_id")
    op.drop_column("smslog", "template_type")
