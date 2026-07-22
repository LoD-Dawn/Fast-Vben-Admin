"""Create ERP purchase order headers and lines.

Revision ID: erp_purchase_orders
Revises: erp_document_sequence
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_purchase_orders"
down_revision = "erp_document_sequence"
branch_labels = None
depends_on = None

TENANT_TABLES = ("purchase_order", "purchase_order_item")


def enable_tenant_rls(table: str) -> None:
    policy = f"erp_{table}_tenant_isolation"
    op.execute(f"ALTER TABLE erp.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE erp.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {policy} ON erp.{table}
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "purchase_order",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("no", sa.String(length=32), nullable=False), sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_name", sa.String(length=200), nullable=False), sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("business_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False), sa.Column("total_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("product_amount", sa.Numeric(20, 4), nullable=False), sa.Column("tax_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("discount_rate", sa.Numeric(7, 4), nullable=False), sa.Column("discount_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("deposit_amount", sa.Numeric(20, 4), nullable=False), sa.Column("total_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=True), sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False), sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True), sa.Column("reversed_by", sa.Uuid(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id", "tenant_id"], ["erp.supplier.id", "erp.supplier.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("version > 0", name="ck_erp_purchase_order_version"), sa.CheckConstraint("total_quantity > 0", name="ck_erp_purchase_order_quantity"),
        sa.CheckConstraint("product_amount >= 0", name="ck_erp_purchase_order_product_amount"), sa.CheckConstraint("tax_amount >= 0", name="ck_erp_purchase_order_tax_amount"),
        sa.CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_erp_purchase_order_discount_rate"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_erp_purchase_order_discount_amount"), sa.CheckConstraint("deposit_amount >= 0", name="ck_erp_purchase_order_deposit_amount"),
        sa.CheckConstraint("total_amount >= 0", name="ck_erp_purchase_order_total_amount"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("tenant_id", "no", name="uq_erp_purchase_order_tenant_no"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_erp_purchase_order_id_tenant_id"), schema="erp",
    )
    for column in ("tenant_id", "supplier_id", "owner_id", "business_at"):
        op.create_index(f"ix_erp_purchase_order_{column}", "purchase_order", [column], schema="erp")
    op.create_table(
        "purchase_order_item",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_order_id", sa.Uuid(), nullable=False), sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False), sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False), sa.Column("product_barcode", sa.String(length=100), nullable=True),
        sa.Column("unit_name", sa.String(length=100), nullable=False), sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(20, 4), nullable=False), sa.Column("product_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("tax_rate", sa.Numeric(7, 4), nullable=False), sa.Column("tax_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("total_amount", sa.Numeric(20, 4), nullable=False), sa.Column("received_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("returned_quantity", sa.Numeric(20, 6), nullable=False), sa.Column("remark", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["purchase_order_id", "tenant_id"], ["erp.purchase_order.id", "erp.purchase_order.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id", "tenant_id"], ["erp.product_unit.id", "erp.product_unit.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_erp_purchase_order_item_quantity"), sa.CheckConstraint("unit_price >= 0", name="ck_erp_purchase_order_item_unit_price"),
        sa.CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_erp_purchase_order_item_tax_rate"),
        sa.CheckConstraint("received_quantity >= 0 AND received_quantity <= quantity", name="ck_erp_purchase_order_item_received_quantity"),
        sa.CheckConstraint("returned_quantity >= 0 AND returned_quantity <= received_quantity", name="ck_erp_purchase_order_item_returned_quantity"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("purchase_order_id", "line_no", name="uq_erp_purchase_order_item_line"), schema="erp",
    )
    for column in ("tenant_id", "purchase_order_id", "product_id", "unit_id"):
        op.create_index(f"ix_erp_purchase_order_item_{column}", "purchase_order_item", [column], schema="erp")
    for table in TENANT_TABLES:
        enable_tenant_rls(table)


def downgrade() -> None:
    op.drop_table("purchase_order_item", schema="erp")
    op.drop_table("purchase_order", schema="erp")
