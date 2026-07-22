"""Create ERP idempotency command receipts.

Revision ID: erp_command_receipts
Revises: erp_document_action_log
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_command_receipts"
down_revision = "erp_document_action_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "command_receipt",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("command_name", sa.String(120), nullable=False),
        sa.Column("idempotency_key_sha256", sa.String(64), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("resource_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processing', 'completed')",
            name="ck_erp_command_receipt_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "command_name",
            "idempotency_key_sha256",
            name="uq_erp_command_receipt_command_key",
        ),
        schema="erp",
    )
    for column in ("tenant_id", "command_name", "resource_id", "expires_at"):
        op.create_index(
            f"ix_erp_command_receipt_{column}",
            "command_receipt",
            [column],
            schema="erp",
        )
    op.execute("ALTER TABLE erp.command_receipt ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE erp.command_receipt FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY erp_command_receipt_tenant_isolation ON erp.command_receipt "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("command_receipt", schema="erp")
