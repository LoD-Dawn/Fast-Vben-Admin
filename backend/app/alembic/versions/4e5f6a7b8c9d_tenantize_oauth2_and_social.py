"""tenantize oauth2 and social

Revision ID: 4e5f6a7b8c9d
Revises: 3e4f5a6b7c8d
Create Date: 2026-07-16 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4e5f6a7b8c9d"
down_revision: str | None = "3e4f5a6b7c8d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-4000-8000-000000000001"
TENANT_TABLES = (
    "oauth2client",
    "oauth2accesstoken",
    "oauth2authorizationcode",
    "socialclient",
    "socialuser",
)


def add_tenant_column(table_name: str) -> None:
    op.add_column(table_name, sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET tenant_id = CAST(:tenant_id AS UUID)
            """
        ).bindparams(tenant_id=DEFAULT_TENANT_ID)
    )
    op.alter_column(table_name, "tenant_id", nullable=False)
    op.create_index(
        op.f(f"ix_{table_name}_tenant_id"),
        table_name,
        ["tenant_id"],
        unique=False,
    )
    op.create_foreign_key(
        f"fk_{table_name}_tenant_id_tenant",
        table_name,
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def upgrade() -> None:
    for table_name in TENANT_TABLES:
        add_tenant_column(table_name)

    op.create_unique_constraint(
        "uq_oauth2client_tenant_client_id",
        "oauth2client",
        ["tenant_id", "client_id"],
    )
    op.create_unique_constraint(
        "uq_oauth2client_id_tenant_id",
        "oauth2client",
        ["id", "tenant_id"],
    )
    op.create_foreign_key(
        "fk_oauth2authorizationcode_client_tenant",
        "oauth2authorizationcode",
        "oauth2client",
        ["client_id", "tenant_id"],
        ["client_id", "tenant_id"],
    )
    op.create_foreign_key(
        "fk_oauth2accesstoken_client_tenant",
        "oauth2accesstoken",
        "oauth2client",
        ["client_id", "tenant_id"],
        ["client_id", "tenant_id"],
    )

    op.drop_constraint(
        "uq_socialclient_social_type_user_type",
        "socialclient",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_socialclient_tenant_social_type_user_type",
        "socialclient",
        ["tenant_id", "social_type", "user_type"],
    )
    op.create_unique_constraint(
        "uq_socialclient_id_tenant_id",
        "socialclient",
        ["id", "tenant_id"],
    )

    op.drop_constraint("socialuser_user_id_fkey", "socialuser", type_="foreignkey")
    op.drop_constraint(
        "socialuser_social_client_id_fkey",
        "socialuser",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_socialuser_type_openid",
        "socialuser",
        type_="unique",
    )
    op.create_foreign_key(
        "fk_socialuser_membership_tenant",
        "socialuser",
        "tenantmembership",
        ["user_id", "tenant_id"],
        ["user_id", "tenant_id"],
    )
    op.create_foreign_key(
        "fk_socialuser_client_tenant",
        "socialuser",
        "socialclient",
        ["social_client_id", "tenant_id"],
        ["id", "tenant_id"],
    )
    op.create_unique_constraint(
        "uq_socialuser_tenant_type_openid",
        "socialuser",
        ["tenant_id", "type", "openid"],
    )


def downgrade() -> None:
    for table_name in reversed(TENANT_TABLES):
        op.execute(
            sa.text(
                f"""
                DELETE FROM {table_name}
                WHERE tenant_id != CAST(:tenant_id AS UUID)
                """
            ).bindparams(tenant_id=DEFAULT_TENANT_ID)
        )

    op.drop_constraint(
        "uq_socialuser_tenant_type_openid",
        "socialuser",
        type_="unique",
    )
    op.drop_constraint(
        "fk_socialuser_client_tenant",
        "socialuser",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_socialuser_membership_tenant",
        "socialuser",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "socialuser_social_client_id_fkey",
        "socialuser",
        "socialclient",
        ["social_client_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "socialuser_user_id_fkey",
        "socialuser",
        "user",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_socialuser_type_openid",
        "socialuser",
        ["type", "openid"],
    )

    op.drop_constraint(
        "uq_socialclient_id_tenant_id",
        "socialclient",
        type_="unique",
    )
    op.drop_constraint(
        "uq_socialclient_tenant_social_type_user_type",
        "socialclient",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_socialclient_social_type_user_type",
        "socialclient",
        ["social_type", "user_type"],
    )

    op.drop_constraint(
        "fk_oauth2accesstoken_client_tenant",
        "oauth2accesstoken",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_oauth2authorizationcode_client_tenant",
        "oauth2authorizationcode",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_oauth2client_id_tenant_id",
        "oauth2client",
        type_="unique",
    )
    op.drop_constraint(
        "uq_oauth2client_tenant_client_id",
        "oauth2client",
        type_="unique",
    )

    for table_name in reversed(TENANT_TABLES):
        op.drop_constraint(
            f"fk_{table_name}_tenant_id_tenant",
            table_name,
            type_="foreignkey",
        )
        op.drop_index(op.f(f"ix_{table_name}_tenant_id"), table_name=table_name)
        op.drop_column(table_name, "tenant_id")
