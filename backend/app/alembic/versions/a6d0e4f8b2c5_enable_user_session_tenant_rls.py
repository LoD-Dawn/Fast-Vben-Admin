"""Enable forced tenant isolation for authenticated user sessions.

Revision ID: a6d0e4f8b2c5
Revises: f5c9d3e7a1b4
Create Date: 2026-07-20
"""

from alembic import op

revision = "a6d0e4f8b2c5"
down_revision = "f5c9d3e7a1b4"
branch_labels = None
depends_on = None


TABLE = "usersession"
POLICY = "usersession_tenant_isolation"


def upgrade() -> None:
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{TABLE}" FORCE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS "{POLICY}" ON "{TABLE}"')
    op.execute(
        f'''CREATE POLICY "{POLICY}" ON "{TABLE}"
        USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        )
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        )'''
    )


def downgrade() -> None:
    op.execute(f'DROP POLICY IF EXISTS "{POLICY}" ON "{TABLE}"')
    op.execute(f'ALTER TABLE "{TABLE}" NO FORCE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{TABLE}" DISABLE ROW LEVEL SECURITY')
