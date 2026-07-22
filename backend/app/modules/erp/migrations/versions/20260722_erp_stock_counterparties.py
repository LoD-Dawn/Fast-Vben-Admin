"""Add optional counterparties to other stock documents."""

import sqlalchemy as sa
from alembic import op

revision = "erp_stock_counterparties"
down_revision = "erp_product_category_required"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stock_in", sa.Column("supplier_id", sa.Uuid(), nullable=True), schema="erp")
    op.add_column("stock_out", sa.Column("customer_id", sa.Uuid(), nullable=True), schema="erp")
    op.create_index("ix_erp_stock_in_supplier_id", "stock_in", ["supplier_id"], schema="erp")
    op.create_index("ix_erp_stock_out_customer_id", "stock_out", ["customer_id"], schema="erp")


def downgrade() -> None:
    op.drop_index("ix_erp_stock_out_customer_id", table_name="stock_out", schema="erp")
    op.drop_index("ix_erp_stock_in_supplier_id", table_name="stock_in", schema="erp")
    op.drop_column("stock_out", "customer_id", schema="erp")
    op.drop_column("stock_in", "supplier_id", schema="erp")
