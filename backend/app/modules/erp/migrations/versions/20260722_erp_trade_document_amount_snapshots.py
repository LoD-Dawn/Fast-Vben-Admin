"""Add settlement accounts and immutable trade-document amount snapshots.

Revision ID: erp_trade_doc_snapshots
Revises: erp_master_data_uniqueness
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_trade_doc_snapshots"
down_revision = "erp_master_data_uniqueness"
branch_labels = None
depends_on = None

PURCHASE_HEADERS = ("purchase_in", "purchase_return")
SALE_HEADERS = ("sale_out", "sale_return")
ITEM_TABLES = (
    "purchase_in_item",
    "purchase_return_item",
    "sale_out_item",
    "sale_return_item",
)


def add_column(table: str, column: sa.Column) -> None:
    op.add_column(table, column, schema="erp")


def upgrade() -> None:
    for table in ("purchase_order", "sale_order", *PURCHASE_HEADERS, *SALE_HEADERS):
        add_column(table, sa.Column("settlement_account_id", sa.Uuid(), nullable=True))
        op.create_index(
            f"ix_erp_{table}_settlement_account_id",
            table,
            ["settlement_account_id"],
            schema="erp",
        )
        op.create_foreign_key(
            f"fk_erp_{table}_settlement_account_tenant",
            table,
            "settlement_account",
            ["settlement_account_id", "tenant_id"],
            ["id", "tenant_id"],
            source_schema="erp",
            referent_schema="erp",
            ondelete="RESTRICT",
        )

    for table in PURCHASE_HEADERS:
        for name, precision in (
            ("product_amount", sa.Numeric(20, 4)),
            ("tax_amount", sa.Numeric(20, 4)),
            ("discount_rate", sa.Numeric(7, 4)),
            ("discount_amount", sa.Numeric(20, 4)),
            ("other_fee", sa.Numeric(20, 4)),
        ):
            add_column(table, sa.Column(name, precision, nullable=False, server_default="0"))
        for expression, name in (
            ("product_amount >= 0", f"ck_erp_{table}_product_amount"),
            ("tax_amount >= 0", f"ck_erp_{table}_tax_amount"),
            ("discount_rate >= 0 AND discount_rate <= 100", f"ck_erp_{table}_discount_rate"),
            ("discount_amount >= 0", f"ck_erp_{table}_discount_amount"),
            ("other_fee >= 0", f"ck_erp_{table}_other_fee"),
        ):
            op.create_check_constraint(name, table, expression, schema="erp")

    for table in SALE_HEADERS:
        for name, precision in (
            ("product_amount", sa.Numeric(20, 4)),
            ("tax_amount", sa.Numeric(20, 4)),
            ("discount_rate", sa.Numeric(7, 4)),
            ("discount_amount", sa.Numeric(20, 4)),
            ("other_deduction", sa.Numeric(20, 4)),
        ):
            add_column(table, sa.Column(name, precision, nullable=False, server_default="0"))
        for expression, name in (
            ("product_amount >= 0", f"ck_erp_{table}_product_amount"),
            ("tax_amount >= 0", f"ck_erp_{table}_tax_amount"),
            ("discount_rate >= 0 AND discount_rate <= 100", f"ck_erp_{table}_discount_rate"),
            ("discount_amount >= 0", f"ck_erp_{table}_discount_amount"),
            ("other_deduction >= 0", f"ck_erp_{table}_other_deduction"),
        ):
            op.create_check_constraint(name, table, expression, schema="erp")

    for table in ITEM_TABLES:
        for name, precision in (
            ("tax_rate", sa.Numeric(7, 4)),
            ("product_amount", sa.Numeric(20, 4)),
            ("tax_amount", sa.Numeric(20, 4)),
            ("total_amount", sa.Numeric(20, 4)),
        ):
            add_column(table, sa.Column(name, precision, nullable=False, server_default="0"))
        op.create_check_constraint(
            f"ck_erp_{table}_tax_rate", table, "tax_rate >= 0 AND tax_rate <= 100", schema="erp"
        )

    for table in (*PURCHASE_HEADERS, *SALE_HEADERS):
        for name in ("product_amount", "tax_amount", "discount_rate", "discount_amount"):
            op.alter_column(table, name, server_default=None, schema="erp")
    for table in PURCHASE_HEADERS:
        op.alter_column(table, "other_fee", server_default=None, schema="erp")
    for table in SALE_HEADERS:
        op.alter_column(table, "other_deduction", server_default=None, schema="erp")
    for table in ITEM_TABLES:
        for name in ("tax_rate", "product_amount", "tax_amount", "total_amount"):
            op.alter_column(table, name, server_default=None, schema="erp")


def downgrade() -> None:
    for table in ITEM_TABLES:
        op.drop_constraint(f"ck_erp_{table}_tax_rate", table, schema="erp")
        for name in ("total_amount", "tax_amount", "product_amount", "tax_rate"):
            op.drop_column(table, name, schema="erp")
    for table in PURCHASE_HEADERS:
        for name in ("other_fee", "discount_amount", "discount_rate", "tax_amount", "product_amount"):
            op.drop_constraint(f"ck_erp_{table}_{name}", table, schema="erp")
        for name in ("other_fee", "discount_amount", "discount_rate", "tax_amount", "product_amount"):
            op.drop_column(table, name, schema="erp")
    for table in SALE_HEADERS:
        for name in ("other_deduction", "discount_amount", "discount_rate", "tax_amount", "product_amount"):
            op.drop_constraint(f"ck_erp_{table}_{name}", table, schema="erp")
        for name in ("other_deduction", "discount_amount", "discount_rate", "tax_amount", "product_amount"):
            op.drop_column(table, name, schema="erp")
    for table in ("purchase_order", "sale_order", *PURCHASE_HEADERS, *SALE_HEADERS):
        op.drop_constraint(f"fk_erp_{table}_settlement_account_tenant", table, schema="erp")
        op.drop_index(f"ix_erp_{table}_settlement_account_id", table_name=table, schema="erp")
        op.drop_column(table, "settlement_account_id", schema="erp")
