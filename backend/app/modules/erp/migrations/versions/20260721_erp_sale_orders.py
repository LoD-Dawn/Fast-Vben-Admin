"""Create ERP sale order headers and lines.

Revision ID: erp_sale_orders
Revises: erp_product_price_references
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_sale_orders"
down_revision = "erp_product_price_references"
branch_labels = None
depends_on = None


def rls(table: str) -> None:
    op.execute(f"ALTER TABLE erp.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE erp.{table} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY erp_{table}_tenant_isolation ON erp.{table} USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)")


def upgrade() -> None:
    op.create_table(
        "sale_order",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False), sa.Column("no", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False), sa.Column("customer_name", sa.String(200), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("business_at", sa.DateTime(timezone=True), nullable=False), sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("total_quantity", sa.Numeric(20, 6), nullable=False), sa.Column("product_amount", sa.Numeric(20, 4), nullable=False), sa.Column("tax_amount", sa.Numeric(20, 4), nullable=False), sa.Column("discount_rate", sa.Numeric(7, 4), nullable=False), sa.Column("discount_amount", sa.Numeric(20, 4), nullable=False), sa.Column("deposit_amount", sa.Numeric(20, 4), nullable=False), sa.Column("total_amount", sa.Numeric(20, 4), nullable=False), sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("updated_by", sa.Uuid(), nullable=False), sa.Column("approved_by", sa.Uuid(), nullable=True), sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True), sa.Column("reversed_by", sa.Uuid(), nullable=True), sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=True), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id", "tenant_id"], ["erp.customer.id", "erp.customer.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("version > 0", name="ck_erp_sale_order_version"), sa.CheckConstraint("total_quantity > 0", name="ck_erp_sale_order_quantity"), sa.CheckConstraint("product_amount >= 0", name="ck_erp_sale_order_product_amount"), sa.CheckConstraint("tax_amount >= 0", name="ck_erp_sale_order_tax_amount"), sa.CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_sale_order_discount_rate"), sa.CheckConstraint("discount_amount >= 0", name="ck_erp_sale_order_discount_amount"), sa.CheckConstraint("deposit_amount >= 0", name="ck_erp_sale_order_deposit_amount"), sa.CheckConstraint("total_amount >= 0", name="ck_erp_sale_order_total_amount"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("tenant_id", "no", name="uq_erp_sale_order_tenant_no"), sa.UniqueConstraint("id", "tenant_id", name="uq_erp_sale_order_id_tenant_id"), schema="erp")
    for column in ("tenant_id", "customer_id", "owner_id", "business_at"):
        op.create_index(f"ix_erp_sale_order_{column}", "sale_order", [column], schema="erp")
    op.create_table(
        "sale_order_item",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False), sa.Column("sale_order_id", sa.Uuid(), nullable=False), sa.Column("line_no", sa.Integer(), nullable=False), sa.Column("product_id", sa.Uuid(), nullable=False), sa.Column("unit_id", sa.Uuid(), nullable=False), sa.Column("product_name", sa.String(200), nullable=False), sa.Column("product_barcode", sa.String(100), nullable=True), sa.Column("unit_name", sa.String(100), nullable=False), sa.Column("quantity", sa.Numeric(20, 6), nullable=False), sa.Column("unit_price", sa.Numeric(20, 4), nullable=False), sa.Column("product_amount", sa.Numeric(20, 4), nullable=False), sa.Column("tax_rate", sa.Numeric(7, 4), nullable=False), sa.Column("tax_amount", sa.Numeric(20, 4), nullable=False), sa.Column("total_amount", sa.Numeric(20, 4), nullable=False), sa.Column("shipped_quantity", sa.Numeric(20, 6), nullable=False), sa.Column("returned_quantity", sa.Numeric(20, 6), nullable=False), sa.Column("remark", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["sale_order_id", "tenant_id"], ["erp.sale_order.id", "erp.sale_order.tenant_id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["unit_id", "tenant_id"], ["erp.product_unit.id", "erp.product_unit.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_erp_sale_order_item_quantity"), sa.CheckConstraint("unit_price >= 0", name="ck_erp_sale_order_item_unit_price"), sa.CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_sale_order_item_tax_rate"), sa.CheckConstraint("shipped_quantity >= 0 AND shipped_quantity <= quantity", name="ck_erp_sale_order_item_shipped_quantity"), sa.CheckConstraint("returned_quantity >= 0 AND returned_quantity <= shipped_quantity", name="ck_erp_sale_order_item_returned_quantity"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("sale_order_id", "line_no", name="uq_erp_sale_order_item_line"), schema="erp")
    for column in ("tenant_id", "sale_order_id", "product_id", "unit_id"):
        op.create_index(f"ix_erp_sale_order_item_{column}", "sale_order_item", [column], schema="erp")
    rls("sale_order")
    rls("sale_order_item")


def downgrade() -> None:
    op.drop_table("sale_order_item", schema="erp")
    op.drop_table("sale_order", schema="erp")
