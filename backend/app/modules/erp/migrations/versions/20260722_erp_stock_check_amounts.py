"""Add reference and difference amounts to stock checks."""

import sqlalchemy as sa
from alembic import op

revision = "erp_stock_check_amounts"
down_revision = "erp_stock_document_amounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stock_check", sa.Column("total_amount", sa.Numeric(20, 4), nullable=False, server_default="0"), schema="erp")
    op.create_check_constraint("ck_erp_stock_check_total_amount", "stock_check", "total_amount >= 0", schema="erp")
    op.alter_column("stock_check", "total_amount", server_default=None, schema="erp")
    for column in ("reference_price", "difference_amount"):
        op.add_column("stock_check_item", sa.Column(column, sa.Numeric(20, 4), nullable=False, server_default="0"), schema="erp")
        op.alter_column("stock_check_item", column, server_default=None, schema="erp")


def downgrade() -> None:
    for column in ("difference_amount", "reference_price"):
        op.drop_column("stock_check_item", column, schema="erp")
    op.drop_constraint("ck_erp_stock_check_total_amount", "stock_check", schema="erp")
    op.drop_column("stock_check", "total_amount", schema="erp")
