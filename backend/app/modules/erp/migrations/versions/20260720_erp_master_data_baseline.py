"""Create the ERP master-data baseline with forced tenant RLS.

Revision ID: erp_master_data_baseline
Revises: None
Create Date: 2026-07-20
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_master_data_baseline"
down_revision = None
branch_labels = ("erp",)
depends_on = None

TENANT_TABLES = ("product_unit", "product_category", "product", "warehouse")


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
    op.execute("CREATE SCHEMA IF NOT EXISTS erp")
    op.create_table(
        "product_unit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_erp_product_unit_tenant_code"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_erp_product_unit_id_tenant_id"),
        schema="erp",
    )
    op.create_index("ix_erp_product_unit_tenant_id", "product_unit", ["tenant_id"], schema="erp")
    op.create_table(
        "product_category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_id", "tenant_id"],
            ["erp.product_category.id", "erp.product_category.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_erp_product_category_tenant_code"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_erp_product_category_id_tenant_id"),
        schema="erp",
    )
    op.create_index("ix_erp_product_category_tenant_id", "product_category", ["tenant_id"], schema="erp")
    op.create_index("ix_erp_product_category_parent_id", "product_category", ["parent_id"], schema="erp")
    op.create_table(
        "product",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("barcode", sa.String(length=100), nullable=True),
        sa.Column("specification", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_id", "tenant_id"],
            ["erp.product_category.id", "erp.product_category.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id", "tenant_id"],
            ["erp.product_unit.id", "erp.product_unit.tenant_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_erp_product_tenant_code"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_erp_product_id_tenant_id"),
        schema="erp",
    )
    op.create_index("ix_erp_product_tenant_id", "product", ["tenant_id"], schema="erp")
    op.create_index("ix_erp_product_category_id", "product", ["category_id"], schema="erp")
    op.create_index("ix_erp_product_unit_id", "product", ["unit_id"], schema="erp")
    op.create_table(
        "warehouse",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("contact_name", sa.String(length=100), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_erp_warehouse_tenant_code"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_erp_warehouse_id_tenant_id"),
        schema="erp",
    )
    op.create_index("ix_erp_warehouse_tenant_id", "warehouse", ["tenant_id"], schema="erp")
    for table in TENANT_TABLES:
        enable_tenant_rls(table)


def downgrade() -> None:
    for table in ("product", "product_category", "product_unit", "warehouse"):
        op.drop_table(table, schema="erp")
    op.execute("DROP SCHEMA erp")
