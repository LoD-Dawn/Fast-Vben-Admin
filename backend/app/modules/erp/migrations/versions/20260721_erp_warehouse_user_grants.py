"""Create ERP warehouse user grants.

Revision ID: erp_warehouse_user_grants
Revises: erp_document_attachments
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_warehouse_user_grants"
down_revision = "erp_document_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouse_user_grant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["warehouse_id", "tenant_id"],
            ["erp.warehouse.id", "erp.warehouse.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "warehouse_id", "user_id", name="uq_erp_warehouse_user_grant"
        ),
        schema="erp",
    )
    for column in ("tenant_id", "warehouse_id", "user_id"):
        op.create_index(
            f"ix_erp_warehouse_user_grant_{column}", "warehouse_user_grant", [column], schema="erp"
        )
    op.execute("ALTER TABLE erp.warehouse_user_grant ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE erp.warehouse_user_grant FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY erp_warehouse_user_grant_tenant_isolation ON erp.warehouse_user_grant "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("warehouse_user_grant", schema="erp")
