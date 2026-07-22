"""Create append-only ERP document action logs.

Revision ID: erp_document_action_log
Revises: erp_finance_documents
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "erp_document_action_log"
down_revision = "erp_finance_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_action_log",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False), sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("resource_no", sa.String(32), nullable=True), sa.Column("action", sa.String(32), nullable=False),
        sa.Column("old_status", sa.String(32), nullable=True), sa.Column("new_status", sa.String(32), nullable=True),
        sa.Column("old_version", sa.Integer(), nullable=True), sa.Column("new_version", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False), sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("old_version IS NULL OR old_version > 0", name="ck_erp_action_log_old_version"),
        sa.CheckConstraint("new_version IS NULL OR new_version > 0", name="ck_erp_action_log_new_version"),
        sa.PrimaryKeyConstraint("id"), schema="erp",
    )
    for column in ("tenant_id", "resource_type", "resource_id", "action", "actor_id", "occurred_at"):
        op.create_index(f"ix_erp_document_action_log_{column}", "document_action_log", [column], schema="erp")
    op.execute("ALTER TABLE erp.document_action_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE erp.document_action_log FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY erp_document_action_log_tenant_isolation ON erp.document_action_log "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("document_action_log", schema="erp")
