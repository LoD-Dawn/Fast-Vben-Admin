"""Add settlement totals to ERP purchase and sale stock documents.

Revision ID: erp_document_settlement_amounts
Revises: erp_settlement_accounts
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_document_settlement_amounts"
down_revision = "erp_settlement_accounts"
branch_labels = None
depends_on = None

TABLES = ("purchase_in", "purchase_return", "sale_out", "sale_return")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("total_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
            schema="erp",
        )
        op.add_column(
            table,
            sa.Column("settled_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
            schema="erp",
        )
        op.create_check_constraint(
            f"ck_erp_{table}_total_amount", table, "total_amount >= 0", schema="erp"
        )
        op.create_check_constraint(
            f"ck_erp_{table}_settled_amount", table, "settled_amount >= 0", schema="erp"
        )
        op.alter_column(table, "total_amount", server_default=None, schema="erp")
        op.alter_column(table, "settled_amount", server_default=None, schema="erp")


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "settled_amount", schema="erp")
        op.drop_column(table, "total_amount", schema="erp")
