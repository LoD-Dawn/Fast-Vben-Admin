"""Create ERP purchase receipt and return documents.

Revision ID: erp_purchase_stock_documents
Revises: erp_sale_orders
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_purchase_stock_documents"
down_revision = "erp_sale_orders"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "purchase_in",
    "purchase_in_item",
    "purchase_return",
    "purchase_return_item",
)


def enable_tenant_rls(table: str) -> None:
    policy = f"erp_{table}_tenant_isolation"
    op.execute(f"ALTER TABLE erp.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE erp.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {policy} ON erp.{table} "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def document_columns(*, source_column: str, source_target: str) -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("no", sa.String(32), nullable=False),
        sa.Column(source_column, sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("business_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("total_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.Uuid(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint([source_column, "tenant_id"], [source_target, source_target.replace(".id", ".tenant_id")], ondelete="RESTRICT"),
    ]


def upgrade() -> None:
    purchase_in_columns = document_columns(source_column="purchase_order_id", source_target="erp.purchase_order.id")
    purchase_in_columns[3:3] = [
        sa.Column("purchase_order_no", sa.String(32), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_name", sa.String(200), nullable=False),
    ]
    purchase_in_columns.extend(
        [
            sa.ForeignKeyConstraint(["supplier_id", "tenant_id"], ["erp.supplier.id", "erp.supplier.tenant_id"], ondelete="RESTRICT"),
            sa.CheckConstraint("version > 0", name="ck_erp_purchase_in_version"),
            sa.CheckConstraint("total_quantity > 0", name="ck_erp_purchase_in_quantity"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "no", name="uq_erp_purchase_in_tenant_no"),
            sa.UniqueConstraint("id", "tenant_id", name="uq_erp_purchase_in_id_tenant_id"),
        ]
    )
    op.create_table("purchase_in", *purchase_in_columns, schema="erp")
    for column in ("tenant_id", "purchase_order_id", "supplier_id", "owner_id", "business_at"):
        op.create_index(f"ix_erp_purchase_in_{column}", "purchase_in", [column], schema="erp")

    op.create_table(
        "purchase_in_item",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_in_id", sa.Uuid(), nullable=False), sa.Column("purchase_order_item_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False), sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False), sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("unit_name", sa.String(100), nullable=False), sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("reference_price", sa.Numeric(20, 4), nullable=False), sa.Column("returned_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["purchase_in_id", "tenant_id"], ["erp.purchase_in.id", "erp.purchase_in.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_order_item_id"], ["erp.purchase_order_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_erp_purchase_in_item_quantity"),
        sa.CheckConstraint("returned_quantity >= 0 AND returned_quantity <= quantity", name="ck_erp_purchase_in_item_returned_quantity"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("purchase_in_id", "line_no", name="uq_erp_purchase_in_item_line"),
        sa.UniqueConstraint("purchase_in_id", "purchase_order_item_id", name="uq_erp_purchase_in_item_order_line"), schema="erp",
    )
    for column in ("tenant_id", "purchase_in_id", "purchase_order_item_id", "product_id", "warehouse_id"):
        op.create_index(f"ix_erp_purchase_in_item_{column}", "purchase_in_item", [column], schema="erp")

    purchase_return_columns = document_columns(source_column="purchase_in_id", source_target="erp.purchase_in.id")
    purchase_return_columns[3:3] = [
        sa.Column("purchase_in_no", sa.String(32), nullable=False),
        sa.Column("purchase_order_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_name", sa.String(200), nullable=False),
    ]
    purchase_return_columns.extend(
        [
            sa.ForeignKeyConstraint(["purchase_order_id", "tenant_id"], ["erp.purchase_order.id", "erp.purchase_order.tenant_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["supplier_id", "tenant_id"], ["erp.supplier.id", "erp.supplier.tenant_id"], ondelete="RESTRICT"),
            sa.CheckConstraint("version > 0", name="ck_erp_purchase_return_version"),
            sa.CheckConstraint("total_quantity > 0", name="ck_erp_purchase_return_quantity"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "no", name="uq_erp_purchase_return_tenant_no"),
            sa.UniqueConstraint("id", "tenant_id", name="uq_erp_purchase_return_id_tenant_id"),
        ]
    )
    op.create_table("purchase_return", *purchase_return_columns, schema="erp")
    for column in ("tenant_id", "purchase_in_id", "purchase_order_id", "supplier_id", "owner_id", "business_at"):
        op.create_index(f"ix_erp_purchase_return_{column}", "purchase_return", [column], schema="erp")

    op.create_table(
        "purchase_return_item",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_return_id", sa.Uuid(), nullable=False), sa.Column("purchase_in_item_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_order_item_id", sa.Uuid(), nullable=False), sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False), sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False), sa.Column("unit_name", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False), sa.Column("reference_price", sa.Numeric(20, 4), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["purchase_return_id", "tenant_id"], ["erp.purchase_return.id", "erp.purchase_return.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_in_item_id"], ["erp.purchase_in_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_order_item_id"], ["erp.purchase_order_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_erp_purchase_return_item_quantity"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("purchase_return_id", "line_no", name="uq_erp_purchase_return_item_line"),
        sa.UniqueConstraint("purchase_return_id", "purchase_in_item_id", name="uq_erp_purchase_return_item_in_line"), schema="erp",
    )
    for column in ("tenant_id", "purchase_return_id", "purchase_in_item_id", "purchase_order_item_id", "product_id", "warehouse_id"):
        op.create_index(f"ix_erp_purchase_return_item_{column}", "purchase_return_item", [column], schema="erp")
    for table in TENANT_TABLES:
        enable_tenant_rls(table)


def downgrade() -> None:
    for table in ("purchase_return_item", "purchase_return", "purchase_in_item", "purchase_in"):
        op.drop_table(table, schema="erp")
