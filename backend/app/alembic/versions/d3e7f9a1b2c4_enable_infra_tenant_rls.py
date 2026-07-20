"""Enable forced tenant isolation for Platform infrastructure tables.

Revision ID: d3e7f9a1b2c4
Revises: b6f8c1d2e3a4
Create Date: 2026-07-20
"""

from alembic import op

revision = "d3e7f9a1b2c4"
down_revision = "b6f8c1d2e3a4"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "fileasset",
    "filestoragechannel",
    "mailaccount",
    "mailtemplate",
    "maillog",
    "loginlog",
    "operationlog",
)


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
