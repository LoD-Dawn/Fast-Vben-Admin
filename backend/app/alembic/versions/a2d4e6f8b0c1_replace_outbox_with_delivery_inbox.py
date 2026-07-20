"""replace outbox completion with delivery and inbox state

Revision ID: a2d4e6f8b0c1
Revises: c31ccca371d3
Create Date: 2026-07-20 10:10:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


revision = "a2d4e6f8b0c1"
down_revision = "c31ccca371d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `published` meant consumer completion in the old model; preserve it as complete.
    op.execute("UPDATE outboxevent SET status = 'complete' WHERE status = 'published'")
    # Existing pending rows have no persisted target snapshot, so they cannot be
    # retried safely after this model change. Operators can replay from source data.
    op.execute(
        """
        UPDATE outboxevent
        SET status = 'dead_letter',
            dead_lettered_at = COALESCE(dead_lettered_at, NOW()),
            last_error = COALESCE(last_error, 'M2 migration: no delivery target snapshot')
        WHERE status = 'pending'
        """
    )
    op.alter_column("outboxevent", "published_at", new_column_name="completed_at")
    op.add_column("outboxevent", sa.Column("aggregate_sequence", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_outboxevent_aggregate_sequence"),
        "outboxevent",
        ["aggregate_sequence"],
        unique=False,
    )
    op.rename_table("eventconsumerreceipt", "inboxreceipt")
    op.create_table(
        "eventdelivery",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("target_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("consumer_module", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_by", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["outboxevent.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "target_name", name="uq_event_delivery_target"),
    )
    for column in (
        "event_id",
        "target_type",
        "consumer_module",
        "status",
        "available_at",
        "locked_by",
        "locked_until",
    ):
        op.create_index(op.f(f"ix_eventdelivery_{column}"), "eventdelivery", [column], unique=False)


def downgrade() -> None:
    for column in (
        "locked_until",
        "locked_by",
        "available_at",
        "status",
        "consumer_module",
        "target_type",
        "event_id",
    ):
        op.drop_index(op.f(f"ix_eventdelivery_{column}"), table_name="eventdelivery")
    op.drop_table("eventdelivery")
    op.rename_table("inboxreceipt", "eventconsumerreceipt")
    op.drop_index(op.f("ix_outboxevent_aggregate_sequence"), table_name="outboxevent")
    op.drop_column("outboxevent", "aggregate_sequence")
    op.alter_column("outboxevent", "completed_at", new_column_name="published_at")
    op.execute("UPDATE outboxevent SET status = 'published' WHERE status = 'complete'")
