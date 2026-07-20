"""Platform module-runtime state and persistence models."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import get_datetime_utc


class ModuleDesiredState(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNINSTALL_PENDING = "uninstall_pending"


class ModuleObservedState(StrEnum):
    BUNDLED = "bundled"
    MIGRATING = "migrating"
    READY = "ready"
    DEGRADED = "degraded"


class ModuleEntitlementEffect(StrEnum):
    GRANT = "grant"
    REVOKE = "revoke"


class OutboxEventStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    DEAD_LETTER = "dead_letter"


class EventDeliveryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    DEAD_LETTER = "dead_letter"


class EventDeliveryTargetType(StrEnum):
    LOCAL_CONSUMER = "local_consumer"
    EXTERNAL_BROKER = "external_broker"


class CapabilityBindingStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class ModuleRegistry(SQLModel, table=True):
    code: str = Field(primary_key=True, max_length=100)
    version: str = Field(max_length=100)
    desired_state: ModuleDesiredState = Field(
        default=ModuleDesiredState.ENABLED, sa_type=String(32), index=True
    )
    observed_state: ModuleObservedState = Field(
        default=ModuleObservedState.BUNDLED, sa_type=String(32), index=True
    )
    manifest_digest: str = Field(max_length=100)
    target_revision: str | None = Field(default=None, max_length=100)
    actual_revision: str | None = Field(default=None, max_length=100)
    health_details: str | None = Field(default=None, max_length=4000)
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ModuleRegistryPublic(SQLModel):
    code: str
    version: str
    desired_state: ModuleDesiredState
    observed_state: ModuleObservedState
    manifest_digest: str
    target_revision: str | None = None
    actual_revision: str | None = None
    health_details: str | None = None
    updated_at: datetime | None = None


class ModuleDesiredStateUpdate(SQLModel):
    desired_state: ModuleDesiredState
    reason: str | None = Field(default=None, max_length=500)


class TenantPlanModule(SQLModel, table=True):
    plan_id: uuid.UUID = Field(
        foreign_key="tenantplan.id", primary_key=True, ondelete="CASCADE"
    )
    module_code: str = Field(primary_key=True, max_length=100)
    is_enabled: bool = False
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class TenantPlanModuleUpdate(SQLModel):
    is_enabled: bool


class TenantModule(SQLModel, table=True):
    tenant_id: uuid.UUID = Field(
        foreign_key="tenant.id", primary_key=True, ondelete="CASCADE"
    )
    module_code: str = Field(primary_key=True, max_length=100)
    is_enabled: bool = True
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class TenantModuleUpdate(SQLModel):
    is_enabled: bool


class TenantModuleEntitlementOverride(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenant.id", index=True, ondelete="CASCADE"
    )
    module_code: str = Field(max_length=100, index=True)
    effect: ModuleEntitlementEffect = Field(sa_type=String(32))
    starts_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,  # type: ignore
    )
    ends_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,  # type: ignore
    )
    reason: str = Field(min_length=1, max_length=500)
    operator_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class TenantModuleEntitlementOverrideCreate(SQLModel):
    effect: ModuleEntitlementEffect
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str = Field(min_length=1, max_length=500)


class ModuleStateAudit(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    module_code: str = Field(max_length=100, index=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True, ondelete="CASCADE"
    )
    action: str = Field(max_length=100)
    previous_value: str | None = Field(default=None, max_length=100)
    next_value: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=500)
    actor_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class OutboxEvent(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    module_code: str = Field(max_length=100, index=True)
    event_type: str = Field(max_length=200, index=True)
    event_version: int = 1
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True, ondelete="CASCADE"
    )
    aggregate_id: str = Field(max_length=100, index=True)
    aggregate_sequence: int | None = Field(default=None, index=True)
    payload: str = Field(max_length=16000)
    trace_id: str | None = Field(default=None, max_length=100)
    occurred_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    available_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    status: OutboxEventStatus = Field(
        default=OutboxEventStatus.PENDING, sa_type=String(32), index=True
    )
    attempts: int = 0
    last_error: str | None = Field(default=None, max_length=2000)
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    dead_lettered_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class EventDelivery(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("event_id", "target_name", name="uq_event_delivery_target"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: uuid.UUID = Field(
        foreign_key="outboxevent.id", index=True, ondelete="CASCADE"
    )
    target_name: str = Field(max_length=100)
    target_type: EventDeliveryTargetType = Field(
        default=EventDeliveryTargetType.LOCAL_CONSUMER, sa_type=String(32), index=True
    )
    consumer_module: str | None = Field(default=None, max_length=100, index=True)
    is_required: bool = True
    status: EventDeliveryStatus = Field(
        default=EventDeliveryStatus.PENDING, sa_type=String(32), index=True
    )
    attempts: int = 0
    available_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)  # type: ignore
    locked_by: str | None = Field(default=None, max_length=100, index=True)
    locked_until: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        index=True,  # type: ignore
    )
    delivered_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    dead_lettered_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    last_error: str | None = Field(default=None, max_length=2000)


class InboxReceipt(SQLModel, table=True):
    consumer_name: str = Field(primary_key=True, max_length=100)
    event_id: uuid.UUID = Field(
        foreign_key="outboxevent.id", primary_key=True, ondelete="CASCADE"
    )
    processed_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore


class CapabilityBinding(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "consumer_module",
            "aggregate_type",
            "aggregate_id",
            "capability_code",
            name="uq_capability_binding_aggregate",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenant.id", index=True, ondelete="CASCADE"
    )
    consumer_module: str = Field(max_length=100, index=True)
    aggregate_type: str = Field(max_length=100)
    aggregate_id: str = Field(max_length=100)
    capability_code: str = Field(max_length=200)
    provider_code: str = Field(max_length=100)
    provider_version: str = Field(max_length=100)
    external_instance_id: str | None = Field(default=None, max_length=200)
    status: CapabilityBindingStatus = Field(
        default=CapabilityBindingStatus.ACTIVE, sa_type=String(32), index=True
    )
    created_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    closed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class OutboxEventPublic(SQLModel):
    id: uuid.UUID
    module_code: str
    event_type: str
    event_version: int
    tenant_id: uuid.UUID | None = None
    aggregate_id: str
    occurred_at: datetime
    status: OutboxEventStatus
    attempts: int
    last_error: str | None = None
