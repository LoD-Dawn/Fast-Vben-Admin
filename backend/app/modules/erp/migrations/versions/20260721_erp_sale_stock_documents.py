"""Create ERP sale shipment and return documents.

Revision ID: erp_sale_stock_documents
Revises: erp_purchase_stock_documents
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_sale_stock_documents"
down_revision = "erp_purchase_stock_documents"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "sale_out",
    "sale_out_item",
    "sale_return",
    "sale_return_item",
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
    sale_out_columns = document_columns(source_column="sale_order_id", source_target="erp.sale_order.id")
    sale_out_columns[3:3] = [
        sa.Column("sale_order_no", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=False),
    ]
    sale_out_columns.extend(
        [
            sa.ForeignKeyConstraint(["customer_id", "tenant_id"], ["erp.customer.id", "erp.customer.tenant_id"], ondelete="RESTRICT"),
            sa.CheckConstraint("version > 0", name="ck_erp_sale_out_version"),
            sa.CheckConstraint("total_quantity > 0", name="ck_erp_sale_out_quantity"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "no", name="uq_erp_sale_out_tenant_no"),
            sa.UniqueConstraint("id", "tenant_id", name="uq_erp_sale_out_id_tenant_id"),
        ]
    )
    op.create_table("sale_out", *sale_out_columns, schema="erp")
    for column in ("tenant_id", "sale_order_id", "customer_id", "owner_id", "business_at"):
        op.create_index(f"ix_erp_sale_out_{column}", "sale_out", [column], schema="erp")

    op.create_table(
        "sale_out_item",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("sale_out_id", sa.Uuid(), nullable=False), sa.Column("sale_order_item_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False), sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False), sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("unit_name", sa.String(100), nullable=False), sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("reference_price", sa.Numeric(20, 4), nullable=False), sa.Column("returned_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["sale_out_id", "tenant_id"], ["erp.sale_out.id", "erp.sale_out.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_order_item_id"], ["erp.sale_order_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_erp_sale_out_item_quantity"),
        sa.CheckConstraint("returned_quantity >= 0 AND returned_quantity <= quantity", name="ck_erp_sale_out_item_returned_quantity"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("sale_out_id", "line_no", name="uq_erp_sale_out_item_line"),
        sa.UniqueConstraint("sale_out_id", "sale_order_item_id", name="uq_erp_sale_out_item_order_line"), schema="erp",
    )
    for column in ("tenant_id", "sale_out_id", "sale_order_item_id", "product_id", "warehouse_id"):
        op.create_index(f"ix_erp_sale_out_item_{column}", "sale_out_item", [column], schema="erp")

    sale_return_columns = document_columns(source_column="sale_out_id", source_target="erp.sale_out.id")
    sale_return_columns[3:3] = [
        sa.Column("sale_out_no", sa.String(32), nullable=False),
        sa.Column("sale_order_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=False),
    ]
    sale_return_columns.extend(
        [
            sa.ForeignKeyConstraint(["sale_order_id", "tenant_id"], ["erp.sale_order.id", "erp.sale_order.tenant_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["customer_id", "tenant_id"], ["erp.customer.id", "erp.customer.tenant_id"], ondelete="RESTRICT"),
            sa.CheckConstraint("version > 0", name="ck_erp_sale_return_version"),
            sa.CheckConstraint("total_quantity > 0", name="ck_erp_sale_return_quantity"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "no", name="uq_erp_sale_return_tenant_no"),
            sa.UniqueConstraint("id", "tenant_id", name="uq_erp_sale_return_id_tenant_id"),
        ]
    )
    op.create_table("sale_return", *sale_return_columns, schema="erp")
    for column in ("tenant_id", "sale_out_id", "sale_order_id", "customer_id", "owner_id", "business_at"):
        op.create_index(f"ix_erp_sale_return_{column}", "sale_return", [column], schema="erp")

    op.create_table(
        "sale_return_item",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("sale_return_id", sa.Uuid(), nullable=False), sa.Column("sale_out_item_id", sa.Uuid(), nullable=False),
        sa.Column("sale_order_item_id", sa.Uuid(), nullable=False), sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False), sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False), sa.Column("unit_name", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False), sa.Column("reference_price", sa.Numeric(20, 4), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["sale_return_id", "tenant_id"], ["erp.sale_return.id", "erp.sale_return.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_out_item_id"], ["erp.sale_out_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sale_order_item_id"], ["erp.sale_order_item.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id", "tenant_id"], ["erp.product.id", "erp.product.tenant_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id", "tenant_id"], ["erp.warehouse.id", "erp.warehouse.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("quantity > 0", name="ck_erp_sale_return_item_quantity"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("sale_return_id", "line_no", name="uq_erp_sale_return_item_line"),
        sa.UniqueConstraint("sale_return_id", "sale_out_item_id", name="uq_erp_sale_return_item_out_line"), schema="erp",
    )
    for column in ("tenant_id", "sale_return_id", "sale_out_item_id", "sale_order_item_id", "product_id", "warehouse_id"):
        op.create_index(f"ix_erp_sale_return_item_{column}", "sale_return_item", [column], schema="erp")
    for table in TENANT_TABLES:
        enable_tenant_rls(table)


def downgrade() -> None:
    for table in ("sale_return_item", "sale_return", "sale_out_item", "sale_out"):
        op.drop_table(table, schema="erp")
