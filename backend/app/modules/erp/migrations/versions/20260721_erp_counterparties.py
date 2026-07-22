"""Create ERP supplier and customer master data.

Revision ID: erp_counterparties
Revises: erp_stock_move_check
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_counterparties"
down_revision = "erp_stock_move_check"
branch_labels = None
depends_on = None

TENANT_TABLES = ("supplier", "customer")


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


def create_counterparty(table: str) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("contact_name", sa.String(length=100), nullable=True),
        sa.Column("mobile", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("fax", sa.String(length=50), nullable=True),
        sa.Column("tax_no", sa.String(length=100), nullable=True),
        sa.Column("tax_rate", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("bank_name", sa.String(length=200), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 100",
            name=f"ck_erp_{table}_tax_rate",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name=f"uq_erp_{table}_tenant_name"),
        sa.UniqueConstraint("id", "tenant_id", name=f"uq_erp_{table}_id_tenant_id"),
        schema="erp",
    )
    op.create_index(f"ix_erp_{table}_tenant_id", table, ["tenant_id"], schema="erp")
    op.create_index(f"ix_erp_{table}_name", table, ["name"], schema="erp")
    op.create_index(
        f"ix_erp_{table}_contact_name", table, ["contact_name"], schema="erp"
    )


def upgrade() -> None:
    for table in TENANT_TABLES:
        create_counterparty(table)
        enable_tenant_rls(table)


def downgrade() -> None:
    for table in ("customer", "supplier"):
        op.drop_table(table, schema="erp")
