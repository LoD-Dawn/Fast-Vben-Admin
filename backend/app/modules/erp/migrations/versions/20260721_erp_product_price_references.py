"""Add ERP product reference pricing.

Revision ID: erp_product_price_references
Revises: erp_purchase_orders
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_product_price_references"
down_revision = "erp_purchase_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        "purchase_reference_price",
        "sale_reference_price",
        "min_sale_price",
    ):
        op.add_column(
            "product",
            sa.Column(column, sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
            schema="erp",
        )
        op.create_check_constraint(
            f"ck_erp_product_{column}",
            "product",
            f"{column} >= 0",
            schema="erp",
        )
    op.alter_column("product", "purchase_reference_price", server_default=None, schema="erp")
    op.alter_column("product", "sale_reference_price", server_default=None, schema="erp")
    op.alter_column("product", "min_sale_price", server_default=None, schema="erp")


def downgrade() -> None:
    for column in ("min_sale_price", "sale_reference_price", "purchase_reference_price"):
        op.drop_column("product", column, schema="erp")
