"""Create ERP stock move and stock check documents.

Revision ID: erp_stock_move_check
Revises: erp_stock_baseline
Create Date: 2026-07-20
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_stock_move_check"
down_revision = "erp_stock_baseline"
branch_labels = None
depends_on = None

TENANT_TABLES = ("stock_move", "stock_move_item", "stock_check", "stock_check_item")


def enable_tenant_rls(table: str) -> None:
    policy = f"erp_{table}_tenant_isolation"
    op.execute(f"ALTER TABLE erp.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE erp.{table} FORCE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {policy} ON erp.{table}")
    op.execute(
        f"""
        CREATE POLICY {policy} ON erp.{table}
        USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        )
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        )
        """
    )


def create_document_header(table: str) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("no", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("business_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("total_quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.Uuid(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("version > 0", name=f"ck_erp_{table}_version"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "no", name=f"uq_erp_{table}_tenant_no"),
        sa.UniqueConstraint("id", "tenant_id", name=f"uq_erp_{table}_id_tenant_id"),
        schema="erp",
    )
    op.create_index(f"ix_erp_{table}_tenant_id", table, ["tenant_id"], schema="erp")
    op.create_index(f"ix_erp_{table}_owner_id", table, ["owner_id"], schema="erp")
    op.create_index(f"ix_erp_{table}_business_at", table, ["business_at"], schema="erp")


def upgrade() -> None:
    create_document_header("stock_move")
    op.create_table(
        "stock_move_item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("stock_move_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("from_warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("to_warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("reference_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_erp_stock_move_item_quantity"),
        sa.CheckConstraint(
            "from_warehouse_id <> to_warehouse_id",
            name="ck_erp_stock_move_item_warehouses",
        ),
        sa.ForeignKeyConstraint(
            ["stock_move_id", "tenant_id"],
            ["erp.stock_move.id", "erp.stock_move.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_move_id", "line_no", name="uq_erp_stock_move_item_line"),
        schema="erp",
    )
    for column in (
        "tenant_id",
        "stock_move_id",
        "product_id",
        "from_warehouse_id",
        "to_warehouse_id",
    ):
        op.create_index(
            f"ix_erp_stock_move_item_{column}",
            "stock_move_item",
            [column],
            schema="erp",
        )

    create_document_header("stock_check")
    op.create_table(
        "stock_check_item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("stock_check_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("actual_quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("difference_quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "snapshot_quantity >= 0", name="ck_erp_stock_check_item_snapshot"
        ),
        sa.CheckConstraint(
            "actual_quantity >= 0", name="ck_erp_stock_check_item_actual"
        ),
        sa.CheckConstraint(
            "difference_quantity = actual_quantity - snapshot_quantity",
            name="ck_erp_stock_check_item_difference",
        ),
        sa.ForeignKeyConstraint(
            ["stock_check_id", "tenant_id"],
            ["erp.stock_check.id", "erp.stock_check.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "tenant_id"],
            ["erp.product.id", "erp.product.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_check_id", "line_no", name="uq_erp_stock_check_item_line"),
        schema="erp",
    )
    for column in ("tenant_id", "stock_check_id", "product_id", "warehouse_id"):
        op.create_index(
            f"ix_erp_stock_check_item_{column}",
            "stock_check_item",
            [column],
            schema="erp",
        )

    for table in TENANT_TABLES:
        enable_tenant_rls(table)


def downgrade() -> None:
    for table in ("stock_check_item", "stock_check", "stock_move_item", "stock_move"):
        op.drop_table(table, schema="erp")
