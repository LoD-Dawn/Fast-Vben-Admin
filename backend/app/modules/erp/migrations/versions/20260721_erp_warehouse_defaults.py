"""Add ERP warehouse operational settings.

Revision ID: erp_warehouse_defaults
Revises: erp_counterparty_bank_accounts
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_warehouse_defaults"
down_revision = "erp_counterparty_bank_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "warehouse",
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        schema="erp",
    )
    op.add_column(
        "warehouse",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="erp",
    )
    op.add_column(
        "warehouse", sa.Column("remark", sa.String(500), nullable=True), schema="erp"
    )
    op.create_index(
        "uq_erp_warehouse_tenant_default",
        "warehouse",
        ["tenant_id"],
        unique=True,
        schema="erp",
        postgresql_where=sa.text("is_default"),
    )
    op.alter_column("warehouse", "sort", server_default=None, schema="erp")
    op.alter_column("warehouse", "is_default", server_default=None, schema="erp")


def downgrade() -> None:
    op.drop_index("uq_erp_warehouse_tenant_default", table_name="warehouse", schema="erp")
    op.drop_column("warehouse", "remark", schema="erp")
    op.drop_column("warehouse", "is_default", schema="erp")
    op.drop_column("warehouse", "sort", schema="erp")
