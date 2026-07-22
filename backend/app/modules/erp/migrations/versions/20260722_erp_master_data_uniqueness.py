"""Enforce normalized ERP master-data uniqueness rules.

Revision ID: erp_master_data_uniqueness
Revises: erp_stock_counterparty_fks
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_master_data_uniqueness"
down_revision = "erp_stock_counterparty_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    # Legacy imports allowed duplicate display values. Keep every record, but
    # normalize whitespace and disambiguate later duplicates deterministically
    # before database constraints make the current business rule enforceable.
    for table in ("product_unit", "warehouse"):
        connection.execute(sa.text(f"UPDATE erp.{table} SET name = btrim(name)"))
        connection.execute(
            sa.text(
                f"""
                WITH duplicates AS (
                    SELECT id,
                           row_number() OVER (
                               PARTITION BY tenant_id, name ORDER BY created_at, id
                           ) AS duplicate_index
                    FROM erp.{table}
                )
                UPDATE erp.{table} AS target
                SET name = left(target.name, 80) || ' (' ||
                           substring(replace(target.id::text, '-', '') FROM 1 FOR 16) || ')'
                FROM duplicates
                WHERE target.id = duplicates.id AND duplicates.duplicate_index > 1
                """
            )
        )
    connection.execute(sa.text("UPDATE erp.product SET barcode = NULL WHERE btrim(coalesce(barcode, '')) = ''"))
    connection.execute(sa.text("UPDATE erp.product SET barcode = btrim(barcode) WHERE barcode IS NOT NULL"))
    connection.execute(
        sa.text(
            """
            WITH duplicates AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY tenant_id, barcode ORDER BY created_at, id
                       ) AS duplicate_index
                FROM erp.product
                WHERE barcode IS NOT NULL
            )
            UPDATE erp.product AS target
            SET barcode = left(target.barcode, 80) || '-' ||
                          substring(replace(target.id::text, '-', '') FROM 1 FOR 16)
            FROM duplicates
            WHERE target.id = duplicates.id AND duplicates.duplicate_index > 1
            """
        )
    )
    op.create_unique_constraint(
        "uq_erp_product_unit_tenant_name",
        "product_unit",
        ["tenant_id", "name"],
        schema="erp",
    )
    op.create_unique_constraint(
        "uq_erp_warehouse_tenant_name",
        "warehouse",
        ["tenant_id", "name"],
        schema="erp",
    )
    op.create_index(
        "uq_erp_product_tenant_barcode",
        "product",
        ["tenant_id", "barcode"],
        unique=True,
        schema="erp",
        postgresql_where="barcode IS NOT NULL AND barcode <> ''",
    )


def downgrade() -> None:
    op.drop_index("uq_erp_product_tenant_barcode", table_name="product", schema="erp")
    op.drop_constraint("uq_erp_warehouse_tenant_name", "warehouse", schema="erp")
    op.drop_constraint("uq_erp_product_unit_tenant_name", "product_unit", schema="erp")
