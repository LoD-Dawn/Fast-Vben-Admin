"""Create encrypted ERP settlement accounts.

Revision ID: erp_settlement_accounts
Revises: erp_sale_stock_documents
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_settlement_accounts"
down_revision = "erp_sale_stock_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settlement_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("account_no_encrypted", sa.String(1000), nullable=False),
        sa.Column("account_no_fingerprint", sa.String(80), nullable=False),
        sa.Column("account_no_last4", sa.String(4), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_erp_settlement_account_tenant_name"),
        sa.UniqueConstraint(
            "tenant_id",
            "account_no_fingerprint",
            name="uq_erp_settlement_account_tenant_fingerprint",
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_erp_settlement_account_id_tenant_id"),
        schema="erp",
    )
    op.create_index(
        "ix_erp_settlement_account_tenant_id",
        "settlement_account",
        ["tenant_id"],
        schema="erp",
    )
    op.create_index(
        "uq_erp_settlement_account_default_per_tenant",
        "settlement_account",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
        schema="erp",
    )
    op.execute("ALTER TABLE erp.settlement_account ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE erp.settlement_account FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY erp_settlement_account_tenant_isolation ON erp.settlement_account "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("settlement_account", schema="erp")
