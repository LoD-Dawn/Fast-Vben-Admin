"""Protect supplier and customer bank accounts at rest.

Revision ID: erp_counterparty_bank_accounts
Revises: erp_reconciliation_control
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_counterparty_bank_accounts"
down_revision = "erp_reconciliation_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("supplier", "customer"):
        op.add_column(
            table,
            sa.Column("bank_account_encrypted", sa.String(1000), nullable=True),
            schema="erp",
        )
        op.add_column(
            table,
            sa.Column("bank_account_last4", sa.String(4), nullable=True),
            schema="erp",
        )


def downgrade() -> None:
    for table in ("supplier", "customer"):
        op.drop_column(table, "bank_account_last4", schema="erp")
        op.drop_column(table, "bank_account_encrypted", schema="erp")
