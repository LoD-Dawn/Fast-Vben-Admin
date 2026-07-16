"""add tenant operations

Revision ID: 3e4f5a6b7c8d
Revises: 2d3e4f5a6b7c
Create Date: 2026-07-16 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3e4f5a6b7c8d"
down_revision: str | None = "2d3e4f5a6b7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())

    if "tenantprofile" not in table_names:
        op.create_table(
            "tenantprofile",
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("contact_user_id", sa.UUID(), nullable=True),
            sa.Column("contact_name", sa.String(length=100), nullable=True),
            sa.Column("contact_mobile", sa.String(length=32), nullable=True),
            sa.Column("industry", sa.Integer(), nullable=True),
            sa.Column("tenant_type", sa.Integer(), nullable=True),
            sa.Column("address_code", sa.String(length=100), nullable=True),
            sa.Column("address_detail", sa.String(length=255), nullable=True),
            sa.Column("qualifications", sa.String(length=500), nullable=True),
            sa.Column("website", sa.String(length=255), nullable=True),
            sa.Column("recharge_amount", sa.Float(), nullable=False, server_default="0"),
            sa.Column("payment_amount", sa.Float(), nullable=False, server_default="0"),
            sa.Column("balance_amount", sa.Float(), nullable=False, server_default="0"),
            sa.Column("account_count", sa.Integer(), nullable=True),
            sa.Column(
                "lifecycle_status",
                sa.String(length=32),
                nullable=False,
                server_default="formal",
            ),
            sa.Column(
                "lifecycle_status_before_freeze",
                sa.String(length=32),
                nullable=True,
            ),
            sa.Column(
                "effective_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column(
                "trial_ends_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column(
                "service_expires_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("frozen_reason", sa.String(length=500), nullable=True),
            sa.Column("owner_name", sa.String(length=100), nullable=True),
            sa.Column("customer_source", sa.String(length=100), nullable=True),
            sa.Column("follow_up_notes", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["contact_user_id"], ["user.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("tenant_id"),
        )
    else:
        columns = _column_names("tenantprofile")
        new_columns = (
            sa.Column(
                "lifecycle_status",
                sa.String(length=32),
                nullable=False,
                server_default="formal",
            ),
            sa.Column(
                "lifecycle_status_before_freeze",
                sa.String(length=32),
                nullable=True,
            ),
            sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "service_expires_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("frozen_reason", sa.String(length=500), nullable=True),
            sa.Column("owner_name", sa.String(length=100), nullable=True),
            sa.Column("customer_source", sa.String(length=100), nullable=True),
            sa.Column("follow_up_notes", sa.String(length=1000), nullable=True),
        )
        for column in new_columns:
            if column.name not in columns:
                op.add_column("tenantprofile", column)

    profile_indexes = _index_names("tenantprofile")
    for index_name, column_name in (
        ("ix_tenantprofile_lifecycle_status", "lifecycle_status"),
        ("ix_tenantprofile_trial_ends_at", "trial_ends_at"),
        ("ix_tenantprofile_service_expires_at", "service_expires_at"),
        ("ix_tenantprofile_owner_name", "owner_name"),
        ("ix_tenantprofile_customer_source", "customer_source"),
    ):
        if index_name not in profile_indexes:
            op.create_index(index_name, "tenantprofile", [column_name], unique=False)

    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())
    if "tenantplanprofile" not in table_names:
        op.create_table(
            "tenantplanprofile",
            sa.Column("plan_id", sa.UUID(), nullable=False),
            sa.Column("package_type", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("logo", sa.String(length=500), nullable=True),
            sa.Column("price", sa.Float(), nullable=False, server_default="0"),
            sa.Column("published", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("order_num", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "subscription_num", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "subscription_total_amount",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("remark", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["plan_id"], ["tenantplan.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("plan_id"),
        )

    if "tenantplanmenu" not in table_names:
        op.create_table(
            "tenantplanmenu",
            sa.Column("plan_id", sa.UUID(), nullable=False),
            sa.Column("menu_id", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["menu_id"], ["menu.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["plan_id"], ["tenantplan.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("plan_id", "menu_id"),
        )

    op.execute(
        sa.text(
            """
            INSERT INTO tenantprofile (
                tenant_id, lifecycle_status, effective_at, created_at, updated_at
            )
            SELECT id, 'formal', COALESCE(created_at, CURRENT_TIMESTAMP),
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM tenant
            ON CONFLICT (tenant_id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tenantprofile
            SET effective_at = COALESCE(effective_at, created_at, CURRENT_TIMESTAMP)
            WHERE effective_at IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO tenantplanprofile (plan_id, created_at, updated_at)
            SELECT id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM tenantplan
            ON CONFLICT (plan_id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO tenantplanmenu (plan_id, menu_id, created_at)
            SELECT plan.id, menu.id, CURRENT_TIMESTAMP
            FROM tenantplan AS plan
            CROSS JOIN menu
            WHERE COALESCE(menu.permission_code, '') NOT LIKE 'platform:%'
            ON CONFLICT (plan_id, menu_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())
    if "tenantplanmenu" in table_names:
        op.drop_table("tenantplanmenu")
    if "tenantplanprofile" in table_names:
        op.drop_table("tenantplanprofile")
    if "tenantprofile" in table_names:
        lifecycle_columns = {
            "lifecycle_status",
            "lifecycle_status_before_freeze",
            "effective_at",
            "trial_ends_at",
            "service_expires_at",
            "frozen_at",
            "frozen_reason",
            "owner_name",
            "customer_source",
            "follow_up_notes",
        }
        columns = _column_names("tenantprofile")
        for column_name in lifecycle_columns & columns:
            op.drop_column("tenantprofile", column_name)
