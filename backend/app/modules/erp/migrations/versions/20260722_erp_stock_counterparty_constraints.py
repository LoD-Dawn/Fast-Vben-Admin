"""Enforce tenant-scoped stock document counterparties."""

from alembic import op

revision = "erp_stock_counterparty_fks"
down_revision = "erp_stock_check_amounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_erp_stock_in_supplier",
        "stock_in",
        "supplier",
        ["supplier_id", "tenant_id"],
        ["id", "tenant_id"],
        source_schema="erp",
        referent_schema="erp",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_erp_stock_out_customer",
        "stock_out",
        "customer",
        ["customer_id", "tenant_id"],
        ["id", "tenant_id"],
        source_schema="erp",
        referent_schema="erp",
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_erp_stock_out_customer", "stock_out", schema="erp")
    op.drop_constraint("fk_erp_stock_in_supplier", "stock_in", schema="erp")
