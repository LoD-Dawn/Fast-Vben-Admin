"""Enable forced tenant isolation for Platform social identity tables.

Revision ID: f5c9d3e7a1b4
Revises: e4b8c2d6f0a3
Create Date: 2026-07-20
"""

from alembic import op

revision = "f5c9d3e7a1b4"
down_revision = "e4b8c2d6f0a3"
branch_labels = None
depends_on = None


TENANT_TABLES = ("socialclient", "socialuser")


def upgrade() -> None:
    for table in TENANT_TABLES:
        policy = f"{table}_tenant_isolation"
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
        op.execute(
            f'''CREATE POLICY "{policy}" ON "{table}"
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )'''
        )


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        policy = f"{table}_tenant_isolation"
        op.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
