"""Create ERP logical document attachments.

Revision ID: erp_document_attachments
Revises: erp_command_receipts
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_document_attachments"
down_revision = "erp_command_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_attachment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sort >= 0", name="ck_erp_document_attachment_sort"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "document_type", "document_id", "file_id",
            name="uq_erp_document_attachment_file",
        ),
        schema="erp",
    )
    for column in ("tenant_id", "document_type", "document_id", "file_id"):
        op.create_index(
            f"ix_erp_document_attachment_{column}", "document_attachment", [column], schema="erp"
        )
    op.execute("ALTER TABLE erp.document_attachment ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE erp.document_attachment FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY erp_document_attachment_tenant_isolation ON erp.document_attachment "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("document_attachment", schema="erp")
