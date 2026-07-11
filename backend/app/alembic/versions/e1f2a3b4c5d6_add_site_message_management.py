"""add site message management

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sitemessagetemplate",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("sender_name", sa.String(length=100), nullable=False),
        sa.Column("content", sa.String(length=10000), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("params", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sitemessagetemplate_code"),
        "sitemessagetemplate",
        ["code"],
        unique=True,
    )

    op.add_column("usermessage", sa.Column("template_id", sa.UUID(), nullable=True))
    op.add_column(
        "usermessage",
        sa.Column("template_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "usermessage",
        sa.Column("template_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "usermessage",
        sa.Column("sender_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "usermessage",
        sa.Column("template_params", sa.String(length=4000), nullable=True),
    )
    op.create_foreign_key(
        "fk_usermessage_template_id_sitemessagetemplate",
        "usermessage",
        "sitemessagetemplate",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_usermessage_template_id", "usermessage", ["template_id"])
    op.create_index("ix_usermessage_template_code", "usermessage", ["template_code"])


def downgrade() -> None:
    op.drop_index("ix_usermessage_template_code", table_name="usermessage")
    op.drop_index("ix_usermessage_template_id", table_name="usermessage")
    op.drop_constraint(
        "fk_usermessage_template_id_sitemessagetemplate",
        "usermessage",
        type_="foreignkey",
    )
    op.drop_column("usermessage", "template_params")
    op.drop_column("usermessage", "sender_name")
    op.drop_column("usermessage", "template_name")
    op.drop_column("usermessage", "template_code")
    op.drop_column("usermessage", "template_id")
    op.drop_index(op.f("ix_sitemessagetemplate_code"), table_name="sitemessagetemplate")
    op.drop_table("sitemessagetemplate")
