"""Enable forced row-level tenant isolation for Items.

Revision ID: items_enable_tenant_rls
Revises: items_rename_tenant_index
Create Date: 2026-07-20
"""

from alembic import op

revision = "items_enable_tenant_rls"
down_revision = "items_rename_tenant_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE items.item ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE items.item FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS items_item_tenant_isolation ON items.item")
    op.execute(
        """
        CREATE POLICY items_item_tenant_isolation ON items.item
        USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        )
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS items_item_tenant_isolation ON items.item")
    op.execute("ALTER TABLE items.item NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE items.item DISABLE ROW LEVEL SECURITY")
