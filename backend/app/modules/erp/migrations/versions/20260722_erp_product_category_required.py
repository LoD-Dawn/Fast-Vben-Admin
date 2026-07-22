"""Require a category for every product while retaining legacy records.

Revision ID: erp_product_category_required
Revises: erp_warehouse_cost_references
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "erp_product_category_required"
down_revision = "erp_warehouse_cost_references"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    tenant_ids = connection.execute(
        sa.text(
            "SELECT DISTINCT tenant_id FROM erp.product WHERE category_id IS NULL"
        )
    ).scalars()
    for tenant_id in tenant_ids:
        category_id = uuid.uuid5(uuid.NAMESPACE_URL, f"erp-legacy-category:{tenant_id}")
        connection.execute(
            sa.text(
                """
                INSERT INTO erp.product_category
                    (id, tenant_id, code, name, parent_id, sort, is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :code, :name, NULL, 0, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": category_id,
                "tenant_id": tenant_id,
                "code": f"legacy-uncat-{category_id.hex[:16]}",
                "name": "历史未分类",
            },
        )
        connection.execute(
            sa.text(
                "UPDATE erp.product SET category_id = :category_id "
                "WHERE tenant_id = :tenant_id AND category_id IS NULL"
            ),
            {"category_id": category_id, "tenant_id": tenant_id},
        )
    op.alter_column("product", "category_id", nullable=False, schema="erp")


def downgrade() -> None:
    op.alter_column("product", "category_id", nullable=True, schema="erp")
