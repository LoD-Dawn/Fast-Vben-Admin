"""Store server-calculated totals for other stock documents."""

import sqlalchemy as sa
from alembic import op

revision = "erp_stock_document_amounts"
down_revision = "erp_stock_counterparties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("stock_in", "stock_out", "stock_move"):
        op.add_column(table, sa.Column("total_amount", sa.Numeric(20, 4), nullable=False, server_default="0"), schema="erp")
        op.create_check_constraint(f"ck_erp_{table}_total_amount", table, "total_amount >= 0", schema="erp")
        op.alter_column(table, "total_amount", server_default=None, schema="erp")


def downgrade() -> None:
    for table in ("stock_move", "stock_out", "stock_in"):
        op.drop_constraint(f"ck_erp_{table}_total_amount", table, schema="erp")
        op.drop_column(table, "total_amount", schema="erp")
