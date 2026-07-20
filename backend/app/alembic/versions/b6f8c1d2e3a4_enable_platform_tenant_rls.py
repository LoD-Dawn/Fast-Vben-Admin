"""Enable forced tenant isolation for Platform operational tables.

Revision ID: b6f8c1d2e3a4
Revises: a2d4e6f8b0c1
Create Date: 2026-07-20
"""

from alembic import op


revision = "b6f8c1d2e3a4"
down_revision = "a2d4e6f8b0c1"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "department",
    "post",
    "role",
    "roledatascopedepartment",
    "userpost",
    "userrole",
    "dictionaryitem",
    "dictionarytype",
    "notice",
    "sitemessagetemplate",
    "systemsetting",
    "usermessage",
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
