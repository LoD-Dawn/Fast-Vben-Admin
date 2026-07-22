"""Add operational product master-data fields.

Revision ID: erp_product_operational_fields
Revises: erp_warehouse_defaults
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_product_operational_fields"
down_revision = "erp_warehouse_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "product",
        sa.Column("weight", sa.Numeric(precision=20, scale=6), nullable=False, server_default="0"),
        schema="erp",
    )
    op.add_column(
        "product",
        sa.Column("expiry_days", sa.Integer(), nullable=False, server_default="0"),
        schema="erp",
    )
    op.add_column("product", sa.Column("remark", sa.String(500), nullable=True), schema="erp")
    op.create_check_constraint("ck_erp_product_weight", "product", "weight >= 0", schema="erp")
    op.create_check_constraint("ck_erp_product_expiry_days", "product", "expiry_days >= 0", schema="erp")
    op.alter_column("product", "weight", server_default=None, schema="erp")
    op.alter_column("product", "expiry_days", server_default=None, schema="erp")


def downgrade() -> None:
    op.drop_constraint("ck_erp_product_expiry_days", "product", schema="erp")
    op.drop_constraint("ck_erp_product_weight", "product", schema="erp")
    op.drop_column("product", "remark", schema="erp")
    op.drop_column("product", "expiry_days", schema="erp")
    op.drop_column("product", "weight", schema="erp")
