"""Create ERP payment and receipt settlement documents.

Revision ID: erp_finance_documents
Revises: erp_document_settlement_amounts
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_finance_documents"
down_revision = "erp_document_settlement_amounts"
branch_labels = None
depends_on = None


def enable_tenant_rls(table: str) -> None:
    policy = f"erp_{table}_tenant_isolation"
    op.execute(f"ALTER TABLE erp.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE erp.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {policy} ON erp.{table} "
        "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def create_header(*, table: str, counterparty: str, amount: str) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("no", sa.String(32), nullable=False), sa.Column(f"{counterparty}_id", sa.Uuid(), nullable=False),
        sa.Column(f"{counterparty}_name", sa.String(200), nullable=False), sa.Column("settlement_account_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("business_at", sa.DateTime(timezone=True), nullable=False), sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("total_settlement_amount", sa.Numeric(20, 4), nullable=False), sa.Column("discount_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column(amount, sa.Numeric(20, 4), nullable=False), sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True), sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.Uuid(), nullable=True), sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint([f"{counterparty}_id", "tenant_id"], [f"erp.{counterparty}.id", f"erp.{counterparty}.tenant_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["settlement_account_id", "tenant_id"], ["erp.settlement_account.id", "erp.settlement_account.tenant_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("version > 0", name=f"ck_erp_{table}_version"),
        sa.CheckConstraint("total_settlement_amount >= 0", name=f"ck_erp_{table}_settlement_amount"),
        sa.CheckConstraint("discount_amount >= 0", name=f"ck_erp_{table}_discount_amount"),
        sa.CheckConstraint(f"{amount} >= 0", name=f"ck_erp_{table}_{amount}"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("tenant_id", "no", name=f"uq_erp_{table}_tenant_no"),
        sa.UniqueConstraint("id", "tenant_id", name=f"uq_erp_{table}_id_tenant_id"), schema="erp",
    )
    for column in ("tenant_id", f"{counterparty}_id", "settlement_account_id", "owner_id", "business_at"):
        op.create_index(f"ix_erp_{table}_{column}", table, [column], schema="erp")


def create_item(*, table: str, header: str, source_types: str) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(f"{header}_id", sa.Uuid(), nullable=False), sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False), sa.Column("source_document_no", sa.String(32), nullable=False),
        sa.Column("source_total_signed", sa.Numeric(20, 4), nullable=False), sa.Column("settled_before_signed", sa.Numeric(20, 4), nullable=False),
        sa.Column("settlement_signed", sa.Numeric(20, 4), nullable=False), sa.Column("discount_allocated", sa.Numeric(20, 4), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint([f"{header}_id", "tenant_id"], [f"erp.{header}.id", f"erp.{header}.tenant_id"], ondelete="CASCADE"),
        sa.CheckConstraint(f"source_type IN ({source_types})", name=f"ck_erp_{table}_source_type"),
        sa.CheckConstraint("discount_allocated >= 0", name=f"ck_erp_{table}_discount"),
        sa.CheckConstraint("settlement_signed <> 0", name=f"ck_erp_{table}_settlement"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint(f"{header}_id", "source_type", "source_document_id", name=f"uq_erp_{table}_source"), schema="erp",
    )
    for column in ("tenant_id", f"{header}_id", "source_type", "source_document_id"):
        op.create_index(f"ix_erp_{table}_{column}", table, [column], schema="erp")


def upgrade() -> None:
    create_header(table="finance_payment", counterparty="supplier", amount="payment_amount")
    create_item(table="finance_payment_item", header="finance_payment", source_types="'purchase_in', 'purchase_return'")
    create_header(table="finance_receipt", counterparty="customer", amount="receipt_amount")
    create_item(table="finance_receipt_item", header="finance_receipt", source_types="'sale_out', 'sale_return'")
    for table in ("finance_payment", "finance_payment_item", "finance_receipt", "finance_receipt_item"):
        enable_tenant_rls(table)


def downgrade() -> None:
    for table in ("finance_receipt_item", "finance_receipt", "finance_payment_item", "finance_payment"):
        op.drop_table(table, schema="erp")
