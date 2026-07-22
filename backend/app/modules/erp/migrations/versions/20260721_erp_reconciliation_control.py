"""Add ERP tenant integrity settings and reconciliation runs.

Revision ID: erp_reconciliation_control
Revises: erp_warehouse_user_grants
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "erp_reconciliation_control"
down_revision = "erp_warehouse_user_grants"
branch_labels = None
depends_on = None


def _enable_tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE erp.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE erp.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY erp_{table}_tenant_isolation ON erp.{table} "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def upgrade() -> None:
    op.create_table(
        "erp_setting",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column(
            "integrity_status", sa.String(16), nullable=False, server_default="healthy"
        ),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_erp_setting_version"),
        sa.CheckConstraint(
            "integrity_status IN ('healthy', 'degraded')",
            name="ck_erp_setting_integrity_status",
        ),
        sa.PrimaryKeyConstraint("tenant_id"),
        schema="erp",
    )
    op.create_table(
        "reconciliation_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stock_difference_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "settlement_difference_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'passed', 'failed')",
            name="ck_erp_reconciliation_run_status",
        ),
        sa.CheckConstraint(
            "stock_difference_count >= 0",
            name="ck_erp_reconciliation_run_stock_difference_count",
        ),
        sa.CheckConstraint(
            "settlement_difference_count >= 0",
            name="ck_erp_reconciliation_run_settlement_difference_count",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="erp",
    )
    for column in ("tenant_id", "started_at", "triggered_by"):
        op.create_index(
            f"ix_erp_reconciliation_run_{column}",
            "reconciliation_run",
            [column],
            schema="erp",
        )
    _enable_tenant_rls("erp_setting")
    _enable_tenant_rls("reconciliation_run")


def downgrade() -> None:
    op.drop_table("reconciliation_run", schema="erp")
    op.drop_table("erp_setting", schema="erp")
