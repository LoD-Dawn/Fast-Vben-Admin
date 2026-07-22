"""Create the ERP inventory balance, ledger, and stock document baseline.

Revision ID: erp_stock_baseline
Revises: erp_master_data_baseline
Create Date: 2026-07-20
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_stock_baseline"
down_revision = "erp_master_data_baseline"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "stock_balance",
    "stock_ledger",
    "stock_in",
    "stock_in_item",
    "stock_out",
    "stock_out_item",
)


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


def upgrade() -> None:
    op.create_table(
        "stock_balance",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantity >= 0", name="ck_erp_stock_balance_quantity"),
        sa.CheckConstraint("version > 0", name="ck_erp_stock_balance_version"),
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
        sa.UniqueConstraint(
            "tenant_id",
            "product_id",
            "warehouse_id",
            name="uq_erp_stock_balance_tenant_product_warehouse",
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_erp_stock_balance_id_tenant_id"),
        schema="erp",
    )
    op.create_index("ix_erp_stock_balance_tenant_id", "stock_balance", ["tenant_id"], schema="erp")
    op.create_index("ix_erp_stock_balance_product_id", "stock_balance", ["product_id"], schema="erp")
    op.create_index("ix_erp_stock_balance_warehouse_id", "stock_balance", ["warehouse_id"], schema="erp")

    op.create_table(
        "stock_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("delta_quantity", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("ledger_type", sa.String(length=32), nullable=False),
        sa.Column("source_document_type", sa.String(length=32), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("source_item_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_no", sa.String(length=32), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("reversal_of_id", sa.Uuid(), nullable=True),
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("delta_quantity <> 0", name="ck_erp_stock_ledger_delta"),
        sa.CheckConstraint(
            "balance_after >= 0", name="ck_erp_stock_ledger_balance_after"
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
        sa.UniqueConstraint(
            "tenant_id",
            "source_document_type",
            "source_document_id",
            "source_item_id",
            "source_version",
            "ledger_type",
            name="uq_erp_stock_ledger_source_effect",
        ),
        schema="erp",
    )
    op.create_index("ix_erp_stock_ledger_tenant_id", "stock_ledger", ["tenant_id"], schema="erp")
    op.create_index("ix_erp_stock_ledger_product_id", "stock_ledger", ["product_id"], schema="erp")
    op.create_index("ix_erp_stock_ledger_warehouse_id", "stock_ledger", ["warehouse_id"], schema="erp")
    op.create_index("ix_erp_stock_ledger_ledger_type", "stock_ledger", ["ledger_type"], schema="erp")
    op.create_index("ix_erp_stock_ledger_source_document_type", "stock_ledger", ["source_document_type"], schema="erp")
    op.create_index("ix_erp_stock_ledger_source_document_id", "stock_ledger", ["source_document_id"], schema="erp")
    op.create_index("ix_erp_stock_ledger_source_item_id", "stock_ledger", ["source_item_id"], schema="erp")
    op.create_index("ix_erp_stock_ledger_reversal_of_id", "stock_ledger", ["reversal_of_id"], schema="erp")
    op.create_index("ix_erp_stock_ledger_occurred_at", "stock_ledger", ["occurred_at"], schema="erp")
    op.create_index(
        "uq_erp_stock_ledger_reversal",
        "stock_ledger",
        ["tenant_id", "reversal_of_id"],
        unique=True,
        postgresql_where=sa.text("reversal_of_id IS NOT NULL"),
        schema="erp",
    )

    for table, item_table, foreign_key, line_constraint in (
        ("stock_in", "stock_in_item", "stock_in_id", "uq_erp_stock_in_item_line"),
        ("stock_out", "stock_out_item", "stock_out_id", "uq_erp_stock_out_item_line"),
    ):
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
        op.create_table(
            item_table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column(foreign_key, sa.Uuid(), nullable=False),
            sa.Column("line_no", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Uuid(), nullable=False),
            sa.Column("warehouse_id", sa.Uuid(), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=20, scale=6), nullable=False),
            sa.Column("reference_price", sa.Numeric(precision=20, scale=4), nullable=False),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.CheckConstraint("quantity > 0", name=f"ck_erp_{item_table}_quantity"),
            sa.ForeignKeyConstraint(
                [foreign_key, "tenant_id"],
                [f"erp.{table}.id", f"erp.{table}.tenant_id"],
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
            sa.UniqueConstraint(foreign_key, "line_no", name=line_constraint),
            schema="erp",
        )
        op.create_index(f"ix_erp_{item_table}_tenant_id", item_table, ["tenant_id"], schema="erp")
        op.create_index(f"ix_erp_{item_table}_{foreign_key}", item_table, [foreign_key], schema="erp")
        op.create_index(f"ix_erp_{item_table}_product_id", item_table, ["product_id"], schema="erp")
        op.create_index(f"ix_erp_{item_table}_warehouse_id", item_table, ["warehouse_id"], schema="erp")

    for table in TENANT_TABLES:
        enable_tenant_rls(table)


def downgrade() -> None:
    for table in ("stock_out_item", "stock_out", "stock_in_item", "stock_in", "stock_ledger", "stock_balance"):
        op.drop_table(table, schema="erp")
