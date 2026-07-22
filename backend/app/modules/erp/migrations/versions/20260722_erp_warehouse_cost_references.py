"""Add warehouse cost reference fields."""

import sqlalchemy as sa
from alembic import op

revision = "erp_warehouse_cost_references"
down_revision = "erp_product_operational_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("storage_fee_reference", "transport_fee_reference"):
        op.add_column("warehouse", sa.Column(column, sa.Numeric(20, 4), nullable=False, server_default="0"), schema="erp")
        op.create_check_constraint(f"ck_erp_warehouse_{column}", "warehouse", f"{column} >= 0", schema="erp")
        op.alter_column("warehouse", column, server_default=None, schema="erp")


def downgrade() -> None:
    for column in ("transport_fee_reference", "storage_fee_reference"):
        op.drop_constraint(f"ck_erp_warehouse_{column}", "warehouse", schema="erp")
        op.drop_column("warehouse", column, schema="erp")
