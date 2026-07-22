"""Create transactional ERP document number sequences.

Revision ID: erp_document_sequence
Revises: erp_counterparties
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_document_sequence"
down_revision = "erp_counterparties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_sequence",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("prefix", sa.String(length=12), nullable=False),
        sa.Column("sequence_date", sa.Date(), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.CheckConstraint("next_value > 0", name="ck_erp_document_sequence_next_value"),
        sa.PrimaryKeyConstraint("tenant_id", "prefix", "sequence_date"),
        schema="erp",
    )
    op.execute("ALTER TABLE erp.document_sequence ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE erp.document_sequence FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY erp_document_sequence_tenant_isolation ON erp.document_sequence
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.drop_table("document_sequence", schema="erp")
